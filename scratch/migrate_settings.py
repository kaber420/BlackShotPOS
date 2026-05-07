import sqlite3
import os

db_path = "pos_database.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE businesssettings ADD COLUMN menu_title VARCHAR DEFAULT 'Nuestra Selección'")
        cursor.execute("ALTER TABLE businesssettings ADD COLUMN menu_subtitle VARCHAR DEFAULT 'Preparado con pasión, servido con arte.'")
        conn.commit()
        print("Columns added successfully.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Columns already exist.")
        else:
            print(f"Error: {e}")
    finally:
        conn.close()
else:
    print("Database not found.")
