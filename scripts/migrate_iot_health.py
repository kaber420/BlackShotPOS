"""
Migración: Agrega columnas de salud a la tabla iotdevice.
Ejecutar una sola vez desde la raíz del proyecto:
    python scripts/migrate_iot_health.py
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'pos_database.db')
db_path = os.path.abspath(db_path)

print(f"Base de datos: {db_path}")

conn = sqlite3.connect(db_path)
try:
    # Agregar columnas una por una
    columns = [
        ("type", "TEXT DEFAULT 'esp32'"),
        ("battery_level", "INTEGER"),
        ("rssi", "INTEGER"),
        ("firmware_version", "TEXT")
    ]
    
    for col_name, col_type in columns:
        try:
            conn.execute(f"ALTER TABLE iotdevice ADD COLUMN {col_name} {col_type}")
            print(f"✅ Columna '{col_name}' añadida correctamente.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"ℹ️  La columna '{col_name}' ya existe.")
            else:
                print(f"❌ Error al añadir '{col_name}': {e}")
    
    # También asegurar que table_id sea opcional ( SQLite no soporta fácil ALTER COLUMN )
    # pero como ya agregamos columnas, el esquema de SQLModel se encargará de las lecturas.
    
    conn.commit()
    print("✅ Migración de IoT finalizada.")
except Exception as e:
    print(f"❌ Error general: {e}")
finally:
    conn.close()
