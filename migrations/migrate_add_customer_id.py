"""
migrate_add_customer_id.py
--------------------------
Añade el campo `customer_id` a la tabla `order`.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'pos_database.db')

def run():
    if not os.path.exists(DB_PATH):
        print(f"❌  Base de datos no encontrada en: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        # Añadir columna customer_id a la tabla order
        # SQLModel mapea UUID a CHAR(32) por defecto en SQLite
        conn.execute("ALTER TABLE `order` ADD COLUMN customer_id CHAR(32) REFERENCES customer(id)")
        conn.commit()
        print("✅  Columna `customer_id` añadida a la tabla `order` correctamente.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("ℹ️   La columna `customer_id` ya existe en la tabla `order`.")
        else:
            print(f"❌  Error al migrar: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run()
