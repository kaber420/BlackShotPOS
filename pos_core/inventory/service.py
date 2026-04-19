from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
import os
from .models import (
    Category, CategoryCreate, CategoryUpdate, 
    Product, ProductCreate, ProductUpdate, 
    Ingredient, IngredientCreate, IngredientUpdate, 
    RecipeItem, RecipeItemCreate, 
    ModifierGroup, ModifierGroupCreate, ModifierGroupUpdate, 
    Modifier, ModifierCreate, ModifierUpdate, 
    POSPreset, POSPresetCreate, 
    Measure, MeasureCreate, 
    ProductVariant, ProductVariantCreate, ProductVariantUpdate,
    ModifierQuantity
)
from typing import List, Optional

def delete_local_image(url: Optional[str]):
    """Elimina físicamente un archivo de imagen si es local."""
    if not url or not url.startswith("/uploads/"):
        return
    filename = url.replace("/uploads/", "")
    # Evitar salir del directorio por seguridad
    if "/" in filename or ".." in filename:
        return
    file_path = os.path.join("data/img", filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Error borrando archivo {file_path}: {e}")

async def create_category(session: AsyncSession, category: CategoryCreate) -> Category:
    """Crea una nueva categoría en la base de datos."""
    db_category = Category.model_validate(category)
    session.add(db_category)
    await session.commit()
    await session.refresh(db_category)
    return db_category

async def get_categories(session: AsyncSession) -> List[Category]:
    """Obtiene todas las categorías activas con sus productos y detalles cargados."""
    from sqlalchemy.orm import selectinload, joinedload
    statement = select(Category).options(
        selectinload(Category.products).options(
            selectinload(Product.variants).joinedload(ProductVariant.measure),
            selectinload(Product.modifier_groups).selectinload(ModifierGroup.modifiers).joinedload(Modifier.ingredient)
        )
    )
    result = await session.execute(statement)
    return result.scalars().all()

async def update_category(session: AsyncSession, category_id: int, category_data: CategoryUpdate) -> Optional[Category]:
    """Actualiza una categoría existente."""
    db_category = await session.get(Category, category_id)
    if not db_category:
        return None
    
    # Actualizar campos
    update_data = category_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_category, key, value)
        
    session.add(db_category)
    await session.commit()
    await session.refresh(db_category)
    return db_category

async def delete_category(session: AsyncSession, category_id: int) -> bool:
    """Elimina una categoría (física o lógicamente según convenga, aquí física por simplicidad)."""
    db_category = await session.get(Category, category_id)
    if not db_category:
        return False
    await session.delete(db_category)
    await session.commit()
    return True

async def create_product(session: AsyncSession, product: ProductCreate) -> Product:
    """Crea un nuevo producto."""
    db_product = Product.model_validate(product)
    session.add(db_product)
    await session.commit()
    await session.refresh(db_product)
    
    # Recargar con relaciones para evitar MissingGreenlet en el response_model (ProductRead)
    from sqlalchemy.orm import selectinload
    statement = select(Product).where(Product.id == db_product.id).options(
        selectinload(Product.category),
        selectinload(Product.variants),
        selectinload(Product.modifier_groups)
    )
    result = await session.execute(statement)
    return result.scalar_one()

async def get_products(session: AsyncSession, category_id: Optional[int] = None, include_inactive: bool = False) -> List[Product]:
    """Obtiene el listado de productos, con sus grupos de modificadores y categorías cargados."""
    from sqlalchemy.orm import selectinload
    statement = select(Product).options(
        selectinload(Product.category),
        selectinload(Product.modifier_groups).selectinload(ModifierGroup.modifiers).selectinload(Modifier.ingredient),
        selectinload(Product.variants).selectinload(ProductVariant.measure)
    )
    if not include_inactive:
        statement = statement.where(Product.is_active == True)
    if category_id:
        statement = statement.where(Product.category_id == category_id)
    result = await session.execute(statement)
    return result.scalars().all()

