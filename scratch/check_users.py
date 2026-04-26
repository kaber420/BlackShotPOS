import asyncio
from pos_core.database import async_session_maker
from pos_core.auth.models import User
from sqlmodel import select

async def check_users():
    async with async_session_maker() as session:
        statement = select(User)
        result = await session.execute(statement)
        users = result.scalars().all()
        print(f"Encontrados {len(users)} usuarios:")
        for u in users:
            print(f"- ID: {u.id}, Email: {u.email}, Role: {u.custom_metadata.get('role', 'N/A')}")
            print(f"  Metadata: {u.custom_metadata}")

if __name__ == "__main__":
    asyncio.run(check_users())
