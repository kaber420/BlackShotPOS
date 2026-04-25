import sqlite3

def migrate():
    conn = sqlite3.connect('pos_database.db')
    cursor = conn.cursor()
    
    print("Starting migration of recipeitem table...")
    
    # 1. Rename existing table
    try:
        cursor.execute("ALTER TABLE recipeitem RENAME TO recipeitem_old;")
        print("Renamed recipeitem to recipeitem_old.")
    except sqlite3.OperationalError as e:
        print(f"Error renaming table (maybe it already exists?): {e}")

    # 2. Create new table with nullable ingredient_id
    cursor.execute("""
    CREATE TABLE recipeitem (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        variant_id INTEGER,
        ingredient_id INTEGER,
        modifier_group_id INTEGER,
        quantity FLOAT NOT NULL,
        FOREIGN KEY(product_id) REFERENCES product (id),
        FOREIGN KEY(variant_id) REFERENCES productvariant (id),
        FOREIGN KEY(ingredient_id) REFERENCES ingredient (id),
        FOREIGN KEY(modifier_group_id) REFERENCES modifiergroup (id) ON DELETE CASCADE
    );
    """)
    print("Created new recipeitem table with nullable ingredient_id.")

    # 3. Copy data
    cursor.execute("PRAGMA table_info(recipeitem_old);")
    old_cols = [col[1] for col in cursor.fetchall()]
    common_cols = [col for col in old_cols if col in ['id', 'product_id', 'variant_id', 'ingredient_id', 'modifier_group_id', 'quantity']]
    
    cols_str = ", ".join(common_cols)
    cursor.execute(f"INSERT INTO recipeitem ({cols_str}) SELECT {cols_str} FROM recipeitem_old;")
    print(f"Copied data from recipeitem_old to recipeitem. Columns: {cols_str}")

    # 4. Drop old table
    cursor.execute("DROP TABLE recipeitem_old;")
    print("Dropped recipeitem_old.")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate()