async def get_product_by_id(session: AsyncSession, product_id: int) -> Optional[Product]:
    """Obtiene un producto específico por su ID con todos sus modificadores, variantes y categoría."""
    from sqlalchemy.orm import selectinload
    statement = select(Product).where(Product.id == product_id).options(
        selectinload(Product.category),
        selectinload(Product.modifier_groups).selectinload(ModifierGroup.modifiers).selectinload(Modifier.ingredient),
        selectinload(Product.variants).selectinload(ProductVariant.measure)
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()

async def update_product(session: AsyncSession, product_id: int, product_data: ProductUpdate) -> Optional[Product]:
    """Actualiza un producto existente, incluyendo sus vínculos a grupos de modificadores."""
    from .models import ProductModifierLink
    from sqlalchemy.orm import selectinload
    
    statement = select(Product).where(Product.id == product_id).options(
        selectinload(Product.modifier_groups)
    )
    result = await session.execute(statement)
    db_product = result.scalar_one_or_none()
    
    if not db_product:
        return None
    
    # Actualizar campos básicos
    update_data = product_data.model_dump(exclude_unset=True, exclude={"modifier_groups"})
    for key, value in update_data.items():
        if key == "image_url" and db_product.image_url != value:
            # Si la imagen cambió y teníamos una local, borrar la anterior
            delete_local_image(db_product.image_url)
        setattr(db_product, key, value)
        
    # Sincronizar Grupos de Modificadores (Many-to-Many)
    if product_data.modifier_groups is not None:
        # 1. Eliminar vínculos actuales
        from sqlmodel import delete
        delete_stmt = delete(ProductModifierLink).where(ProductModifierLink.product_id == product_id)
        await session.execute(delete_stmt)
        
        # 2. Crear nuevos vínculos
        for group_dict in product_data.modifier_groups:
            group_id = group_dict.get("id")
            if group_id:
                new_link = ProductModifierLink(product_id=product_id, modifier_group_id=group_id)
                session.add(new_link)

    session.add(db_product)
    await session.commit()
    
    # Recargar con relaciones
    return await get_product_by_id(session, product_id)

async def delete_product(session: AsyncSession, product_id: int) -> bool:
    """Desactiva un producto (borrado lógico por seguridad en ventas)."""
    db_product = await session.get(Product, product_id)
    if not db_product:
        return False
    db_product.is_active = False
    session.add(db_product)
    await session.commit()
    return True

# --- Operaciones de Ingredientes (Materia Prima) ---

async def create_ingredient(session: AsyncSession, ingredient: IngredientCreate) -> Ingredient:
    db_ingredient = Ingredient.model_validate(ingredient)
    session.add(db_ingredient)
    await session.commit()
    await session.refresh(db_ingredient)
    return db_ingredient

async def get_ingredients(session: AsyncSession) -> List[Ingredient]:
    statement = select(Ingredient)
    result = await session.execute(statement)
    return result.scalars().all()

async def update_ingredient(session: AsyncSession, ingredient_id: int, ingredient_data: IngredientUpdate) -> Optional[Ingredient]:
    """Actualiza un ingrediente existente."""
    db_ingredient = await session.get(Ingredient, ingredient_id)
    if not db_ingredient:
        return None
    
    update_data = ingredient_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_ingredient, key, value)
        
    session.add(db_ingredient)
    await session.commit()
    await session.refresh(db_ingredient)
    return db_ingredient

async def delete_ingredient(session: AsyncSession, ingredient_id: int) -> bool:
    """Elimina un ingrediente."""
    db_ingredient = await session.get(Ingredient, ingredient_id)
    if not db_ingredient:
        return False
    await session.delete(db_ingredient)
    await session.commit()
    return True

# --- Operaciones de Modificadores ---

async def create_modifier_group(session: AsyncSession, group: ModifierGroupCreate) -> ModifierGroup:
    db_group = ModifierGroup.model_validate(group)
    session.add(db_group)
    await session.commit()
    await session.refresh(db_group)
    
    # Recargar con relaciones para evitar MissingGreenlet en el response_model
    from sqlalchemy.orm import selectinload
    statement = select(ModifierGroup).where(ModifierGroup.id == db_group.id).options(
        selectinload(ModifierGroup.modifiers)
    )
    result = await session.execute(statement)
    return result.scalar_one()

