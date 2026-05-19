import asyncio
from sqlmodel import select
from pos_core.database import engine
from pos_core.iot.models import IoTDevice
from sqlalchemy.ext.asyncio import AsyncSession

async def main():
    async with AsyncSession(engine) as session:
        statement = select(IoTDevice)
        result = await session.execute(statement)
        devices = result.scalars().all()
        if not devices:
            print("No IoT devices found in the database.")
        for d in devices:
            print(f"Device: {d.name} | Table ID: {d.table_id} | Token: {d.token} | Active: {d.is_active}")

if __name__ == '__main__':
    asyncio.run(main())
