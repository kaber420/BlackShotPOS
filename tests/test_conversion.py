import asyncio
import os
import sys

# Añadir el directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pos_core.database import async_session_maker
from pos_core.inventory.models import Ingredient
from pos_core.inventory import unit_converter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

async def test_conversion():
    print("--- Test de Conversión de Inventario ---")
    
    async with async_session_maker() as session:
        # 1. Crear un ingrediente en Litros (L)
        leche = Ingredient(
            name="Leche de Prueba",
            measure_type="volume",
            unit="L",
            current_stock=10.0,
            minimum_stock=1.0
        )
        session.add(leche)
        await session.commit()
        await session.refresh(leche)
        print(f"Ingrediente creado: {leche.name}, Stock: {leche.current_stock} {leche.unit}")

        # 2. Simular adición de ingrediente a receta (como lo haría el router)
        # Queremos 200ml en una receta para un ingrediente que está en Litros
        input_qty = 200.0
        input_unit = "ml"
        
        # El router ahora debería usar convert_units
        final_qty = unit_converter.convert_units(
            input_qty, 
            input_unit, 
            leche.unit, 
            leche.measure_type
        )
        
        print(f"Conversión: {input_qty}{input_unit} -> {final_qty}{leche.unit}")
        
        if final_qty != 0.2:
            print(f"ERROR: Se esperaba 0.2, se obtuvo {final_qty}")
            return

        # 3. Simular descuento (como lo haría process_inventory_depletion)
        leche.current_stock -= final_qty
        session.add(leche)
        await session.commit()
        await session.refresh(leche)
        
        print(f"Stock después de descuento: {leche.current_stock} {leche.unit}")
        
        if leche.current_stock != 9.8:
            print(f"ERROR: Se esperaba 9.8, se obtuvo {leche.current_stock}")
            return

        from pos_core.inventory.services import ingredient_service
        from pos_core.inventory.models import IngredientUpdate
        
        # Cambiar de L a ml
        update_data = IngredientUpdate(unit="ml")
        updated_leche = await ingredient_service.update_ingredient(session, leche.id, update_data)
        
        print(f"Después de cambiar unidad a ml: Stock: {updated_leche.current_stock} {updated_leche.unit}")
        
        if updated_leche.current_stock != 9800.0:
            print(f"ERROR: Se esperaba 9800, se obtuvo {updated_leche.current_stock}")
            return

        print("--- ¡TODOS LOS TESTS PASARON! ---")
        
        # Limpiar
        await session.delete(updated_leche)
        await session.commit()

if __name__ == "__main__":
    asyncio.run(test_conversion())
