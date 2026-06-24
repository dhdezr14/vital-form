#!/usr/bin/env python3
"""
Consolidador de metricas Fitdays.
Lee todos los XLS (extension .csv), deduplica por timestamp y exporta a CSV.

Uso: python consolidate_fitdays.py
Para agregar mediciones: copia nuevo .csv a esta carpeta y vuelve a correr.
"""

import re
import unicodedata
import xlrd
import csv
from pathlib import Path
from datetime import datetime

FITDAYS_FOLDER = Path(__file__).parent
OUTPUT_CSV = FITDAYS_FOLDER.parent / "fitdays_db.csv"

# Mapa de nombre de columna normalizada (sin tildes) -> nombre en DB
COLUMN_MAP = {
    "peso":                          "peso_kg",
    "imc":                           "imc",
    "grasa corporal":                "grasa_corporal_pct",
    "grasa subcutanea":              "grasa_subcutanea_pct",
    "frecuencia cardiaca":           "frec_cardiaca",
    "indice cardiaco":               "indice_cardiaco",
    "grasa visceral":                "grasa_visceral",
    "agua corporal":                 "agua_corporal_pct",
    "musculo esqueletico":           "musculo_esqueletico_pct",
    "masa muscular":                 "masa_muscular_kg",
    "masa esqueletica":              "masa_esqueletica_kg",
    "proteina":                      "proteina_pct",
    "bmr":                           "bmr_kcal",
    "edad corporal":                 "edad_corporal",
    "masa grasa":                    "masa_grasa_kg",
    "contenido de agua":             "contenido_agua_kg",
    "frecuencia muscular":           "frec_muscular_pct",
    "cantidad de proteina":          "cantidad_proteina_kg",
    "obesidad":                      "obesidad_score",
    "perdida de grasa":              "perdida_grasa_kg",
    "smi":                           "smi_kg_m2",
    "puntuacion corporal":           "puntuacion_corporal",
    "peso objetivo recomendado":     "peso_objetivo_kg",
    "control de peso":               "control_peso_kg",
    "control de grasa":              "control_grasa_kg",
    "control muscular":              "control_muscular_kg",
    "right arm-analisis de obesidad segmentario": "seg_obesidad_brazo_der",
    "left arm-analisis de obesidad segmentario":  "seg_obesidad_brazo_izq",
    "trunk-analisis de obesidad segmentario":     "seg_obesidad_tronco",
    "right leg-analisis de obesidad segmentario": "seg_obesidad_pierna_der",
    "left leg-analisis de obesidad segmentario":  "seg_obesidad_pierna_izq",
    "right arm-equilibrio muscular":  "eq_muscular_brazo_der_pct",
    "left arm-equilibrio muscular":   "eq_muscular_brazo_izq_pct",
    "trunk-equilibrio muscular":      "eq_muscular_tronco_pct",
    "right leg-equilibrio muscular":  "eq_muscular_pierna_der_pct",
    "left leg-equilibrio muscular":   "eq_muscular_pierna_izq_pct",
    "right arm-impedancia bioelectrica": "impedancia_brazo_der",
    "left arm-impedancia bioelectrica":  "impedancia_brazo_izq",
    "trunk-impedancia bioelectrica":     "impedancia_tronco",
    "right leg-impedancia bioelectrica": "impedancia_pierna_der",
    "left leg-impedancia bioelectrica":  "impedancia_pierna_izq",
}

OUTPUT_COLS = (
    ["fecha", "hora", "primera_del_dia"]
    + list(COLUMN_MAP.values())
    + ["_source"]
)
# Deduplicar manteniendo orden
seen = set()
OUTPUT_COLS = [c for c in OUTPUT_COLS if not (c in seen or seen.add(c))]


def normalize(s):
    """Convierte a minusculas y quita tildes."""
    nfkd = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def clean_value(raw):
    s = str(raw).strip()
    if not s or s.lower() in ("nan", "none", "- -", "--"):
        return ""
    if re.match(r"^-?\d+\.?\d*/\d+\.?\d*$", s):
        return s
    m = re.search(r"(-?\d+\.?\d*)", s)
    return m.group(1) if m else ""


def parse_timestamp(raw):
    s = str(raw).strip()
    m = re.match(r"(\d{2}:\d{2})\s+(\d{2}/\d{2}/\d{4})", s)
    if not m:
        return None
    hora, fecha = m.group(1), m.group(2)
    try:
        dt = datetime.strptime("{} {}".format(fecha, hora), "%d/%m/%Y %H:%M")
        return dt, dt.strftime("%Y-%m-%d"), hora
    except ValueError:
        return None


def read_xls_file(path):
    try:
        wb = xlrd.open_workbook(str(path))
        ws = wb.sheet_by_index(0)
    except Exception as e:
        print("  WARNING {}: {}".format(path.name, e))
        return []
    if ws.nrows < 2:
        return []
    headers = [str(ws.cell_value(0, c)).strip() for c in range(ws.ncols)]
    records = []
    for r in range(1, ws.nrows):
        ts = parse_timestamp(ws.cell_value(r, 0))
        if not ts:
            continue
        dt_obj, fecha, hora = ts
        row = {"fecha": fecha, "hora": hora, "_dt": dt_obj, "_source": path.name}
        for c in range(1, ws.ncols):
            h = headers[c] if c < len(headers) else "col_{}".format(c)
            col_name = COLUMN_MAP.get(normalize(h), normalize(h))
            row[col_name] = clean_value(ws.cell_value(r, c))
        if row.get("peso_kg"):
            records.append(row)
    return records


def completeness(rec):
    return sum(1 for k, v in rec.items() if not k.startswith("_") and v not in ("", None))


def consolidate():
    NON_DATA = {"consolidate_fitdays", "extract_fitdays_structure", "integrate_with_main_db"}
    files = [f for f in sorted(FITDAYS_FOLDER.glob("*"))
             if f.suffix in (".csv", ".xls", ".xlsx") and f.stem not in NON_DATA]

    print("\n" + "=" * 60)
    print("CONSOLIDADOR FITDAYS")
    print("=" * 60)
    print("Archivos: {}\n".format(len(files)))

    all_records = {}
    for f in files:
        recs = read_xls_file(f)
        print("  {:25s} -> {} registros".format(f.name, len(recs)))
        for rec in recs:
            key = "{} {}".format(rec["fecha"], rec["hora"])
            if key not in all_records or completeness(rec) > completeness(all_records[key]):
                all_records[key] = rec

    sorted_records = sorted(all_records.values(), key=lambda r: r["_dt"])

    seen_dates = set()
    for rec in sorted_records:
        rec["primera_del_dia"] = "1" if rec["fecha"] not in seen_dates else "0"
        seen_dates.add(rec["fecha"])

    with open(str(OUTPUT_CSV), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted_records)

    print("\n" + "=" * 60)
    print("Total registros unicos : {}".format(len(sorted_records)))
    if sorted_records:
        print("Rango de fechas        : {} -> {}".format(
            sorted_records[0]["fecha"], sorted_records[-1]["fecha"]))
    print("Output                 : {}".format(OUTPUT_CSV))
    print("=" * 60)
    print("\nPara nuevas mediciones:")
    print("  1. Copia el .csv de Fitdays a esta carpeta")
    print("  2. python consolidate_fitdays.py\n")


if __name__ == "__main__":
    consolidate()
