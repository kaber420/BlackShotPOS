import asyncio
import os
import sys

# Añadir el directorio raíz al path para poder importar pos_core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from pos_core.database import engine, init_db, async_session_maker
from pos_core.catalog.models import Category, Product, RecipeItem, Measure, ProductVariant
from pos_core.inventory.models import Ingredient
from sqlmodel import select

async def seed():
    print("--- Iniciando Sembrado de Datos ---")
    
    # 0. Eliminar DB anterior para asegurar esquema fresco
    db_path = os.path.join(os.path.dirname(__file__), "..", "..", "pos_database.db")
    if os.path.exists(db_path):
        print("Eliminando base de datos antigua...")
        os.remove(db_path)

    
    # 1. Asegurar que las tablas existan
    await init_db()
    
    async with async_session_maker() as session:
        # Check if already seeded
        statement = select(Category)
        result = await session.execute(statement)
        if result.scalars().first():
            print("La base de datos ya tiene datos. Saltando sembrado.")
            return

        # 1.5 Crear Impuestos
        print("Creando impuestos...")
        from pos_core.catalog.models import Tax
        tax_iva_16 = Tax(name="IVA 16%", rate=16.0, description="Impuesto al valor agregado general")
        tax_iva_0 = Tax(name="IVA 0%", rate=0.0, description="Impuesto tasa cero para alimentos")
        tax_exento = Tax(name="Exento", rate=0.0, description="Sin impuestos aplicables")
        
        session.add_all([tax_iva_16, tax_iva_0, tax_exento])
        await session.commit()
        await session.refresh(tax_iva_16)
        await session.refresh(tax_iva_0)

        # 1.6 Crear Áreas de Producción
        print("Creando áreas de producción...")
        from pos_core.kitchen.models import ProductionArea
        area_general = ProductionArea(name="General", description="Estación principal / Punto de venta", printer_ip="192.168.1.102")
        area_bar = ProductionArea(name="Barra", description="Estación de bebidas calientes y frías", printer_ip="192.168.1.100")
        area_kitchen = ProductionArea(name="Cocina", description="Estación de repostería y alimentos", printer_ip="192.168.1.101")
        
        session.add_all([area_general, area_bar, area_kitchen])
        await session.commit()
        await session.refresh(area_general)
        await session.refresh(area_bar)
        await session.refresh(area_kitchen)

        # 2. Crear Categorías
        print("Creando categorías...")
        cat_cafe = Category(name="Café", description="Bebidas calientes a base de espresso", production_area_id=area_bar.id)
        cat_te = Category(name="Té & Infusiones", description="Tés de hoja suelta y tisanas", production_area_id=area_bar.id)
        cat_frias = Category(name="Bebidas Frías", description="Frappés, Iced Coffee y Sodas", production_area_id=area_bar.id)
        cat_bread = Category(name="Repostería", description="Pan dulce y acompañamientos", production_area_id=area_kitchen.id)
        
        session.add_all([cat_cafe, cat_te, cat_frias, cat_bread])
        await session.commit()
        await session.refresh(cat_cafe)
        await session.refresh(cat_bread)

        # 3. Crear Medidas
        print("Creando medidas...")
        m_chico = Measure(name="Chico", value=8, unit="oz")
        m_mediano = Measure(name="Mediano", value=12, unit="oz")
        m_grande = Measure(name="Grande", value=16, unit="oz")
        m_unico = Measure(name="Único", value=1, unit="pz")
        
        session.add_all([m_chico, m_mediano, m_grande, m_unico])
        await session.commit()
        await session.refresh(m_chico)
        await session.refresh(m_mediano)
        await session.refresh(m_grande)
        await session.refresh(m_unico)

        # 4. Crear Ingredientes (con los nuevos campos multi-unidad)
        print("Creando ingredientes...")
        i_grano = Ingredient(name="Café en Grano (Mezcla Casa)", measure_type="weight", unit="g", current_stock=10000, minimum_stock=1000, cost_per_unit=0.05)
        i_leche = Ingredient(name="Leche Entera", measure_type="volume", unit="ml", current_stock=20000, minimum_stock=2000, cost_per_unit=0.02)
        i_agua = Ingredient(name="Agua Purificada", measure_type="volume", unit="ml", current_stock=100000, minimum_stock=5000, cost_per_unit=0.001)
        i_croissant = Ingredient(name="Croissant Mantequilla", measure_type="unit", unit="pz", current_stock=24, minimum_stock=5, cost_per_unit=15.0)
        
        session.add_all([i_grano, i_leche, i_agua, i_croissant])
        await session.commit()
        await session.refresh(i_grano)
        await session.refresh(i_leche)
        await session.refresh(i_agua)
        await session.refresh(i_croissant)

        # 5. Crear Productos con Variantes (Café)
        print("Creando productos y variantes...")
        
        # Americano
        p_americano = Product(name="Americano", description="Espresso con agua caliente", price=35, category_id=cat_cafe.id, tax_id=tax_iva_16.id)
        session.add(p_americano)
        await session.commit()
        await session.refresh(p_americano)
        
        v_ame_chico = ProductVariant(product_id=p_americano.id, measure_id=m_chico.id, price=35)
        v_ame_mediano = ProductVariant(product_id=p_americano.id, measure_id=m_mediano.id, price=45)
        v_ame_grande = ProductVariant(product_id=p_americano.id, measure_id=m_grande.id, price=55)
        session.add_all([v_ame_chico, v_ame_mediano, v_ame_grande])
        
        # Latte
        p_latte = Product(name="Latte", description="Espresso con leche vaporizada", price=45, category_id=cat_cafe.id, tax_id=tax_iva_16.id)
        session.add(p_latte)
        await session.commit()
        await session.refresh(p_latte)
        
        v_lat_chico = ProductVariant(product_id=p_latte.id, measure_id=m_chico.id, price=45)
        v_lat_mediano = ProductVariant(product_id=p_latte.id, measure_id=m_mediano.id, price=55)
        v_lat_grande = ProductVariant(product_id=p_latte.id, measure_id=m_grande.id, price=65)
        session.add_all([v_lat_chico, v_lat_mediano, v_lat_grande])

        # Repostería (Sin variantes usualmente, o variante 'Único')
        p_croissant = Product(name="Croissant", description="Delicioso pan de mantequilla", price=40, category_id=cat_bread.id, tax_id=tax_iva_0.id)
        session.add(p_croissant)
        await session.commit()
        await session.refresh(p_croissant)
        
        v_croissant = ProductVariant(product_id=p_croissant.id, measure_id=m_unico.id, price=40)
        session.add(v_croissant)

        await session.commit()
        await session.refresh(v_ame_chico)
        await session.refresh(v_ame_grande)
        await session.refresh(v_lat_chico)
        await session.refresh(v_lat_grande)

        # 6. Crear Recetas específicas por Variante
        print("Creando recetas por variante...")
        
        # Americano Chico: 15g café, 200ml agua
        r1 = RecipeItem(variant_id=v_ame_chico.id, ingredient_id=i_grano.id, quantity=15, input_quantity=15, input_unit="g")
        r2 = RecipeItem(variant_id=v_ame_chico.id, ingredient_id=i_agua.id, quantity=200, input_quantity=200, input_unit="ml")
        
        # Americano Grande: 20g café, 400ml agua
        r3 = RecipeItem(variant_id=v_ame_grande.id, ingredient_id=i_grano.id, quantity=20, input_quantity=20, input_unit="g")
        r4 = RecipeItem(variant_id=v_ame_grande.id, ingredient_id=i_agua.id, quantity=400, input_quantity=400, input_unit="ml")
        
        # Latte Chico: 15g café, 200ml leche
        r5 = RecipeItem(variant_id=v_lat_chico.id, ingredient_id=i_grano.id, quantity=15, input_quantity=15, input_unit="g")
        r6 = RecipeItem(variant_id=v_lat_chico.id, ingredient_id=i_leche.id, quantity=200, input_quantity=200, input_unit="ml")
        
        # Latte Grande: 20g café, 0.4 Litros leche (ejemplo de conversión)
        r7 = RecipeItem(variant_id=v_lat_grande.id, ingredient_id=i_grano.id, quantity=20, input_quantity=20, input_unit="g")
        r8 = RecipeItem(variant_id=v_lat_grande.id, ingredient_id=i_leche.id, quantity=400, input_quantity=0.4, input_unit="L")
        
        # Croissant: 1 unidad
        r9 = RecipeItem(variant_id=v_croissant.id, ingredient_id=i_croissant.id, quantity=1, input_quantity=1, input_unit="pz")
        
        session.add_all([r1, r2, r3, r4, r5, r6, r7, r8, r9])
        await session.commit()

        # 7. Crear categorías de movimientos de caja (Caja Chica)
        print("Creando categorías de movimientos de caja...")
        from pos_core.accounting.models import CashMovementCategory, CashMovementType

        DEFAULT_CATEGORIES = [
            # Gastos
            {"name": "Compra de Insumos",             "type": CashMovementType.EXPENSE,    "description": "Compras de materia prima e ingredientes"},
            {"name": "Limpieza",                      "type": CashMovementType.EXPENSE,    "description": "Productos y servicios de limpieza"},
            {"name": "Mantenimiento",                 "type": CashMovementType.EXPENSE,    "description": "Reparaciones y mantenimiento de equipo"},
            {"name": "Propinas / Personal",           "type": CashMovementType.EXPENSE,    "description": "Pagos directos a empleados"},
            {"name": "Servicios",                     "type": CashMovementType.EXPENSE,    "description": "Agua, luz, gas, internet"},
            {"name": "Varios / Emergencias",          "type": CashMovementType.EXPENSE,    "description": "Gastos no categorizados"},
            {"name": "Gastos por Cortesías / Mermas", "type": CashMovementType.EXPENSE,    "description": "Costo de insumos regalados o mermas"},
            # Retiros
            {"name": "Retiro Parcial",                "type": CashMovementType.WITHDRAWAL, "description": "Retiro de seguridad del efectivo en caja"},
            # Ingresos
            {"name": "Fondo Extra",                   "type": CashMovementType.INCOME,     "description": "Adición de efectivo al fondo de caja"},
            {"name": "Corrección",                    "type": CashMovementType.INCOME,     "description": "Ajuste por error en conteo previo"},
        ]

        for cat_data in DEFAULT_CATEGORIES:
            session.add(CashMovementCategory(**cat_data))
        await session.commit()

        print("--- Sembrado de Datos COMPLETADO ---")

if __name__ == "__main__":
    asyncio.run(seed())
