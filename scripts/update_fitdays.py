#!/usr/bin/env python3
"""
update_fitdays.py — Inserta o actualiza datos de composición corporal (Fitdays)
Uso: python update_fitdays.py

Cuando tengas una medición nueva de Fitdays, corre este script
o edita directamente el INSERT al final del archivo.
"""

import sqlite3, sys
from datetime import date
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent))

try:
    from config import DB_PATH
except ImportError:
    DB_PATH = "data/triathlon.db"


def ensure_schema(conn):
    """Crea las tablas si no existen."""
    schema_path = Path(__file__).parent / "schema.sql"
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.commit()


def get_conn():
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    ensure_schema(conn)
    return conn


def insert_measurement(data: dict):
    """Inserta una medición de Fitdays en la base de datos."""
    conn = get_conn()

    conn.execute("""
        INSERT OR REPLACE INTO body_composition
        (date, weight_kg, body_fat_pct, muscle_mass_kg, skeletal_muscle_kg,
         tbw_pct, visceral_fat, bmr_kcal, bone_mass_kg, body_age, bmi, notes)
        VALUES
        (:date, :weight_kg, :body_fat_pct, :muscle_mass_kg, :skeletal_muscle_kg,
         :tbw_pct, :visceral_fat, :bmr_kcal, :bone_mass_kg, :body_age, :bmi, :notes)
    """, data)

    conn.commit()
    conn.close()
    print(f"✓ Medición {data['date']} guardada correctamente")


def show_last(n=5):
    """Muestra las últimas N mediciones."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT date, weight_kg, body_fat_pct, muscle_mass_kg,
               skeletal_muscle_kg, tbw_pct, visceral_fat
        FROM body_composition
        ORDER BY date DESC
        LIMIT ?
    """, (n,)).fetchall()
    conn.close()

    print(f"\n{'─'*75}")
    print(f"{'Fecha':<12} {'Peso':>6} {'Grasa%':>7} {'MM':>7} {'ME':>7} {'TBW%':>6} {'GV':>4}")
    print(f"{'─'*75}")
    for r in rows:
        print(f"{r[0]:<12} {r[1] or '—':>6} {r[2] or '—':>7} {r[3] or '—':>7} "
              f"{r[4] or '—':>7} {r[5] or '—':>6} {r[6] or '—':>4}")
    print(f"{'─'*75}\n")


if __name__ == "__main__":

    # ── HISTORIAL INICIAL (datos ya conocidos) ────────────────
    historical = [
        {"date": "2026-01-15", "weight_kg": 83.23, "body_fat_pct": 13.5,
         "muscle_mass_kg": None, "skeletal_muscle_kg": 67.2,
         "tbw_pct": None, "visceral_fat": None, "bmr_kcal": 1925,
         "bone_mass_kg": None, "body_age": None, "bmi": None,
         "notes": "Inicio post diciembre"},

        {"date": "2026-02-02", "weight_kg": 82.87, "body_fat_pct": 14.0,
         "muscle_mass_kg": 66.5, "skeletal_muscle_kg": 40.9,
         "tbw_pct": None, "visceral_fat": 3, "bmr_kcal": 1909,
         "bone_mass_kg": None, "body_age": None, "bmi": None,
         "notes": "Ajuste inicial"},

        {"date": "2026-02-16", "weight_kg": 82.78, "body_fat_pct": 13.4,
         "muscle_mass_kg": 66.9, "skeletal_muscle_kg": 41.2,
         "tbw_pct": 63.5, "visceral_fat": 3, "bmr_kcal": 1918,
         "bone_mass_kg": None, "body_age": None, "bmi": None,
         "notes": "Recomposición positiva"},

        {"date": "2026-02-23", "weight_kg": 81.49, "body_fat_pct": 13.2,
         "muscle_mass_kg": 65.9, "skeletal_muscle_kg": 40.6,
         "tbw_pct": None, "visceral_fat": 2, "bmr_kcal": 1896,
         "bone_mass_kg": None, "body_age": None, "bmi": None,
         "notes": "Déficit más agresivo"},

        {"date": "2026-03-09", "weight_kg": 82.55, "body_fat_pct": 13.7,
         "muscle_mass_kg": 66.6, "skeletal_muscle_kg": 40.9,
         "tbw_pct": 63.3, "visceral_fat": 3, "bmr_kcal": 1909,
         "bone_mass_kg": None, "body_age": None, "bmi": None,
         "notes": "Recuperación de masa"},

        {"date": "2026-03-23", "weight_kg": 81.74, "body_fat_pct": 13.3,
         "muscle_mass_kg": 66.0, "skeletal_muscle_kg": None,
         "tbw_pct": 63.5, "visceral_fat": 2, "bmr_kcal": None,
         "bone_mass_kg": None, "body_age": None, "bmi": None,
         "notes": None},

        {"date": "2026-03-30", "weight_kg": 82.03, "body_fat_pct": 13.2,
         "muscle_mass_kg": 66.5, "skeletal_muscle_kg": None,
         "tbw_pct": 63.6, "visceral_fat": 2, "bmr_kcal": None,
         "bone_mass_kg": None, "body_age": None, "bmi": None,
         "notes": None},

        {"date": "2026-04-06", "weight_kg": 82.22, "body_fat_pct": 13.4,
         "muscle_mass_kg": 66.4, "skeletal_muscle_kg": None,
         "tbw_pct": 63.5, "visceral_fat": 2, "bmr_kcal": None,
         "bone_mass_kg": None, "body_age": None, "bmi": None,
         "notes": None},

        {"date": "2026-04-13", "weight_kg": 82.36, "body_fat_pct": 13.5,
         "muscle_mass_kg": 66.4, "skeletal_muscle_kg": 40.9,
         "tbw_pct": 63.4, "visceral_fat": 3, "bmr_kcal": None,
         "bone_mass_kg": None, "body_age": None, "bmi": None,
         "notes": None},

        {"date": "2026-05-11", "weight_kg": 82.52, "body_fat_pct": 13.9,
         "muscle_mass_kg": 66.3, "skeletal_muscle_kg": 40.8,
         "tbw_pct": 63.1, "visceral_fat": 3, "bmr_kcal": None,
         "bone_mass_kg": None, "body_age": None, "bmi": None,
         "notes": "Post-Malinche + vacaciones Italia"},

        {"date": "2026-05-25", "weight_kg": 82.74, "body_fat_pct": 14.2,
         "muscle_mass_kg": 66.2, "skeletal_muscle_kg": 40.8,
         "tbw_pct": 62.9, "visceral_fat": 3, "bmr_kcal": 1904,
         "bone_mass_kg": None, "body_age": 33, "bmi": None,
         "notes": "Baseline Ticoman — TBW en mínimo histórico"},
    ]

    print("\nCargando historial completo de Fitdays...")
    for entry in historical:
        insert_measurement(entry)

    print("\nÚltimas mediciones en DB:")
    show_last(10)
