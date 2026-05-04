import sqlite3

db_path = "pos_database.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables = ["product", "order", "orderitem", "payment"]

for table in tables:
    print(f"\n--- Schema for table: {table} ---")
    cursor.execute(f'PRAGMA table_info("{table}")')
    columns = cursor.fetchall()
    for col in columns:
        print(f"Column: {col[1]}, Type: {col[2]}")
    
    print(f"\n--- Indices for table: {table} ---")
    cursor.execute(f'PRAGMA index_list("{table}")')
    indices = cursor.fetchall()
    for idx in indices:
        idx_name = idx[1]
        cursor.execute(f'PRAGMA index_info("{idx_name}")')
        idx_info = cursor.fetchall()
        cols = ", ".join([c[2] for c in idx_info])
        print(f"Index: {idx_name}, Columns: ({cols}), Unique: {idx[2]}")

conn.close()
