"""
Migración: Agrega columna recipe_markdown a la tabla product.
Ejecutar una sola vez desde la raíz del proyecto:
    python scripts/migrate_add_recipe.py
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'pos_database.db')
db_path = os.path.abspath(db_path)

print(f"Base de datos: {db_path}")

conn = sqlite3.connect(db_path)
try:
    conn.execute("ALTER TABLE product ADD COLUMN recipe_markdown TEXT")
    conn.commit()
    print("✅ Columna 'recipe_markdown' añadida correctamente a la tabla 'product'.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("ℹ️  La columna 'recipe_markdown' ya existe — no se requiere acción.")
    else:
        raise
finally:
    conn.close()
