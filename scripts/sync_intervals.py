#!/usr/bin/env python3
"""
sync_intervals.py — Descarga actividades y wellness de Intervals.icu
Uso: python sync_intervals.py [--days 30] [--full] [--debug]
"""

import sqlite3, requests, argparse, sys, json
from datetime import datetime, timedelta
from pathlib import Path

# Forzar UTF-8 en consola Windows (evita errores con tildes y emojis)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Añadir carpeta del script al path para importar config
sys.path.insert(0, str(Path(__file__).parent))

try:
    from config import ATHLETE_ID, API_KEY, DB_PATH
    try:
        from config import HR_ZONES
    except ImportError:
        # Fallback si config.py es viejo y no tiene HR_ZONES
        HR_ZONES = [
            {"name":"Z1","label":"Recuperación","min":0,"max":110,"color":"#9ca3af"},
            {"name":"Z2","label":"Aeróbico","min":110,"max":127,"color":"#3b82f6"},
            {"name":"Z3","label":"Tempo","min":127,"max":150,"color":"#22c55e"},
            {"name":"Z4","label":"Umbral","min":150,"max":162,"color":"#f97316"},
            {"name":"Z5","label":"VO2max","min":162,"max":999,"color":"#ef4444"},
        ]
except ImportError:
    print("ERROR: Falta config.py — copia config_template.py como config.py")
    sys.exit(1)

BASE_URL = "https://intervals.icu/api/v1"
AUTH     = ("API_KEY", API_KEY)
DEBUG    = False


def get_db():
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.commit()
    return conn


def api_get(endpoint, params=None):
    url = f"{BASE_URL}/{endpoint}"
    try:
        r = requests.get(url, auth=AUTH, params=params, timeout=30)
    except requests.exceptions.ConnectionError:
        print("  ERROR: No hay conexion a internet o intervals.icu no responde")
        return None
    if DEBUG:
        print(f"  [DEBUG] GET {url} → {r.status_code}")
        print(f"  [DEBUG] Params: {params}")
        print(f"  [DEBUG] Body[:300]: {r.text[:300]}")
    if r.status_code == 401:
        print("  ERROR: API key invalida. Revisa config.py")
        return None
    if r.status_code == 403:
        print("  ERROR 403 — verifica que la API key sea correcta")
        return None
    if r.status_code != 200:
        print(f"  ERROR {r.status_code}: {r.text[:200]}")
        return None
    try:
        return r.json()
    except Exception as e:
        print(f"  ERROR parseando JSON: {e}")
        return None


def fetch_hr_zones_from_stream(activity_id):
    """
    Descarga el stream de FC de una actividad y clasifica cada segundo
    en las 5 zonas de laboratorio. Devuelve [seg_z1, seg_z2, ..., seg_z5].
    """
    data = api_get(f"activity/{activity_id}/streams", params={"types": "heartrate"})
    if not data or not isinstance(data, list):
        return None
    # data = [{"type":"heartrate","data":[99,99,...]}]
    hr_stream = None
    for s in data:
        if s.get("type") == "heartrate":
            hr_stream = s.get("data")
            break
    if not hr_stream:
        return None

    # Clasificar cada segundo (cada punto del stream = 1 segundo)
    zone_secs = [0] * len(HR_ZONES)
    for hr in hr_stream:
        if hr is None or hr <= 0:
            continue
        for i, z in enumerate(HR_ZONES):
            if z["min"] <= hr < z["max"]:
                zone_secs[i] += 1
                break
    return zone_secs


