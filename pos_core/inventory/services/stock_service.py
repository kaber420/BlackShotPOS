from typing import Optional
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Ingredient, IngredientBatch
from pos_core.catalog.models import ProductVariant, ModifierQuantity
from pos_core.events.service import trigger_broadcast
from pos_core.catalog.services.recipe_service import get_variant_recipe, get_product_recipe
from pos_core.exceptions import InsufficientStockError

# Configuración global de comportamiento de inventario
ALLOW_NEGATIVE_STOCK = False
MAX_RECURSION_DEPTH = 5

def _get_val(obj, key, default=None):
    """Helper to get value from either a dict or an object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

async def process_inventory_depletion(session: AsyncSession, order_items) -> None:
    """
    Resta los ingredientes del inventario basándose en las recetas de los productos o variantes en la orden.
    Soporta combos recursivos (productos que contienen otros productos).
    Utiliza una transacción atómica única.
    """
    try:
        for item in order_items:
            # Llamar a la función recursiva para el ítem principal
            await _deplete_recursive(
                session=session,
                product_id=_get_val(item, 'product_id'),
                variant_id=_get_val(item, 'product_variant_id'),
                quantity=_get_val(item, 'quantity', 1),
                selected_modifiers=_get_val(item, 'modifiers', []),
                depth=0
            )
                    
        await session.commit()
        await trigger_broadcast("inventory")
    except Exception as e:
        await session.rollback()
        raise e

async def _deplete_recursive(
    session: AsyncSession, 
    product_id: Optional[int], 
    variant_id: Optional[int], 
    quantity: float,
    selected_modifiers: list = [],
    depth: int = 0
) -> None:
    """Función interna recursiva para descontar inventario."""
    if depth > MAX_RECURSION_DEPTH:
        return
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
            # Ingrediente fijo - Usar Pessimistic Locking
            stmt = select(Ingredient).where(Ingredient.id == ri.ingredient_id).with_for_update()
            res = await session.execute(stmt)
            ingredient = res.scalar_one_or_none()
            
            if ingredient:
                if not ALLOW_NEGATIVE_STOCK and ingredient.current_stock < current_item_qty:
                    raise InsufficientStockError(ingredient.name, ingredient.current_stock, current_item_qty)
                
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
                quantity=current_item_qty,
                depth=depth + 1
            )

        elif ri.modifier_group_id:
            # Ingrediente dinámico: Buscamos qué modificador de este grupo se seleccionó
            for mod in selected_modifiers:
                m_group_id = _get_val(mod, 'modifier_group_id')
                if m_group_id == ri.modifier_group_id:
                    # Encontrado. Ver qué es este modificador (Ingrediente o Producto)
                    mod_ing_id = _get_val(mod, 'ingredient_id')
                    mod_prod_id = _get_val(mod, 'product_id')
                    mod_var_id = _get_val(mod, 'variant_id')

                    if mod_ing_id:
                        # Usar Pessimistic Locking
                        stmt = select(Ingredient).where(Ingredient.id == mod_ing_id).with_for_update()
                        res = await session.execute(stmt)
                        ingredient = res.scalar_one_or_none()
                        
                        if ingredient:
                            if not ALLOW_NEGATIVE_STOCK and ingredient.current_stock < current_item_qty:
                                raise InsufficientStockError(ingredient.name, ingredient.current_stock, current_item_qty)
                                
                            ingredient.current_stock -= current_item_qty
                            session.add(ingredient)
                            # También descontar de los lotes (FEFO)
                            await _subtract_from_batches(session, mod_ing_id, current_item_qty)
                    elif mod_prod_id:
                        await _deplete_recursive(session, mod_prod_id, mod_var_id, current_item_qty, depth=depth + 1)
                    
                    # Registrar este modificador para evitar descuento doble
                    mod_id = _get_val(mod, 'id')
                    deducted_modifier_ids.add(mod_id)
                    break
    
    # 4. Depleción por modificadores seleccionados (que no estuvieran en la receta base)
    for modifier in selected_modifiers:
        mod_id = _get_val(modifier, 'id')
        
        if mod_id in deducted_modifier_ids:
            continue

        mod_ing_id = _get_val(modifier, 'ingredient_id')
        mod_prod_id = _get_val(modifier, 'product_id')
        mod_var_id = _get_val(modifier, 'variant_id')

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
                mod_qty = _get_val(modifier, 'quantity', 0.0)

            if mod_qty > 0:
                # Usar Pessimistic Locking
                stmt = select(Ingredient).where(Ingredient.id == mod_ing_id).with_for_update()
                res = await session.execute(stmt)
                ingredient = res.scalar_one_or_none()
                
                if ingredient:
                    required_qty = mod_qty * quantity
                    if not ALLOW_NEGATIVE_STOCK and ingredient.current_stock < required_qty:
                        raise InsufficientStockError(ingredient.name, ingredient.current_stock, required_qty)
                    
                    ingredient.current_stock -= required_qty
                    session.add(ingredient)
                    # También descontar de los lotes (FEFO)
                    await _subtract_from_batches(session, mod_ing_id, required_qty)
        
        elif mod_prod_id:
            # El modificador es un producto (ej: "Agrandar a papas grandes" donde papas grandes es un producto)
            await _deplete_recursive(session, mod_prod_id, mod_var_id, quantity, depth=depth + 1)

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
