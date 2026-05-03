import asyncio
import os
import sys

# Añadir el directorio raíz al path para poder importar pos_core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pos_core.database import async_session_maker
from pos_core.sales.audit_service import log_action
from pos_core.sales.models import AuditCategory
from sqlmodel import select
from pos_core.sales.models import AuditLog

async def main():
    async with async_session_maker() as session:
        await log_action(
            session=session,
            category=AuditCategory.SECURITY,
            action="PERMISSION_DENIED",
            actor_uuid="123",
            actor_name="Test User",
            reason="Test reason",
            target_id="test_permission",
            target_type="permission"
        )
        await session.commit()
        
        stmt = select(AuditLog)
        result = await session.execute(stmt)
        logs = result.scalars().all()
        for log in logs:
            print(f"Log: {log.category} - {log.action} - {log.target_type}")

if __name__ == "__main__":
    asyncio.run(main())