async def create_modifier(session: AsyncSession, modifier: ModifierCreate) -> Modifier:
    db_modifier = Modifier.model_validate(modifier)
    session.add(db_modifier)
    await session.commit()
    await session.refresh(db_modifier)
    
    # Recargar con relaciones
    from sqlalchemy.orm import selectinload
    statement = select(Modifier).where(Modifier.id == db_modifier.id).options(
        selectinload(Modifier.ingredient)
    )
    result = await session.execute(statement)
    return result.scalar_one()

async def get_modifier_groups(session: AsyncSession) -> List[ModifierGroup]:
    """Obtiene todos los grupos de modificadores con sus opciones y sus ingredientes relacionados."""
    from sqlalchemy.orm import selectinload
    statement = select(ModifierGroup).options(
        selectinload(ModifierGroup.modifiers).selectinload(Modifier.ingredient)
    )
    result = await session.execute(statement)
    return result.scalars().all()

async def update_modifier_group(session: AsyncSession, group_id: int, group_data: ModifierGroupUpdate) -> Optional[ModifierGroup]:
    """Actualiza un grupo de modificadores."""
    db_group = await session.get(ModifierGroup, group_id)
    if not db_group:
        return None
        
    update_data = group_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_group, key, value)
        
    session.add(db_group)
    await session.commit()
    
    # Recargar con relaciones
    from sqlalchemy.orm import selectinload
    statement = select(ModifierGroup).where(ModifierGroup.id == group_id).options(
        selectinload(ModifierGroup.modifiers)
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()

async def delete_modifier_group(session: AsyncSession, group_id: int) -> bool:
    """Elimina un grupo de modificadores."""
    db_group = await session.get(ModifierGroup, group_id)
    if not db_group:
        return False
    await session.delete(db_group)
    await session.commit()
    return True

async def update_modifier(session: AsyncSession, modifier_id: int, modifier_data: ModifierUpdate) -> Optional[Modifier]:
    """Actualiza una opción de modificador."""
    db_modifier = await session.get(Modifier, modifier_id)
    if not db_modifier:
        return None
        
    update_data = modifier_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_modifier, key, value)
        
    session.add(db_modifier)
    await session.commit()
    
    # Recargar con relaciones
    from sqlalchemy.orm import selectinload
    statement = select(Modifier).where(Modifier.id == modifier_id).options(
        selectinload(Modifier.ingredient)
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()

async def delete_modifier(session: AsyncSession, modifier_id: int) -> bool:
    """Elimina una opción de modificador."""
    db_modifier = await session.get(Modifier, modifier_id)
    if not db_modifier:
        return False
    await session.delete(db_modifier)
    await session.commit()
    return True

async def link_modifier_group_to_product(session: AsyncSession, product_id: int, modifier_group_id: int):
    from .models import ProductModifierLink
    from sqlmodel import select
    
    # Verificar si ya existe el vínculo para evitar IntegrityError
    stmt = select(ProductModifierLink).where(
        ProductModifierLink.product_id == product_id,
        ProductModifierLink.modifier_group_id == modifier_group_id
    )
    res = await session.execute(stmt)
    existing = res.scalar_one_or_none()
    
    if existing:
        return existing
        
    link = ProductModifierLink(product_id=product_id, modifier_group_id=modifier_group_id)
    session.add(link)
    await session.commit()
    return link

async def get_product_presets(session: AsyncSession, product_id: int) -> List["POSPreset"]:
    from .models import POSPreset
    statement = select(POSPreset).where(POSPreset.product_id == product_id)
    result = await session.execute(statement)
    return result.scalars().all()

async def create_preset(session: AsyncSession, preset: "POSPreset") -> "POSPreset":
    session.add(preset)
    await session.commit()
    await session.refresh(preset)
    return preset

# --- Operaciones de Medidas (Sizes) ---

async def create_measure(session: AsyncSession, measure: MeasureCreate) -> Measure:
    db_measure = Measure.model_validate(measure)
    session.add(db_measure)
    await session.commit()
    await session.refresh(db_measure)
    return db_measure

async def get_measures(session: AsyncSession) -> List[Measure]:
    result = await session.execute(select(Measure))
    return result.scalars().all()

# --- Operaciones de Variantes ---

async def create_variant(session: AsyncSession, variant: ProductVariantCreate) -> ProductVariant:
    db_variant = ProductVariant.model_validate(variant)
    session.add(db_variant)
    await session.commit()
    await session.refresh(db_variant)
    
    # Recargar con relaciones para evitar MissingGreenlet en el response_model (ProductVariantRead)
    from sqlalchemy.orm import selectinload
    statement = select(ProductVariant).where(ProductVariant.id == db_variant.id).options(
        selectinload(ProductVariant.measure),
        selectinload(ProductVariant.recipe_items)
    )
    result = await session.execute(statement)
    return result.scalar_one()

async def get_variants_by_product(session: AsyncSession, product_id: int) -> List[ProductVariant]:
    from sqlalchemy.orm import selectinload
    statement = select(ProductVariant).where(ProductVariant.product_id == product_id).options(
        selectinload(ProductVariant.measure),
        selectinload(ProductVariant.recipe_items)
    )
    result = await session.execute(statement)
    return result.scalars().all()

async def update_variant(session: AsyncSession, variant_id: int, variant_data: ProductVariantUpdate) -> Optional[ProductVariant]:
    """Actualiza una variante existente."""
    db_variant = await session.get(ProductVariant, variant_id)
    if not db_variant:
        return None
    
    update_data = variant_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "image_url" and db_variant.image_url != value:
            delete_local_image(db_variant.image_url)
        setattr(db_variant, key, value)
        
    session.add(db_variant)
    await session.commit()
    
    # Recargar con relaciones
    from sqlalchemy.orm import selectinload
    statement = select(ProductVariant).where(ProductVariant.id == variant_id).options(
        selectinload(ProductVariant.measure),
        selectinload(ProductVariant.recipe_items)
    )
    result = await session.execute(statement)
    return result.scalar_one()

async def delete_variant(session: AsyncSession, variant_id: int) -> bool:
    """Elimina una variante de producto y su imagen asociada."""
    db_variant = await session.get(ProductVariant, variant_id)
    if not db_variant:
        return False
    
    # Limpiar imagen antes de borrar de DB
    if db_variant.image_url:
        delete_local_image(db_variant.image_url)
        
    await session.delete(db_variant)
    await session.commit()
    return True

async def clear_variant_recipe(session: AsyncSession, variant_id: int):
    """Elimina todos los elementos de la receta asociados a una variante."""
    from sqlmodel import delete
    statement = delete(RecipeItem).where(RecipeItem.variant_id == variant_id)
    await session.execute(statement)
    await session.commit()
    return True

async def update_modifier_quantity(session: AsyncSession, modifier_id: int, measure_id: int, quantity: float) -> ModifierQuantity:
    """Crea o actualiza la cantidad de descuento de un modificador para una medida específica."""
    stmt = select(ModifierQuantity).where(
        ModifierQuantity.modifier_id == modifier_id,
        ModifierQuantity.measure_id == measure_id
    )
    result = await session.execute(stmt)
    db_obj = result.scalar_one_or_none()
    
    if db_obj:
        db_obj.quantity = quantity
    else:
        db_obj = ModifierQuantity(modifier_id=modifier_id, measure_id=measure_id, quantity=quantity)
    
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj

# --- Operaciones de Recetas ---

async def add_ingredient_to_product(session: AsyncSession, recipe_item: RecipeItem) -> RecipeItem:
    """Asocia un ingrediente a un producto con una cantidad específica."""
    session.add(recipe_item)
    await session.commit()
    await session.refresh(recipe_item)
    return recipe_item

async def get_product_recipe(session: AsyncSession, product_id: int) -> List[RecipeItem]:
    """Obtiene la lista de ingredientes y cantidades de un producto (base)."""
    statement = select(RecipeItem).where(RecipeItem.product_id == product_id)
    result = await session.execute(statement)
    return result.scalars().all()

async def get_variant_recipe(session: AsyncSession, variant_id: int) -> List[RecipeItem]:
    """Obtiene la lista de ingredientes y cantidades de una variante específica."""
    statement = select(RecipeItem).where(RecipeItem.variant_id == variant_id)
    result = await session.execute(statement)
    return result.scalars().all()

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

