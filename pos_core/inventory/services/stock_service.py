from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Ingredient, ProductVariant, ModifierQuantity
from pos_core.events.service import trigger_broadcast
from .recipe_service import get_variant_recipe, get_product_recipe

async def process_inventory_depletion(session: AsyncSession, order_items) -> None:
    """
    Resta los ingredientes del inventario baseando en las recetas de los productos o variantes en la orden.
    order_items is expected to be a list of OrderItem objects.
    """
    for item in order_items:
        recipe = []
        # 1. Priorizar receta por variante si existe
        if hasattr(item, 'product_variant_id') and item.product_variant_id:
            recipe = await get_variant_recipe(session, item.product_variant_id) or []
        
        # 2. Si no hay receta por variante, usar receta base del producto
        if not recipe and hasattr(item, 'product_id') and item.product_id:
            recipe = await get_product_recipe(session, item.product_id) or []

        # 3. Procesar cada componente de la receta (Fijo o por Grupo)
        # Guardaremos qué modificadores fueron usados como ingredientes de receta para no duplicar
        deducted_modifier_ids = set()
        
        for ri in recipe:
            final_ingredient_id = None
            final_quantity = ri.quantity * item.quantity

            if ri.ingredient_id:
                # Ingrediente fijo (Vaso, Café, etc)
                final_ingredient_id = ri.ingredient_id
            elif ri.modifier_group_id:
                # Ingrediente dinámico: Buscamos qué modificador de este grupo se seleccionó
                modifiers = getattr(item, 'modifiers', [])
                for mod in modifiers:
                    m_group_id = getattr(mod, 'modifier_group_id', None)
                    if m_group_id == ri.modifier_group_id:
                        final_ingredient_id = getattr(mod, 'ingredient_id', None)
                        # Registrar este modificador para evitar descuento doble
                        deducted_modifier_ids.add(getattr(mod, 'id', None))
                        break
            
            if final_ingredient_id:
                ingredient = await session.get(Ingredient, final_ingredient_id)
                if ingredient:
                    ingredient.current_stock -= final_quantity
                    session.add(ingredient)
        
        # 4. Depleción por modificadores seleccionados (que no estuvieran en la receta base)
        for modifier in getattr(item, 'modifiers', []):
            mod_id = modifier.get('id') if isinstance(modifier, dict) else getattr(modifier, 'id', None)
            
            # SI YA SE DESCONTÓ EN EL PASO 3 (Receta dinámica), OMITIR AQUÍ
            if mod_id in deducted_modifier_ids:
                continue

            ingredient_id = modifier.get('ingredient_id') if isinstance(modifier, dict) else getattr(modifier, 'ingredient_id', None)
            if ingredient_id:
                # Buscar cantidad específica por medida si existe
                quantity = 0.0
                
                # Obtener measure_id desde el item o cargándolo desde el variant_id
                measure_id = getattr(item, 'measure_id', None)
                if not measure_id and item.product_variant_id:
                    variant = await session.get(ProductVariant, item.product_variant_id)
                    if variant:
                        measure_id = variant.measure_id
                
                if measure_id:
                    stmt = select(ModifierQuantity).where(
                        ModifierQuantity.modifier_id == mod_id,
                        ModifierQuantity.measure_id == measure_id
                    )
                    res = await session.execute(stmt)
                    mod_qty = res.scalar_one_or_none()
                    if mod_qty:
                        quantity = mod_qty.quantity
                
                # Si no hay cantidad específica, usar la base del modificador
                if quantity == 0.0:
                    quantity = modifier.get('quantity', 0.0) if isinstance(modifier, dict) else getattr(modifier, 'quantity', 0.0)

                if quantity > 0:
                    mod_ingredient = await session.get(Ingredient, ingredient_id)
                    if mod_ingredient:
                        total_mod_deduction = quantity * item.quantity
                        mod_ingredient.current_stock -= total_mod_deduction
                        session.add(mod_ingredient)
                
    await session.commit()
    await trigger_broadcast("inventory")
