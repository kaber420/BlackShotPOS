import asyncio
from sqlmodel import select
from pos_core.database import engine
from pos_core.tables.models import Table
from pos_core.iot.models import IoTDevice
from sqlalchemy.ext.asyncio import AsyncSession

async def main():
    async with AsyncSession(engine) as session:
        # 1. Buscar o crear una mesa de prueba (Mesa 1)
        statement = select(Table).where(Table.number == 1)
        result = await session.execute(statement)
        table = result.scalars().first()
        
        if not table:
            print("No se encontró Mesa 1. Creando Mesa 1...")
            table = Table(number=1, capacity=4, status="Free", is_active=True)
            session.add(table)
            await session.commit()
            await session.refresh(table)
            print(f"Mesa 1 creada con ID: {table.id}")
        else:
            print(f"Mesa 1 encontrada con ID: {table.id}")
            
        # 2. Registrar el dispositivo IoT de prueba
        statement = select(IoTDevice).where(IoTDevice.token == "test-token-123")
        result = await session.execute(statement)
        device = result.scalars().first()
        
        if not device:
            print("Registrando dispositivo IoT de prueba con token 'test-token-123'...")
            device = IoTDevice(
                device_id="esp32_sim_test",
                token="test-token-123",
                name="ESP32 Simulador de Prueba",
                type="esp32",
                table_id=table.id,
                is_active=True,
                battery_level=100,
                rssi=-50,
                firmware_version="1.0.0"
            )
            session.add(device)
            await session.commit()
            print("¡Dispositivo IoT registrado exitosamente!")
        else:
            print("El dispositivo IoT con token 'test-token-123' ya estaba registrado.")
            # Asegurar que esté activo y enlazado a la mesa correcta
            device.is_active = True
            device.table_id = table.id
            session.add(device)
            await session.commit()
            print("Dispositivo actualizado y activado.")

if __name__ == '__main__':
    asyncio.run(main())
