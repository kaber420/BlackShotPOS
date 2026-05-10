import asyncio
import sys
import os
from datetime import datetime, timezone

# Añadir el path del proyecto para poder importar los módulos
sys.path.append(os.getcwd())

from pos_core.database import async_session_maker
from pos_core.analytics.service import get_dashboard_stats

async def test_analytics():
    print("Testing Analytics Dashboard Stats...")
    async with async_session_maker() as session:
        try:
            stats = await get_dashboard_stats(session)
            print("\nDashboard Stats Results:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
            
            print("\nVerification Successful: SQL Aggregation is working.")
        except Exception as e:
            print(f"\nVerification Failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_analytics())
