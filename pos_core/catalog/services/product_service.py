from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ..models import (
    Product, ProductCreate, ProductUpdate,
    ProductVariant, ProductVariantCreate, ProductVariantUpdate,
    POSPreset, Measure, MeasureCreate, ModifierGroup, Modifier,
    RecipeItem
)
from .utils import delete_local_image

async def create_product(session: AsyncSession, product: ProductCreate) -> Product:
    """Crea un nuevo producto."""
    db_product = Product.model_validate(product)
    session.add(db_product)
    await session.commit()
    await session.refresh(db_product)
    
    from sqlalchemy.orm import selectinload
    statement = select(Product).where(Product.id == db_product.id).options(
        selectinload(Product.category),
        selectinload(Product.tax),
        selectinload(Product.variants),
        selectinload(Product.modifier_groups)
    )
    result = await session.execute(statement)
    return result.scalar_one()

async def get_products(
    session: AsyncSession, 
    category_id: Optional[int] = None, 
    include_inactive: bool = False,
    search: Optional[str] = None,
    offset: int = 0,
    limit: int = 100
) -> List[Product]:
    from sqlalchemy.orm import selectinload
    from sqlalchemy import or_
    statement = select(Product).options(
        selectinload(Product.category),
        selectinload(Product.tax),
        selectinload(Product.modifier_groups).selectinload(ModifierGroup.modifiers).selectinload(Modifier.ingredient),
        selectinload(Product.variants).selectinload(ProductVariant.measure)
    )
    if not include_inactive:
        statement = statement.where(Product.is_active == True)
    if category_id:
        statement = statement.where(Product.category_id == category_id)
    
    if search:
        search_query = f"%{search}%"
        statement = statement.where(
            or_(
                Product.name.ilike(search_query),
                Product.description.ilike(search_query),
                Product.sku.ilike(search_query)
            )
        )
    
    statement = statement.offset(offset).limit(limit)
    
    result = await session.execute(statement)
    return result.scalars().all()

async def get_product_by_id(session: AsyncSession, product_id: int) -> Optional[Product]:
    from sqlalchemy.orm import selectinload
    statement = select(Product).where(Product.id == product_id).options(
        selectinload(Product.category),
        selectinload(Product.tax),
        selectinload(Product.modifier_groups).selectinload(ModifierGroup.modifiers).selectinload(Modifier.ingredient),
        selectinload(Product.variants).selectinload(ProductVariant.measure)
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()

async def update_product(session: AsyncSession, product_id: int, product_data: ProductUpdate) -> Optional[Product]:
    from ..models import ProductModifierLink
    from sqlalchemy.orm import selectinload
    
    statement = select(Product).where(Product.id == product_id).options(
        selectinload(Product.modifier_groups)
    )
    result = await session.execute(statement)
    db_product = result.scalar_one_or_none()
    
    if not db_product:
        return None
    
    update_data = product_data.model_dump(exclude_unset=True, exclude={"modifier_groups"})
    for key, value in update_data.items():
        if key == "image_url" and db_product.image_url != value:
            delete_local_image(db_product.image_url)
        setattr(db_product, key, value)
        
    if product_data.modifier_groups is not None:
        from sqlmodel import delete
        delete_stmt = delete(ProductModifierLink).where(ProductModifierLink.product_id == product_id)
        await session.execute(delete_stmt)
        
        for group_dict in product_data.modifier_groups:
            group_id = group_dict.get("id")
            if group_id:
                new_link = ProductModifierLink(product_id=product_id, modifier_group_id=group_id)
                session.add(new_link)

    session.add(db_product)
    await session.commit()
    
    return await get_product_by_id(session, product_id)

async def delete_product(session: AsyncSession, product_id: int) -> bool:
    db_product = await session.get(Product, product_id)
    if not db_product:
        return False
    db_product.is_active = False
    session.add(db_product)
    await session.commit()
    return True

async def get_product_presets(session: AsyncSession, product_id: int) -> List["POSPreset"]:
    statement = select(POSPreset).where(POSPreset.product_id == product_id)
    result = await session.execute(statement)
    return result.scalars().all()

async def create_preset(session: AsyncSession, preset: "POSPreset") -> "POSPreset":
    session.add(preset)
    await session.commit()
    await session.refresh(preset)
    return preset

async def create_measure(session: AsyncSession, measure: MeasureCreate) -> Measure:
    db_measure = Measure.model_validate(measure)
    session.add(db_measure)
    await session.commit()
    await session.refresh(db_measure)
    return db_measure

async def get_measures(session: AsyncSession) -> List[Measure]:
    result = await session.execute(select(Measure))
    return result.scalars().all()

async def create_variant(session: AsyncSession, variant: ProductVariantCreate) -> ProductVariant:
    db_variant = ProductVariant.model_validate(variant)
    session.add(db_variant)
    await session.commit()
    await session.refresh(db_variant)
    
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
    
    from sqlalchemy.orm import selectinload
    statement = select(ProductVariant).where(ProductVariant.id == variant_id).options(
        selectinload(ProductVariant.measure),
        selectinload(ProductVariant.recipe_items)
    )
    result = await session.execute(statement)
    return result.scalar_one()

async def delete_variant(session: AsyncSession, variant_id: int) -> bool:
    db_variant = await session.get(ProductVariant, variant_id)
    if not db_variant:
        return False
    
    if db_variant.image_url:
        delete_local_image(db_variant.image_url)
        
    await session.delete(db_variant)
    await session.commit()
    return True

async def clear_variant_recipe(session: AsyncSession, variant_id: int):
    from sqlmodel import delete
    statement = delete(RecipeItem).where(RecipeItem.variant_id == variant_id)
    await session.execute(statement)
    await session.commit()
    return True
