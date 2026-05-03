from sqlmodel import Session, select
from models import engine, User, Region, GlobalProduct, GlobalCategory, Branch, create_db_and_tables
import os

def seed():
    # Asegurar que las tablas existan
    create_db_and_tables()

    with Session(engine) as session:
        # 1. Crear Regiones
        if not session.exec(select(Region)).first():
            norte = Region(name="Zona Norte", description="Sucursales del norte del país")
            centro = Region(name="Zona Centro", description="Sucursales de la capital y alrededores")
            session.add(norte)
            session.add(centro)
            session.commit()
            print("✅ Regiones creadas")

        # 2. Crear Categorías Globales
        if not session.exec(select(GlobalCategory)).first():
            bebidas = GlobalCategory(name="Bebidas", description="Cafés, tés y refrescos")
            comida = GlobalCategory(name="Comida", description="Panadería y snacks")
            session.add(bebidas)
            session.add(comida)
            session.commit()
            print("✅ Categorías creadas")

        # 3. Crear Productos Globales
        if not session.exec(select(GlobalProduct)).first():
            bebidas_id = session.exec(select(GlobalCategory).where(GlobalCategory.name == "Bebidas")).first().id
            espresso = GlobalProduct(name="Espresso Maestro", description="Café espresso premium", price_suggested=35.0, category_id=bebidas_id)
            latte = GlobalProduct(name="Latte Art", description="Café con leche cremosa", price_suggested=45.0, category_id=bebidas_id)
            session.add(espresso)
            session.add(latte)
            session.commit()
            print("✅ Productos creados")

        # 4. Crear Usuarios
        if not session.exec(select(User)).first():
            admin = User(
                email="admin@blackshot.app",
                full_name="Admin Global",
                hashed_password="hash_admin123",
                role="superadmin"
            )
            reg_mgr = User(
                email="gerente.norte@blackshot.app",
                full_name="Juan Perez",
                hashed_password="hash_norte123",
                role="regional_manager"
            )
            session.add(admin)
            session.add(reg_mgr)
            session.commit()
            print("✅ Usuarios creados")

if __name__ == "__main__":
    seed()
