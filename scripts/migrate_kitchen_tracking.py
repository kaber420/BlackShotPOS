"""
migrate_kitchen_tracking.py
----------------------------
Añade campos de rastreo del cocinero a las tablas `order` y `orderitem`.

REQUISITO: Ejecutar migrate_waiter_tracking.py primero.
Los campos de timestamps (preparing_at, ready_at, delivered_at) ya los crea ese script.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'pos_database.db')

MIGRATIONS = [
    # ── Tabla Order ───────────────────────────────────────────────────────────
    # ¿Quién tomó/preparó la orden en cocina?
    "ALTER TABLE `order` ADD COLUMN cook_uuid TEXT",
    "ALTER TABLE `order` ADD COLUMN cook_name TEXT",

    # ── Tabla OrderItem ───────────────────────────────────────────────────────
    # ¿Qué cocinero preparó cada ítem individual?
    "ALTER TABLE orderitem ADD COLUMN cook_uuid TEXT",
    "ALTER TABLE orderitem ADD COLUMN cook_name TEXT",
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
    print(f"\n🏁  Migración de cocina completada — {ok} aplicadas, {skipped} ignoradas.")

if __name__ == "__main__":
    run()
