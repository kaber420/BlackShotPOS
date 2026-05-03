import asyncio
from pos_core.database import get_session
from pos_core.catalog.router import list_modifier_groups

async def main():
    async for session in get_session():
        res = await list_modifier_groups(session)
        print("Success:", len(res))
        break

asyncio.run(main())
