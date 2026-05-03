"""
Migración: Agrega columna locale a la tabla businesssettings.
Ejecutar una sola vez desde la raíz del proyecto:
    python scripts/migrate_add_locale.py
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'pos_database.db')
db_path = os.path.abspath(db_path)

print(f"Base de datos: {db_path}")

conn = sqlite3.connect(db_path)
try:
    conn.execute("ALTER TABLE businesssettings ADD COLUMN locale TEXT DEFAULT 'es-MX'")
    conn.commit()
    print("✅ Columna 'locale' añadida correctamente a la tabla 'businesssettings'.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("ℹ️  La columna 'locale' ya existe — no se requiere acción.")
    else:
        print(f"❌ Error: {e}")
finally:
    conn.close()
