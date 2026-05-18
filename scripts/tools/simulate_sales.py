import asyncio
import nats
import json
import random
from datetime import datetime
import os

async def simulate():
    print("🚀 Iniciando Simulador de Ventas...")
    nc = await nats.connect(os.getenv("NATS_URL", "nats://localhost:4222"))
    
    branches = [
        {"id": "branch-norte-1", "name": "Blackshot Norte 1"},
        {"id": "branch-centro-1", "name": "Blackshot Centro 1"}
    ]
    
    products = [
        {"name": "Espresso Maestro", "price": 35.0},
        {"name": "Latte Art", "price": 45.0},
        {"name": "Capuccino Classic", "price": 50.0},
        {"name": "Panini Pollo", "price": 85.0}
    ]

    try:
        while True:
            branch = random.choice(branches)
            # Simular una venta de 1 a 3 items
            items = []
            total = 0
            for _ in range(random.randint(1, 3)):
                p = random.choice(products)
                qty = random.randint(1, 2)
                items.append({
                    "name": p["name"],
                    "quantity": qty,
                    "price": p["price"]
                })
                total += p["price"] * qty

            payload = {
                "branch_id": branch["id"],
                "branch_name": branch["name"],
                "amount": total,
                "total_amount": total,
                "items_count": len(items),
                "items": items,
                "is_final_payment": True,
                "created_at": datetime.now().isoformat()
            }

            # Publicar evento que el event_consumer.py procesará
            subject = f"branches.{branch['id']}.sales.payment_added"
            await nc.publish(subject, json.dumps(payload).encode())
            
            print(f"💰 Venta enviada: {branch['name']} - ${total:.2f}")
            
            # Esperar entre 2 y 5 segundos para la siguiente venta
            await asyncio.sleep(random.uniform(2, 5))
            
    except KeyboardInterrupt:
        await nc.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(simulate())
