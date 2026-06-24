"""
migrate_hr_zones.py
-------------------
Agrega la columna hr_zone_times_by_sport a triathlon_new.db
y copia los datos desde triathlon_backup.db donde coincidan por fecha.

REQUIERE: Streamlit cerrado (Ctrl+C en la terminal).
Uso: python migrate_hr_zones.py
"""
import sqlite3
from pathlib import Path

DATA = Path(__file__).parent / "data"
NEW_DB    = DATA / "triathlon_new.db"
BACKUP_DB = DATA / "triathlon_backup.db"

# 1. Conectar a ambas DBs
new    = sqlite3.connect(str(NEW_DB))
backup = sqlite3.connect(str(BACKUP_DB))

# 2. Agregar columna si no existe
cols = [r[1] for r in new.execute("PRAGMA table_info(activities)").fetchall()]
if "hr_zone_times_by_sport" not in cols:
    new.execute("ALTER TABLE activities ADD COLUMN hr_zone_times_by_sport TEXT")
    print("Columna hr_zone_times_by_sport agregada.")
else:
    print("Columna ya existe.")

# 3. Leer datos del backup: {date -> hr_zone_times_by_sport}
backup_data = backup.execute(
    "SELECT date, hr_zone_times_by_sport FROM activities WHERE hr_zone_times_by_sport IS NOT NULL"
).fetchall()
backup_map = {row[0]: row[1] for row in backup_data}
print(f"Registros en backup con hr_zone: {len(backup_map)}")

# 4. Actualizar triathlon_new.db
updated = 0
for date_val, json_val in backup_map.items():
    result = new.execute(
        "UPDATE activities SET hr_zone_times_by_sport = ? WHERE date = ? AND hr_zone_times_by_sport IS NULL",
        (json_val, date_val)
    )
    updated += result.rowcount

new.commit()
print(f"Actividades actualizadas: {updated}")

total_with = new.execute(
    "SELECT COUNT(*) FROM activities WHERE hr_zone_times_by_sport IS NOT NULL"
).fetchone()[0]
total = new.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
print(f"Total actividades con hr_zone: {total_with}/{total}")

new.close()
backup.close()
print("\nMigracion completa. Puedes volver a abrir Streamlit.")
