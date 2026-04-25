from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from .models import BusinessSettings, BusinessSettingsUpdate

async def get_settings(db: AsyncSession) -> BusinessSettings:
    """Obtiene la configuración del negocio. Si no existe, la crea con defaults."""
    statement = select(BusinessSettings).where(BusinessSettings.id == 1)
    result = await db.execute(statement)
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = BusinessSettings(id=1)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return settings

async def update_settings(db: AsyncSession, settings_in: BusinessSettingsUpdate) -> BusinessSettings:
    """Actualiza la configuración del negocio."""
    settings = await get_settings(db)
    
    update_data = settings_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)
        
    db.add(settings)
    await db.commit()
    await db.refresh(settings)
    return settings
