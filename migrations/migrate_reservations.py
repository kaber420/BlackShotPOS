import sqlite3
import os

db_path = "./pos_database.db"

def migrate():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Skipping migration.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reservation'")
        if cursor.fetchone():
            print("Table 'reservation' already exists. Skipping creation.")
        else:
            print("Creating 'reservation' table...")
            cursor.execute("""
            CREATE TABLE reservation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name VARCHAR NOT NULL,
                customer_phone VARCHAR,
                customer_id VARCHAR,
                table_id INTEGER,
                pax INTEGER DEFAULT 2,
                reservation_time DATETIME NOT NULL,
                status VARCHAR DEFAULT 'PENDING',
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                organization_id VARCHAR DEFAULT 'default',
                is_synced BOOLEAN DEFAULT 0,
                FOREIGN KEY(table_id) REFERENCES "table"(id),
                FOREIGN KEY(customer_id) REFERENCES customer(id)
            )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX idx_reservation_customer_name ON reservation(customer_name)")
            cursor.execute("CREATE INDEX idx_reservation_table_id ON reservation(table_id)")
            cursor.execute("CREATE INDEX idx_reservation_reservation_time ON reservation(reservation_time)")
            cursor.execute("CREATE INDEX idx_reservation_organization_id ON reservation(organization_id)")
            
            conn.commit()
            print("Table 'reservation' created successfully.")
            
        conn.close()
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate()
