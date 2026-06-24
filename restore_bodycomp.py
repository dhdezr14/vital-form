#!/usr/bin/env python3
"""Restaura datos de body_composition de BD vieja a BD nueva"""

import sqlite3

OLD_DB = r"C:\vital-form-streamlit\data\triathlon - copia.db"
NEW_DB = r"C:\vital-form-streamlit\data\triathlon.db"

print(f"Restaurando body_composition...")
print(f"  Origen: {OLD_DB}")
print(f"  Destino: {NEW_DB}\n")

try:
    # Conectar a BD vieja
    old_conn = sqlite3.connect(OLD_DB)
    old_cursor = old_conn.cursor()
    
    # Columnas que existen en ambas BDs (excluyendo 'notes')
    columns = [
        'date', 'weight_kg', 'body_fat_pct', 'muscle_mass_kg',
        'skeletal_muscle_kg', 'tbw_pct', 'visceral_fat', 
        'bmr_kcal', 'bmi', 'bone_mass_kg', 'body_age'
    ]
    
    # Leer datos de BD vieja
    col_names_str = ", ".join(columns)
    old_cursor.execute(f"SELECT {col_names_str} FROM body_composition")
    rows = old_cursor.fetchall()
    
    if not rows:
        print("❌ No hay datos de body_composition en la BD vieja")
        old_conn.close()
        exit(1)
    
    print(f"✓ Se encontraron {len(rows)} registros de body_composition")
    
    # Conectar a BD nueva
    new_conn = sqlite3.connect(NEW_DB)
    new_cursor = new_conn.cursor()
    
    # Insertar datos
    placeholders = ", ".join(["?" for _ in columns])
    query = f"INSERT OR REPLACE INTO body_composition ({col_names_str}) VALUES ({placeholders})"
    new_cursor.executemany(query, rows)
    new_conn.commit()
    
    print(f"✓ {len(rows)} registros restaurados exitosamente")
    
    # Verificar
    new_cursor.execute("SELECT COUNT(*) FROM body_composition")
    count = new_cursor.fetchone()[0]
    print(f"✓ BD nueva ahora tiene {count} registros de body_composition\n")
    
    old_conn.close()
    new_conn.close()
    
    print("✅ Restauración completada")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
