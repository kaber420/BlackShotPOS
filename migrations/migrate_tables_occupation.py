import sqlite3

db_path = "./pos_database.db"
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(\"table\")")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "occupied_at" not in columns:
        print("Adding occupied_at column to table...")
        cursor.execute("ALTER TABLE \"table\" ADD COLUMN occupied_at DATETIME")
        conn.commit()
        print("Column added successfully.")
    else:
        print("Column occupied_at already exists.")
        
    conn.close()
except Exception as e:
    print(f"Error during migration: {e}")
