import sqlite3
import os

def update_inventory_schema():
    db_path = "pos_database.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Updating Inventory Schema ---")

    # 1. Create InventoryCategory table
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventorycategory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR NOT NULL UNIQUE,
            description VARCHAR
        );
        """)
        print("✓ Table 'inventorycategory' ensured.")
    except Exception as e:
        print(f"✗ Error creating 'inventorycategory': {e}")

    # 2. Add category_id to ingredient
    try:
        cursor.execute("ALTER TABLE ingredient ADD COLUMN category_id INTEGER REFERENCES inventorycategory(id);")
        print("✓ Column 'category_id' added to 'ingredient'.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("! Column 'category_id' already exists in 'ingredient'.")
        else:
            print(f"✗ Error adding column 'category_id': {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")

    # 3. Migrate existing categories to the new table
    try:
        cursor.execute("SELECT DISTINCT category FROM ingredient WHERE category IS NOT NULL;")
        categories = cursor.fetchall()
        for (cat_name,) in categories:
            try:
                cursor.execute("INSERT OR IGNORE INTO inventorycategory (name) VALUES (?);", (cat_name,))
                print(f"✓ Migrated category string to table: {cat_name}")
            except Exception as e:
                print(f"✗ Error migrating category '{cat_name}': {e}")
        
        # 4. Link ingredients to category_id
        cursor.execute("""
            UPDATE ingredient 
            SET category_id = (SELECT id FROM inventorycategory WHERE inventorycategory.name = ingredient.category)
            WHERE category_id IS NULL;
        """)
        print("✓ Linked ingredients to new category IDs.")
        
    except Exception as e:
        print(f"✗ Error during data migration: {e}")
        
    conn.commit()
    conn.close()
    print("--- Schema Update Completed ---")

if __name__ == "__main__":
    update_inventory_schema()