def sync_activities(conn, date_from, date_to, fetch_streams=True):
    print(f"  Descargando actividades {date_from} → {date_to}...")
    data = api_get(f"athlete/{ATHLETE_ID}/activities",
                   params={"oldest": date_from, "newest": date_to})
    if data is None:
        return 0
    if not isinstance(data, list):
        print(f"  WARN: respuesta inesperada (tipo {type(data).__name__})")
        if DEBUG: print(f"  [DEBUG] data = {str(data)[:300]}")
        return 0

    # Qué actividades ya tienen zonas calculadas (para no re-descargar streams)
    existing = set()
    for r in conn.execute("SELECT id FROM activities WHERE hr_zone_times IS NOT NULL"):
        existing.add(r[0])

    count = 0
    streams_fetched = 0
    total = len(data)
    for idx, act in enumerate(data):
        act_id = str(act.get("id", ""))
        # Carga: icu_training_load es el valor correcto (tss viene vacío en run/swim)
        load = act.get("icu_training_load")
        if load is None:
            load = act.get("tss")  # fallback

        # Zonas de FC: descargar stream y clasificar con límites de lab.
        # Solo si tiene FC, no la tenemos ya, y fetch_streams está activo.
        hrz_json = None
        has_hr = act.get("average_heartrate") or act.get("max_heartrate")
        if fetch_streams and has_hr and act_id not in existing:
            print(f"    [{idx+1}/{total}] FC zonas: {act.get('name','')[:30]}...", flush=True)
            zones = fetch_hr_zones_from_stream(act_id)
            if zones:
                hrz_json = json.dumps(zones)
                streams_fetched += 1

        row = {
            "id":           str(act.get("id", "")),
            "date":         (act.get("start_date_local") or act.get("start_date", ""))[:10],
            "name":         act.get("name", ""),
            "sport":        act.get("type") or act.get("sport_type", ""),
            "duration_sec": act.get("moving_time") or act.get("elapsed_time") or act.get("timer_time"),
            "distance_m":   act.get("distance"),
            "tss":          load,
            "ctl":          act.get("ctl"),
            "atl":          act.get("atl"),
            "tsb":          act.get("tsb"),
            "avg_power_w":  act.get("average_watts"),
            "norm_power_w": act.get("normalized_power") or act.get("weighted_average_watts"),
            "avg_hr":       act.get("average_heartrate"),
            "max_hr":       act.get("max_heartrate"),
            "avg_cadence":  act.get("average_cadence"),
            "elevation_m":  act.get("total_elevation_gain"),
            "calories":     act.get("calories") or act.get("kilojoules"),
            "avg_pace_ms":  act.get("average_speed"),
            "eftp":         act.get("eFTP") or act.get("ftp"),
            "hr_zone_times": hrz_json,
        }
        if not row["date"]:
            continue
        # COALESCE: si no descargamos zonas esta vez, preservar las que ya estaban
        conn.execute("""
            INSERT INTO activities
            (id,date,name,sport,duration_sec,distance_m,tss,ctl,atl,tsb,
             avg_power_w,norm_power_w,avg_hr,max_hr,avg_cadence,
             elevation_m,calories,avg_pace_ms,eftp,hr_zone_times)
            VALUES
            (:id,:date,:name,:sport,:duration_sec,:distance_m,:tss,:ctl,:atl,:tsb,
             :avg_power_w,:norm_power_w,:avg_hr,:max_hr,:avg_cadence,
             :elevation_m,:calories,:avg_pace_ms,:eftp,:hr_zone_times)
            ON CONFLICT(id) DO UPDATE SET
             date=excluded.date, name=excluded.name, sport=excluded.sport,
             duration_sec=excluded.duration_sec, distance_m=excluded.distance_m,
             tss=excluded.tss, ctl=excluded.ctl, atl=excluded.atl, tsb=excluded.tsb,
             avg_power_w=excluded.avg_power_w, norm_power_w=excluded.norm_power_w,
             avg_hr=excluded.avg_hr, max_hr=excluded.max_hr, avg_cadence=excluded.avg_cadence,
             elevation_m=excluded.elevation_m, calories=excluded.calories,
             avg_pace_ms=excluded.avg_pace_ms, eftp=excluded.eftp,
             hr_zone_times=COALESCE(excluded.hr_zone_times, activities.hr_zone_times)
        """, row)
        count += 1

    conn.commit()
    msg = f"  ✓ {count} actividades guardadas"
    if streams_fetched:
        msg += f" ({streams_fetched} con zonas FC nuevas)"
    print(msg)
    return count


