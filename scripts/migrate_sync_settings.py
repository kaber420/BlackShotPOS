"""
Migración: Agrega columnas nats_url y branch_id a la tabla businesssettings.
Ejecutar desde la raíz:
    python scripts/migrate_sync_settings.py
"""
import sqlite3
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pos_database.db'))

print(f"Base de datos: {db_path}")

conn = sqlite3.connect(db_path)
try:
    # SQLModel suele crear la tabla como 'businesssettings'
    conn.execute("ALTER TABLE businesssettings ADD COLUMN nats_url TEXT DEFAULT 'nats://localhost:4222'")
    conn.execute("ALTER TABLE businesssettings ADD COLUMN branch_id TEXT DEFAULT 'branch_default'")
    conn.commit()
    print("✅ Columnas 'nats_url' y 'branch_id' añadidas correctamente.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("ℹ️  Las columnas ya existen — no se requiere acción.")
    else:
        print(f"❌ Error: {e}")
finally:
    conn.close()
