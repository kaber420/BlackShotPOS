import sqlite3
import os

db_path = "pos_database.db"
if not os.path.exists(db_path):
    print("DB not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT token FROM iotdevice LIMIT 1;")
        row = cursor.fetchone()
        if row:
            print(f"TOKEN: {row[0]}")
        else:
            print("No devices found")
    except Exception as e:
        print(f"Error: {e}")
    conn.close()
