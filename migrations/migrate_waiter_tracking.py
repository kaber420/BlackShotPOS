"""
migrate_waiter_tracking.py
--------------------------
Añade campos de rastreo de mesero y timestamps de ciclo de vida
a las tablas `order` y `orderitem`.

Ejecutar ANTES de migrate_kitchen_tracking.py.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'pos_database.db')

MIGRATIONS = [
    # ── Tabla Order ───────────────────────────────────────────────────────────
    # ¿Quién creó la orden?
    "ALTER TABLE `order` ADD COLUMN waiter_uuid TEXT",
    "ALTER TABLE `order` ADD COLUMN waiter_name TEXT",
    # Timestamps de ciclo de vida de la orden completa
    "ALTER TABLE `order` ADD COLUMN preparing_at DATETIME",
    "ALTER TABLE `order` ADD COLUMN ready_at DATETIME",
    "ALTER TABLE `order` ADD COLUMN delivered_at DATETIME",

    # ── Tabla OrderItem ───────────────────────────────────────────────────────
    # ¿Quién entregó este ítem al cliente?
    "ALTER TABLE orderitem ADD COLUMN delivered_by_uuid TEXT",
    "ALTER TABLE orderitem ADD COLUMN delivered_by_name TEXT",
    # Timestamps de ciclo de vida por ítem (granularidad para analytics de cocina)
    "ALTER TABLE orderitem ADD COLUMN preparing_at DATETIME",
    "ALTER TABLE orderitem ADD COLUMN ready_at DATETIME",
    "ALTER TABLE orderitem ADD COLUMN delivered_at DATETIME",
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
            print(f"ℹ️   Ignorado (ya existe): {e}")
            skipped += 1
    conn.close()
    print(f"\n🏁  Migración de meseros completada — {ok} aplicadas, {skipped} ignoradas.")

if __name__ == "__main__":
    run()
