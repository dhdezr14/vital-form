#!/usr/bin/env python3
"""
Extrae la estructura completa de un archivo Fitdays
Muestra todas las columnas, secciones y valores para análisis
"""

import sys
from pathlib import Path

def extract_fitdays_structure(file_path):
    """Lee archivo Fitdays y extrae estructura completa"""
    
    try:
        try:
    import xlrd
    print(f"Leyendo con xlrd: {file_path}\n")
    book = xlrd.open_workbook(file_path)
    ws = book.sheet_by_index(0)
    
    print(f"Hoja: {ws.name}")
    print(f"Filas: {ws.nrows}, Columnas: {ws.ncols}\n")
    
    print("="*100)
    print("CONTENIDO COMPLETO (FILA POR FILA)")
    print("="*100 + "\n")
    
    # Leer fila por fila
    for row_idx in range(ws.nrows):
        row_data = [(col_idx+1, ws.cell_value(row_idx, col_idx)) for col_idx in range(ws.ncols) if ws.cell_value(row_idx, col_idx)]
        
        if row_data:
            print(f"FILA {row_idx+1}:")
            for col_idx, value in row_data:
                print(f"  Col {col_idx}: {str(value)[:80]}")
            print()
    
    print("\n" + "="*100)
    print("DATOS ÚNICOS (sin duplicados, sin vacíos)")
    print("="*100 + "\n")
    
    # Recolectar todos los datos únicos
    all_values = set()
    for row_idx in range(ws.nrows):
        for col_idx in range(ws.ncols):
            value = ws.cell_value(row_idx, col_idx)
            if value and str(value).strip():
                all_values.add(str(value).strip())
    
    # Ordenar y mostrar
    for i, value in enumerate(sorted(all_values), 1):
        if len(value) > 1:
            print(f"{i:3d}. {value[:100]}")
        
        print(f"Hoja: {ws.title}")
        print(f"Dimensiones: {ws.dimensions}")
        print(f"Filas: {ws.max_row}, Columnas: {ws.max_column}\n")
        
        print("="*100)
        print("CONTENIDO COMPLETO (FILA POR FILA)")
        print("="*100 + "\n")
        
        # Leer fila por fila
        for row_idx, row in enumerate(ws.iter_rows(values_only=False), 1):
            # Filtrar filas vacías
            row_data = [(col_idx, cell.value) for col_idx, cell in enumerate(row, 1) if cell.value]
            
            if row_data:
                print(f"FILA {row_idx}:")
                for col_idx, value in row_data:
                    print(f"  Col {col_idx}: {str(value)[:80]}")
                print()
        
        print("\n" + "="*100)
        print("DATOS ÚNICOS (sin duplicados, sin vacíos)")
        print("="*100 + "\n")
        
        # Recolectar todos los datos únicos
        all_values = set()
        for row in ws.iter_rows(values_only=True):
            for cell in row:
                if cell and str(cell).strip():
                    all_values.add(str(cell).strip())
        
        # Ordenar y mostrar
        for i, value in enumerate(sorted(all_values), 1):
            if len(value) > 1:  # Mostrar valores con más de 1 carácter
                print(f"{i:3d}. {value[:100]}")
        
        print("\n" + "="*100)
        print("PRÓXIMO PASO")
        print("="*100)
        print("\nBasándome en esta estructura, puedo crear un schema de BD")
        print("que capture TODOS estos datos de forma organizada.\n")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    file_path = r"C:\vital-form-streamlit\Fitdays\6_17_26.csv"
    
    if not Path(file_path).exists():
        print(f"ERROR: Archivo no existe: {file_path}")
        sys.exit(1)
    
    extract_fitdays_structure(file_path)
