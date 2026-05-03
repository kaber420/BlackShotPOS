import asyncio
from pos_core.database import get_session
from pos_core.catalog.services.modifier_service import get_modifier_groups

async def main():
    async for session in get_session():
        res = await get_modifier_groups(session)
        print("Success modifier groups:", len(res))
        break

asyncio.run(main())
