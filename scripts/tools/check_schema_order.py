import sqlite3
import os

DB_PATH = os.path.abspath("pos_database.db")

def check():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(`order`)")
    columns = [row[1] for row in cursor.fetchall()]
    print("Columns in 'order' table:")
    for col in columns:
        print(f" - {col}")
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print("\nTables in database:")
    for table in tables:
        print(f" - {table}")
    
    conn.close()

if __name__ == "__main__":
    check()
