import asyncio
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pos_core.database import async_session_maker
from pos_core.accounting.models import Shift, ShiftStatus
from sqlmodel import select
from sqlalchemy import update

async def close_shifts():
    async with async_session_maker() as session:
        await session.execute(update(Shift).where(Shift.status == ShiftStatus.OPEN).values(status=ShiftStatus.CLOSED))
        await session.commit()
        print("Closed all open shifts")

if __name__ == "__main__":
    asyncio.run(close_shifts())
