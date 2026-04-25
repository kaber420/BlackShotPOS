import sqlite3
import os

def update_schema():
    conn = sqlite3.connect("pos_database.db")
    cursor = conn.cursor()
    
    # 1. Add nutrition columns to Product
    columns_product = ["protein", "calories", "carbs", "fats"]
    for col in columns_product:
        try:
            cursor.execute(f"ALTER TABLE product ADD COLUMN {col} FLOAT DEFAULT 0.0;")
            print(f"Added column {col} to product")
        except sqlite3.OperationalError:
            print(f"Column {col} already exists in product")

    # 2. Add image_url to ProductVariant
    try:
        cursor.execute("ALTER TABLE productvariant ADD COLUMN image_url TEXT;")
        print("Added column image_url to productvariant")
    except sqlite3.OperationalError:
        print("Column image_url already exists in productvariant")
        
    # 3. Create ModifierQuantity table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS modifierquantity (
        modifier_id INTEGER NOT NULL,
        measure_id INTEGER NOT NULL,
        quantity FLOAT NOT NULL,
        PRIMARY KEY (modifier_id, measure_id),
        FOREIGN KEY(modifier_id) REFERENCES modifier (id),
        FOREIGN KEY(measure_id) REFERENCES measure (id)
    );
    """)
    print("Ensured modifierquantity table exists")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_schema()
