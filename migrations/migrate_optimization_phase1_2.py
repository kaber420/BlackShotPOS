"""
migrate_optimization_phase1_2.py
--------------------------------
Añade la columna `sku` a la tabla `product` y crea los índices necesarios para 
la optimización del backend (Fases 1 y 2).
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'pos_database.db')

MIGRATIONS = [
    # ── Tabla Product ──────────────────────────────────────────────────────────
    "ALTER TABLE product ADD COLUMN sku TEXT",
    "CREATE INDEX ix_product_sku ON product (sku)",
    "CREATE INDEX ix_product_is_active ON product (is_active)",
    "CREATE INDEX ix_product_category_id ON product (category_id)",
    "CREATE INDEX ix_product_name ON product (name)",

    # ── Tabla Order ────────────────────────────────────────────────────────────
    "CREATE INDEX ix_order_status ON \"order\" (status)",
    "CREATE INDEX ix_order_table_id ON \"order\" (table_id)",
    "CREATE INDEX ix_order_created_at ON \"order\" (created_at)",

    # ── Tabla OrderItem ────────────────────────────────────────────────────────
    "CREATE INDEX ix_orderitem_order_id ON orderitem (order_id)",

    # ── Tabla Payment ──────────────────────────────────────────────────────────
    "CREATE INDEX ix_payment_order_id ON payment (order_id)",
    "CREATE INDEX ix_payment_timestamp ON payment (timestamp)",
]

def run():
    if not os.path.exists(DB_PATH):
        print(f"❌  Base de datos no encontrada en: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    ok = 0
    skipped = 0
    for sql in MIGRATIONS:
        try:
            conn.execute(sql)
            conn.commit()
            print(f"✅  {sql[:70]}...")
            ok += 1
        except sqlite3.OperationalError as e:
            # print(f"ℹ️   Ignorado (ya existe): {e}")
            skipped += 1
    conn.close()
    print(f"\n🏁  Migración de optimización completada — {ok} aplicadas, {skipped} ignoradas.")

if __name__ == "__main__":
    run()
