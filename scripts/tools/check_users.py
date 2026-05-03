import asyncio
from pos_core.database import async_session_maker
from pos_core.auth.models import User
from sqlmodel import select

async def check():
    async with async_session_maker() as s:
        res = await s.execute(select(User))
        users = res.scalars().all()
        for u in users:
            print(f"User: {u.email}, Active: {u.is_active}, Superuser: {u.is_superuser}")

if __name__ == "__main__":
    asyncio.run(check())
