#!/usr/bin/env python3
import sqlite3
from pathlib import Path

consolidated_db = r"C:\vital-form-streamlit\fitdays_consolidated.db"
main_db = r"C:\vital-form-streamlit\data\triathlon.db"

print("\n" + "="*70)
print("INTEGRADOR: Fitdays → BD Principal")
print("="*70 + "\n")

if not Path(consolidated_db).exists():
    print(f"ERROR: {consolidated_db} no existe")
    print("Primero ejecuta: consolidate_fitdays_FINAL.py")
    exit(1)

if not Path(main_db).exists():
    print(f"ERROR: {main_db} no existe")
    exit(1)

print("Leyendo datos consolidados...")
consolidated_conn = sqlite3.connect(consolidated_db)
consolidated_conn.row_factory = sqlite3.Row
c_consolidated = consolidated_conn.cursor()

c_consolidated.execute("SELECT * FROM fitdays_measurements ORDER BY measurement_date")
rows = c_consolidated.fetchall()

print(f"Encontradas {len(rows)} mediciones\n")

# Conectar a BD principal
main_conn = sqlite3.connect(main_db)
c_main = main_conn.cursor()

# Mapeo de columnas
column_mapping = {
    'measurement_date': 'date',
    'weight_kg': 'weight_kg',
    'body_fat_pct': 'body_fat_pct',
    'muscle_mass_kg': 'muscle_mass_kg',
    'skeletal_muscle_kg': 'skeletal_muscle_kg',
    'tbw_pct': 'tbw_pct',
    'visceral_fat_grade': 'visceral_fat',
    'bmr_kcal': 'bmr_kcal',
    'bmi': 'bmi',
    'body_age': 'body_age',
}

inserted = 0
skipped = 0

for row in rows:
    measurement_date = row['measurement_date']
    
    # Verificar si existe
    c_main.execute("SELECT COUNT(*) FROM body_composition WHERE date = ?", (measurement_date,))
    exists = c_main.fetchone()[0] > 0
    
    if exists:
        print(f"  SKIP {measurement_date} (ya existe)")
        skipped += 1
        continue
    
    # Preparar datos
    data = {'date': measurement_date}
    for fit_col, comp_col in column_mapping.items():
        if fit_col != 'measurement_date' and row[fit_col] is not None:
            data[comp_col] = row[fit_col]
    
    # Insertar
    if len(data) > 1:
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        values = list(data.values())
        
        try:
            c_main.execute(f"INSERT INTO body_composition ({columns}) VALUES ({placeholders})", values)
            print(f"  OK {measurement_date}")
            inserted += 1
        except Exception as e:
            print(f"  ERROR {measurement_date}: {e}")
    else:
        print(f"  SKIP {measurement_date} (sin datos)")
        skipped += 1

main_conn.commit()
main_conn.close()
consolidated_conn.close()

print("\n" + "="*70)
print(f"COMPLETADO")
print(f"• Insertados: {inserted}")
print(f"• Omitidos: {skipped}")
print("="*70 + "\n")
print("Abre Streamlit para ver los datos:")
print("  streamlit run app.py\n")
