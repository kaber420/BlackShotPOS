from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Ingredient, ProductVariant, ModifierQuantity, IngredientBatch
from pos_core.events.service import trigger_broadcast
from .recipe_service import get_variant_recipe, get_product_recipe

async def process_inventory_depletion(session: AsyncSession, order_items) -> None:
    """
    Resta los ingredientes del inventario basándose en las recetas de los productos o variantes en la orden.
    Soporta combos recursivos (productos que contienen otros productos).
    """
    for item in order_items:
        # Llamar a la función recursiva para el ítem principal
        await _deplete_recursive(
            session=session,
            product_id=getattr(item, 'product_id', None),
            variant_id=getattr(item, 'product_variant_id', None),
            quantity=item.quantity,
            selected_modifiers=getattr(item, 'modifiers', [])
        )
                
    await session.commit()
    await trigger_broadcast("inventory")

async def _deplete_recursive(
    session: AsyncSession, 
    product_id: Optional[int], 
    variant_id: Optional[int], 
    quantity: float,
    selected_modifiers: list = []
) -> None:
    """Función interna recursiva para descontar inventario."""
    recipe = []
    # 1. Priorizar receta por variante si existe
    if variant_id:
        recipe = await get_variant_recipe(session, variant_id) or []
    
    # 2. Si no hay receta por variante, usar receta base del producto
    if not recipe and product_id:
        recipe = await get_product_recipe(session, product_id) or []

    # 3. Procesar cada componente de la receta (Fijo o por Grupo)
    # Guardaremos qué modificadores fueron usados como ingredientes de receta para no duplicar
    deducted_modifier_ids = set()
    
    for ri in recipe:
        current_item_qty = ri.quantity * quantity

        if ri.ingredient_id:
            # Ingrediente fijo
            ingredient = await session.get(Ingredient, ri.ingredient_id)
            if ingredient:
                ingredient.current_stock -= current_item_qty
                session.add(ingredient)
                # También descontar de los lotes (FEFO)
                await _subtract_from_batches(session, ri.ingredient_id, current_item_qty)
        
        elif ri.child_product_id:
            # PRODUCTO HIJO (COMBO) - RECURSIÓN
            await _deplete_recursive(
                session=session,
                product_id=ri.child_product_id,
                variant_id=ri.child_variant_id,
                quantity=current_item_qty
            )

        elif ri.modifier_group_id:
            # Ingrediente dinámico: Buscamos qué modificador de este grupo se seleccionó
            for mod in selected_modifiers:
                m_group_id = getattr(mod, 'modifier_group_id', None) if not isinstance(mod, dict) else mod.get('modifier_group_id')
                if m_group_id == ri.modifier_group_id:
                    # Encontrado. Ver qué es este modificador (Ingrediente o Producto)
                    mod_ing_id = getattr(mod, 'ingredient_id', None) if not isinstance(mod, dict) else mod.get('ingredient_id')
                    mod_prod_id = getattr(mod, 'product_id', None) if not isinstance(mod, dict) else mod.get('product_id')
                    mod_var_id = getattr(mod, 'variant_id', None) if not isinstance(mod, dict) else mod.get('variant_id')

                    if mod_ing_id:
                        ingredient = await session.get(Ingredient, mod_ing_id)
                        if ingredient:
                            ingredient.current_stock -= current_item_qty
                            session.add(ingredient)
                            # También descontar de los lotes (FEFO)
                            await _subtract_from_batches(session, mod_ing_id, current_item_qty)
                    elif mod_prod_id:
                        await _deplete_recursive(session, mod_prod_id, mod_var_id, current_item_qty)
                    
                    # Registrar este modificador para evitar descuento doble
                    mod_id = getattr(mod, 'id', None) if not isinstance(mod, dict) else mod.get('id')
                    deducted_modifier_ids.add(mod_id)
                    break
    
    # 4. Depleción por modificadores seleccionados (que no estuvieran en la receta base)
    for modifier in selected_modifiers:
        mod_id = getattr(modifier, 'id', None) if not isinstance(modifier, dict) else modifier.get('id')
        
        if mod_id in deducted_modifier_ids:
            continue

        mod_ing_id = getattr(modifier, 'ingredient_id', None) if not isinstance(modifier, dict) else modifier.get('ingredient_id')
        mod_prod_id = getattr(modifier, 'product_id', None) if not isinstance(modifier, dict) else modifier.get('product_id')
        mod_var_id = getattr(modifier, 'variant_id', None) if not isinstance(modifier, dict) else modifier.get('variant_id')

        if mod_ing_id:
            # Buscar cantidad específica por medida si existe
            mod_qty = 0.0
            
            # Intentar obtener measure_id para ver si hay override de cantidad
            measure_id = None
            if variant_id:
                variant = await session.get(ProductVariant, variant_id)
                if variant:
                    measure_id = variant.measure_id
            
            if measure_id:
                stmt = select(ModifierQuantity).where(
                    ModifierQuantity.modifier_id == mod_id,
                    ModifierQuantity.measure_id == measure_id
                )
                res = await session.execute(stmt)
                mq = res.scalar_one_or_none()
                if mq:
                    mod_qty = mq.quantity
            
            if mod_qty == 0.0:
                mod_qty = getattr(modifier, 'quantity', 0.0) if not isinstance(modifier, dict) else modifier.get('quantity', 0.0)

            if mod_qty > 0:
                ingredient = await session.get(Ingredient, mod_ing_id)
                if ingredient:
                    ingredient.current_stock -= (mod_qty * quantity)
                    session.add(ingredient)
                    # También descontar de los lotes (FEFO)
                    await _subtract_from_batches(session, mod_ing_id, mod_qty * quantity)
        
        elif mod_prod_id:
            # El modificador es un producto (ej: "Agrandar a papas grandes" donde papas grandes es un producto)
            await _deplete_recursive(session, mod_prod_id, mod_var_id, quantity)

async def _subtract_from_batches(session: AsyncSession, ingredient_id: int, quantity: float):
    """
    Resta la cantidad especificada de los lotes (batches) del ingrediente.
    Sigue la lógica FEFO (First Expired, First Out).
    """
    from sqlalchemy import select
    # Buscamos lotes activos, ordenados por fecha de caducidad (nulos al final) y luego por fecha de llegada
    stmt = select(IngredientBatch).where(
        IngredientBatch.ingredient_id == ingredient_id,
        IngredientBatch.current_quantity > 0
    ).order_by(IngredientBatch.expiration_date.asc().nullslast(), IngredientBatch.arrival_date.asc())
    
    res = await session.execute(stmt)
    batches = res.scalars().all()
    
    remaining = quantity
    for batch in batches:
        if remaining <= 0:
            break
        take = min(batch.current_quantity, remaining)
        batch.current_quantity -= take
        remaining -= take
        session.add(batch)
                
    await session.commit()
    await trigger_broadcast("inventory")
