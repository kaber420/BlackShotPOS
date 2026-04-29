from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ..models import (
    ModifierGroup, ModifierGroupCreate, ModifierGroupUpdate,
    Modifier, ModifierCreate, ModifierUpdate, ModifierQuantity,
    Ingredient
)
from .. import unit_converter

async def create_modifier_group(session: AsyncSession, group: ModifierGroupCreate) -> ModifierGroup:
    db_group = ModifierGroup.model_validate(group)
    session.add(db_group)
    await session.commit()
    await session.refresh(db_group)
    
    from sqlalchemy.orm import selectinload
    statement = select(ModifierGroup).where(ModifierGroup.id == db_group.id).options(
        selectinload(ModifierGroup.modifiers)
    )
    result = await session.execute(statement)
    return result.scalar_one()

async def create_modifier(session: AsyncSession, modifier: ModifierCreate) -> Modifier:
    db_modifier = Modifier.model_validate(modifier)
    
    if db_modifier.input_unit and db_modifier.ingredient_id:
        ingredient = await session.get(Ingredient, db_modifier.ingredient_id)
        if ingredient:
            db_modifier.quantity = unit_converter.convert_to_base(
                db_modifier.input_quantity, 
                db_modifier.input_unit, 
                ingredient.measure_type
            )
    elif not db_modifier.input_quantity and db_modifier.quantity:
        db_modifier.input_quantity = db_modifier.quantity

    session.add(db_modifier)
    await session.commit()
    await session.refresh(db_modifier)
    
    from sqlalchemy.orm import selectinload
    statement = select(Modifier).where(Modifier.id == db_modifier.id).options(
        selectinload(Modifier.ingredient)
    )
    result = await session.execute(statement)
    return result.scalar_one()

async def get_modifier_groups(session: AsyncSession) -> List[ModifierGroup]:
    from sqlalchemy.orm import selectinload
    statement = select(ModifierGroup).options(
        selectinload(ModifierGroup.modifiers).selectinload(Modifier.ingredient)
    )
    result = await session.execute(statement)
    return result.scalars().all()

async def update_modifier_group(session: AsyncSession, group_id: int, group_data: ModifierGroupUpdate) -> Optional[ModifierGroup]:
    db_group = await session.get(ModifierGroup, group_id)
    if not db_group:
        return None
        
    update_data = group_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_group, key, value)
        
    session.add(db_group)
    await session.commit()
    
    from sqlalchemy.orm import selectinload
    statement = select(ModifierGroup).where(ModifierGroup.id == group_id).options(
        selectinload(ModifierGroup.modifiers)
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()

async def delete_modifier_group(session: AsyncSession, group_id: int) -> bool:
    db_group = await session.get(ModifierGroup, group_id)
    if not db_group:
        return False
    await session.delete(db_group)
    await session.commit()
    return True

async def update_modifier(session: AsyncSession, modifier_id: int, modifier_data: ModifierUpdate) -> Optional[Modifier]:
    db_modifier = await session.get(Modifier, modifier_id)
    if not db_modifier:
        return None
        
    update_data = modifier_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_modifier, key, value)
    
    if db_modifier.input_unit and db_modifier.ingredient_id:
        ingredient = await session.get(Ingredient, db_modifier.ingredient_id)
        if ingredient:
            db_modifier.quantity = unit_converter.convert_to_base(
                db_modifier.input_quantity, 
                db_modifier.input_unit, 
                ingredient.measure_type
            )
        
    session.add(db_modifier)
    await session.commit()
    
    from sqlalchemy.orm import selectinload
    statement = select(Modifier).where(Modifier.id == modifier_id).options(
        selectinload(Modifier.ingredient)
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()

async def delete_modifier(session: AsyncSession, modifier_id: int) -> bool:
    db_modifier = await session.get(Modifier, modifier_id)
    if not db_modifier:
        return False
    await session.delete(db_modifier)
    await session.commit()
    return True

async def link_modifier_group_to_product(session: AsyncSession, product_id: int, modifier_group_id: int):
    from ..models import ProductModifierLink
    
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

async def update_modifier_quantity(session: AsyncSession, modifier_id: int, measure_id: int, quantity: float) -> ModifierQuantity:
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
