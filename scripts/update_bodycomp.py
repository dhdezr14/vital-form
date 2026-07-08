#!/usr/bin/env python3
"""
update_bodycomp.py - Pipeline Fitdays -> body_composition (data/triathlon.db)

1. Corre Fitdays/consolidate_fitdays.py (lee todos los .csv de Fitdays/,
   deduplica y regenera fitdays_db.csv).
2. Inserta en body_composition las fechas que aun no existen en la BD,
   usando la primera medicion del dia (primera_del_dia=1).

Idempotente: correr N veces no duplica nada.
Se usa tanto local como en GitHub Actions (requiere: pip install xlrd).

Uso: python scripts/update_bodycomp.py
"""

import csv
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("VF_DB_PATH", str(ROOT / "data" / "triathlon.db")))
FITDAYS_CSV = ROOT / "fitdays_db.csv"
CONSOLIDATOR = ROOT / "Fitdays" / "consolidate_fitdays.py"

# Mapa columna fitdays_db.csv -> columna body_composition
COLUMN_MAP = {
    "peso_kg":                 "weight_kg",
    "grasa_corporal_pct":      "body_fat_pct",
    "masa_muscular_kg":        "muscle_mass_kg",
    "musculo_esqueletico_pct": "skeletal_muscle_kg",
    "agua_corporal_pct":       "tbw_pct",
    "grasa_visceral":          "visceral_fat",
    "bmr_kcal":                "bmr_kcal",
    "imc":                     "bmi",
    "edad_corporal":           "body_age",
    "grasa_subcutanea_pct":    "grasa_subcutanea_pct",
    "proteina_pct":            "proteina_pct",
    "masa_grasa_kg":           "masa_grasa_kg",
    "contenido_agua_kg":       "contenido_agua_kg",
    "smi_kg_m2":               "smi_kg_m2",
    "puntuacion_corporal":     "puntuacion_corporal",
    "obesidad_score":          "obesidad_score",
}


def run_consolidator():
    print(">> Consolidando archivos Fitdays...")
    result = subprocess.run(
        [sys.executable, str(CONSOLIDATOR)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        sys.exit("ERROR: fallo consolidate_fitdays.py")
    # Ultimas lineas del resumen
    for line in result.stdout.strip().splitlines()[-8:]:
        print("   " + line)


def load_first_of_day():
    rows = {}
    with open(FITDAYS_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("primera_del_dia") == "1":
                rows[r["fecha"]] = r
    return rows


def upsert(rows):
    conn = sqlite3.connect(str(DB_PATH))
    # journal DELETE: la BD viaja commiteada en git, WAL dejaria writes fuera del .db
    conn.execute("PRAGMA journal_mode=DELETE")
    existing = {d for (d,) in conn.execute("SELECT date FROM body_composition")}
    new_dates = sorted(set(rows) - existing)

    if not new_dates:
        print(">> body_composition ya esta al dia (sin fechas nuevas)")
        conn.close()
        return 0

    for d in new_dates:
        r = rows[d]
        data = {"date": d}
        for src, dst in COLUMN_MAP.items():
            v = r.get(src, "")
            if v not in ("", None):
                try:
                    data[dst] = float(v)
                except ValueError:
                    pass
        cols = ", ".join(data)
        ph = ", ".join(["?"] * len(data))
        conn.execute(
            f"INSERT INTO body_composition ({cols}) VALUES ({ph})",
            list(data.values()),
        )
        print(f"   + {d}  peso={data.get('weight_kg')}  grasa={data.get('body_fat_pct')}%")

    conn.commit()
    total, last = conn.execute(
        "SELECT COUNT(*), MAX(date) FROM body_composition"
    ).fetchone()
    conn.close()
    print(f">> Insertadas {len(new_dates)} mediciones. Total: {total}, ultima: {last}")
    return len(new_dates)


if __name__ == "__main__":
    if not DB_PATH.exists():
        sys.exit(f"ERROR: no existe {DB_PATH}")
    run_consolidator()
    upsert(load_first_of_day())