def sync_wellness(conn, date_from, date_to):
    print(f"  Descargando wellness {date_from} → {date_to}...")
    data = api_get(f"athlete/{ATHLETE_ID}/wellness",
                   params={"oldest": date_from, "newest": date_to})
    if data is None:
        return 0

    # Intervals puede devolver lista o dict con key "wellness"
    if isinstance(data, dict):
        data = data.get("wellness") or data.get("data") or []
    if not isinstance(data, list):
        print(f"  WARN: respuesta wellness inesperada (tipo {type(data).__name__})")
        return 0

    count = 0
    for day in data:
        # El ID puede ser la fecha directamente
        date_val = day.get("id") or day.get("date") or ""
        if len(date_val) > 10:
            date_val = date_val[:10]
        if not date_val:
            continue

        ctl_v = day.get("ctl")
        atl_v = day.get("atl")
        tsb_v = day.get("tsb")
        # Intervals.icu define TSB del día como CTL(ayer) - ATL(ayer).
        # Si la API no lo manda, lo derivamos de CTL - ATL.
        if tsb_v is None and ctl_v is not None and atl_v is not None:
            tsb_v = round(ctl_v - atl_v, 1)

        # eFTP viene anidado en sportInfo: [{"type":"Ride","eftp":273,...}]
        eftp_v = None
        sport_info = day.get("sportInfo") or []
        for si in sport_info:
            if si.get("type") in ("Ride", "VirtualRide") and si.get("eftp"):
                eftp_v = round(si["eftp"], 1)
                break

        row = {
            "date":              date_val,
            "ctl":               ctl_v,
            "atl":               atl_v,
            "tsb":               tsb_v,
            "eftp":              eftp_v,
            "ramprate":          day.get("rampRate") or day.get("ramp_rate"),
            "ctl_load":          day.get("ctlLoad") or day.get("ctl_load"),
            "atl_load":          day.get("atlLoad") or day.get("atl_load"),
            "sleep_secs":        day.get("sleepSecs") or day.get("sleep_secs"),
            "sleep_score":       day.get("sleepScore") or day.get("sleep_score"),
            "hrv":               day.get("hrv"),
            "hrv_baseline":      day.get("hrvBaseline") or day.get("hrv_baseline"),
            "rhr":               day.get("restingHR") or day.get("resting_hr") or day.get("rhr"),
            "stress_avg":        day.get("avgStress") or day.get("avg_stress"),
            "respiration":       day.get("avgWakingRespiration") or day.get("respiration"),
            "spo2":              day.get("avgSpo2") or day.get("spo2"),
            "steps":             day.get("steps"),
        }
        conn.execute("""
            INSERT OR REPLACE INTO wellness
            (date,ctl,atl,tsb,eftp,ramprate,ctl_load,atl_load,
             sleep_secs,sleep_score,hrv,hrv_baseline,rhr,
             stress_avg,respiration,spo2,steps)
            VALUES
            (:date,:ctl,:atl,:tsb,:eftp,:ramprate,:ctl_load,:atl_load,
             :sleep_secs,:sleep_score,:hrv,:hrv_baseline,:rhr,
             :stress_avg,:respiration,:spo2,:steps)
        """, row)
        count += 1

    conn.commit()
    print(f"  ✓ {count} dias de wellness guardados")
    return count


def main():
    global DEBUG
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--no-streams", action="store_true",
                        help="No descargar streams de FC (sync rápido, sin zonas nuevas)")
    args = parser.parse_args()
    DEBUG = args.debug

    date_from = "2025-01-01" if args.full else \
                (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
    date_to   = datetime.now().strftime("%Y-%m-%d")

    print(f"\n{'='*50}")
    print(f"  SYNC Intervals.icu → {DB_PATH}")
    print(f"  Periodo: {date_from} → {date_to}")
    if DEBUG: print("  [DEBUG MODE ACTIVO]")
    if not args.no_streams:
        print("  Zonas FC: descargando streams (puede tardar)")
    print(f"{'='*50}\n")

    conn = get_db()
    acts = sync_activities(conn, date_from, date_to, fetch_streams=not args.no_streams)
    well = sync_wellness(conn, date_from, date_to)

    conn.execute("INSERT INTO sync_log (source,records_added,date_from,date_to) VALUES (?,?,?,?)",
                 ("intervals", acts + well, date_from, date_to))
    conn.commit()
    conn.close()

    if acts + well == 0:
        print("\n⚠  No se descargaron datos. Corre con --debug para ver la respuesta de la API:")
        print(f"   python scripts/sync_intervals.py --debug --days 30\n")
    else:
        print(f"\n✓ Sync completo — {acts} actividades, {well} dias de wellness\n")

if __name__ == "__main__":
    main()
