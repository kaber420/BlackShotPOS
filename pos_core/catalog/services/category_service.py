from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ..models import Category, CategoryCreate, CategoryUpdate, Product, ProductVariant, ModifierGroup, Modifier

async def create_category(session: AsyncSession, category: CategoryCreate) -> Category:
    """Crea una nueva categoría en la base de datos."""
    db_category = Category.model_validate(category)
    session.add(db_category)
    await session.commit()
    await session.refresh(db_category)
    return db_category

async def get_categories(session: AsyncSession) -> List[Category]:
    """Obtiene todas las categorías activas."""
    statement = select(Category)
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
