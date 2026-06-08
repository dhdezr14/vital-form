#!/usr/bin/env python3
"""
migrate_to_sheets.py — Migra datos de triathlon.db a Google Sheets
"""

import sqlite3
import sys
import requests
import json
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except:
    pass

if len(sys.argv) < 2:
    print("ERROR: Necesitas pasar la URL del Apps Script")
    print("Uso: python migrate_to_sheets.py <APPS_SCRIPT_URL>")
    sys.exit(1)

APPS_SCRIPT_URL = sys.argv[1]
DB_PATH = "data/triathlon.db"

print(f"\n{'='*60}")
print(f"  MIGRAR DATOS A GOOGLE SHEETS")
print(f"  Apps Script URL: {APPS_SCRIPT_URL[:50]}...")
print(f"{'='*60}\n")

try:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    print(f"OK Conectado a {DB_PATH}")
except Exception as e:
    print(f"ERROR: No se pudo conectar a {DB_PATH}")
    print(f"  {e}")
    sys.exit(1)

print("\n[1/2] Migrando WELLNESS...")

try:
    cursor.execute("""
        SELECT date, ctl, atl, tsb, eftp, hrv, rhr, sleep_secs, stress_avg
        FROM wellness
        WHERE date IS NOT NULL
        ORDER BY date
    """)
    
    wellness_rows = cursor.fetchall()
    wellness_count = 0
    
    for row in wellness_rows:
        payload = {
            "type": "wellness",
            "date": row["date"],
            "ctl": row["ctl"],
            "atl": row["atl"],
            "tsb": row["tsb"],
            "eftp": row["eftp"],
            "hrv": row["hrv"],
            "rhr": row["rhr"],
            "sleep_secs": row["sleep_secs"],
            "stress_avg": row["stress_avg"]
        }
        
        try:
            response = requests.post(APPS_SCRIPT_URL, json=payload, timeout=10)
            if response.status_code == 200:
                wellness_count += 1
                if wellness_count % 10 == 0:
                    print(f"  [{wellness_count}/{len(wellness_rows)}] {row['date']}")
            else:
                print(f"  ERROR en {row['date']}: {response.status_code}")
        except Exception as e:
            print(f"  ERROR POST en {row['date']}: {e}")
    
    print(f"  OK {wellness_count} registros wellness insertados")
    
except Exception as e:
    print(f"  ERROR al leer wellness: {e}")

print("\n[2/2] Migrando COMPOSICION CORPORAL...")

try:
    cursor.execute("""
        SELECT date, weight_kg, body_fat_pct, muscle_mass_kg, 
               skeletal_muscle_kg, tbw_pct, visceral_fat, bmr_kcal, body_age, bmi
        FROM body_composition
        WHERE date IS NOT NULL
        ORDER BY date
    """)
    
    bodycomp_rows = cursor.fetchall()
    bodycomp_count = 0
    
    for row in bodycomp_rows:
        payload = {
            "type": "body_comp",
            "date": row["date"],
            "weight_kg": row["weight_kg"],
            "body_fat_pct": row["body_fat_pct"],
            "muscle_mass_kg": row["muscle_mass_kg"],
            "skeletal_muscle_kg": row["skeletal_muscle_kg"],
            "tbw_pct": row["tbw_pct"],
            "visceral_fat": row["visceral_fat"],
            "bmr_kcal": row["bmr_kcal"],
            "body_age": row["body_age"],
            "bmi": row["bmi"]
        }
        
        try:
            response = requests.post(APPS_SCRIPT_URL, json=payload, timeout=10)
            if response.status_code == 200:
                bodycomp_count += 1
                if bodycomp_count % 5 == 0:
                    print(f"  [{bodycomp_count}/{len(bodycomp_rows)}] {row['date']}")
            else:
                print(f"  ERROR en {row['date']}: {response.status_code}")
        except Exception as e:
            print(f"  ERROR POST en {row['date']}: {e}")
    
    print(f"  OK {bodycomp_count} registros composicion insertados")
    
except Exception as e:
    print(f"  ERROR al leer composicion: {e}")

conn.close()

print(f"\n{'='*60}")
print(f"  MIGRACION COMPLETA")
print(f"{'='*60}\n")
print(f"Abre tu dashboard:")
print(f"  {APPS_SCRIPT_URL}\n")