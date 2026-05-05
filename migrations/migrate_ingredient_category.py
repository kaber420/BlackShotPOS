"""
Migración: Agrega columna category a la tabla ingredient.
Ejecutar una sola vez desde la raíz del proyecto:
    python migrations/migrate_ingredient_category.py
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'pos_database.db')
db_path = os.path.abspath(db_path)

print(f"Base de datos: {db_path}")

if not os.path.exists(db_path):
    print(f"❌ Error: No se encontró la base de datos en {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
try:
    # 1. Verificar si la columna ya existe
    cursor = conn.execute("PRAGMA table_info(ingredient)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'category' not in columns:
        # 2. Añadir la columna
        conn.execute("ALTER TABLE ingredient ADD COLUMN category VARCHAR DEFAULT 'Insumo'")
        conn.commit()
        print("✅ Columna 'category' añadida correctamente a la tabla 'ingredient'.")
        
        # 3. Crear índice para mejorar rendimiento de búsqueda
        try:
            conn.execute("CREATE INDEX ix_ingredient_category ON ingredient (category)")
            conn.commit()
            print("✅ Índice 'ix_ingredient_category' creado.")
        except sqlite3.OperationalError:
            print("ℹ️  El índice ya existe o no se pudo crear.")
    else:
        print("ℹ️  La columna 'category' ya existe — no se requiere acción.")

except sqlite3.OperationalError as e:
    print(f"❌ Error: {e}")
finally:
    conn.close()
