"""
Migración: Agrega columnas received_amount y change_amount a la tabla payment.
Ejecutar desde la raíz del proyecto:
    python scripts/migrate_payment_accounting.py
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'pos_database.db')
db_path = os.path.abspath(db_path)

print(f"Base de datos: {db_path}")

conn = sqlite3.connect(db_path)
try:
    # SQLModel/SQLAlchemy usa nombres de tabla en minúsculas por defecto
    conn.execute("ALTER TABLE payment ADD COLUMN received_amount FLOAT DEFAULT 0.0")
    print("✅ Columna 'received_amount' añadida.")
except sqlite3.OperationalError as e:
    print(f"ℹ️  received_amount: {e}")

try:
    conn.execute("ALTER TABLE payment ADD COLUMN change_amount FLOAT DEFAULT 0.0")
    print("✅ Columna 'change_amount' añadida.")
except sqlite3.OperationalError as e:
    print(f"ℹ️  change_amount: {e}")

conn.commit()
conn.close()
print("🎉 Proceso de migración finalizado.")
