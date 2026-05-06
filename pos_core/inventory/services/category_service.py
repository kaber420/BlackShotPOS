from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ..models import InventoryCategory, InventoryCategoryCreate, InventoryCategoryUpdate

async def get_categories(session: AsyncSession) -> List[InventoryCategory]:
    statement = select(InventoryCategory)
    result = await session.execute(statement)
    return result.scalars().all()

async def create_category(session: AsyncSession, category: InventoryCategoryCreate) -> InventoryCategory:
    db_category = InventoryCategory.model_validate(category)
    session.add(db_category)
    await session.commit()
    await session.refresh(db_category)
    return db_category

async def update_category(session: AsyncSession, category_id: int, category_data: InventoryCategoryUpdate) -> Optional[InventoryCategory]:
    db_category = await session.get(InventoryCategory, category_id)
    if not db_category:
        return None
    
    update_data = category_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_category, key, value)
        
    session.add(db_category)
    await session.commit()
    await session.refresh(db_category)
    return db_category

async def delete_category(session: AsyncSession, category_id: int) -> bool:
    db_category = await session.get(InventoryCategory, category_id)
    if not db_category:
        return False
    await session.delete(db_category)
    await session.commit()
    return True
