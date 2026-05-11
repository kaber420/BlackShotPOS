
import asyncio
from pos_core.database import async_session_maker
from pos_core.accounting.models import CashRegister
from sqlmodel import select

async def main():
    async with async_session_maker() as session:
        result = await session.execute(select(CashRegister))
        registers = result.scalars().all()
        print(f"Total registers: {len(registers)}")
        for r in registers:
            print(f"ID: {r.id}, Name: {r.name}, Active: {r.is_active}")

if __name__ == "__main__":
    asyncio.run(main())
