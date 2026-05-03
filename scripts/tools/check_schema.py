import sqlite3
import os

DB_PATH = "pos_database.db"

def check():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    tables = [
        'category', 
        'product', 
        'ingredient', 
        'modifiergroup', 
        'modifier', 
        'recipeitem', 
        'productmodifierlink', 
        'pospreset'
    ]
    
    for table in tables:
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            print(f"Table '{table}': {columns}")
        except Exception as e:
            print(f"Error checking table '{table}': {e}")
            
    conn.close()

if __name__ == "__main__":
    check()
