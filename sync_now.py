#!/usr/bin/env python3
"""
sync_now.py - Sincroniza Intervals.icu -> triathlon_final.db
Calcula hr_zone_times_by_sport con umbrales por deporte (sport_config).

Uso: python sync_now.py [--days N] [--full] [--no-streams]
"""

import sqlite3, requests, json, sys, argparse
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ── Config ────────────────────────────────────────────────
import os
ROOT    = Path(__file__).parent
DB_PATH = Path(os.environ.get("VF_DB_PATH", str(ROOT / "data" / "triathlon.db")))

# Credenciales: variables de entorno primero (GitHub Actions), luego config.py (local)
API_KEY    = os.environ.get("INTERVALS_API_KEY")
ATHLETE_ID = os.environ.get("INTERVALS_ATHLETE_ID")

if not API_KEY or not ATHLETE_ID:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import config as cfg
        API_KEY    = API_KEY    or cfg.API_KEY
        ATHLETE_ID = ATHLETE_ID or cfg.ATHLETE_ID
    except ImportError:
        print("ERROR: define INTERVALS_API_KEY e INTERVALS_ATHLETE_ID como variables de entorno,")
        print("       o crea scripts/config.py con API_KEY y ATHLETE_ID")
        sys.exit(1)

BASE = "https://intervals.icu/api/v1"
AUTH = ("API_KEY", API_KEY)

SPORT_MAP = {
    "run": "run", "running": "run",
    "ride": "ride", "cycling": "ride", "virtualride": "ride",
    "swim": "swim", "swimming": "swim", "openwaterswim": "swim",
}


# ── DB ────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    # Asegurar columna hr_zone_times_by_sport
    cols = [r[1] for r in conn.execute("PRAGMA table_info(activities)").fetchall()]
    if "hr_zone_times_by_sport" not in cols:
        conn.execute("ALTER TABLE activities ADD COLUMN hr_zone_times_by_sport TEXT")
        conn.commit()
        print("  + columna hr_zone_times_by_sport creada")
    return conn


def load_sport_configs(conn):
    """Retorna {sport_key: {vt1, vt2, rcp, fcmax}} desde sport_config."""
    configs = {}
    try:
        for row in conn.execute("SELECT sport, vt1_bpm, vt2_bpm, rcp_bpm, fcmax_bpm FROM sport_config"):
            key = row["sport"].lower()
            configs[key] = {
                "vt1": row["vt1_bpm"], "vt2": row["vt2_bpm"],
                "rcp": row["rcp_bpm"], "fcmax": row["fcmax_bpm"],
            }
    except Exception:
        pass
    # Defaults si no hay tabla
    defaults = {
        "run":  {"vt1": 122, "vt2": 150, "rcp": 163, "fcmax": 170},
        "ride": {"vt1": 110, "vt2": 127, "rcp": 150, "fcmax": 162},
        "swim": {"vt1": 110, "vt2": 130, "rcp": 145, "fcmax": 155},
    }
    for k, v in defaults.items():
        if k not in configs:
            configs[k] = v
    return configs


# ── API ───────────────────────────────────────────────────
def api_get(endpoint, params=None):
    url = f"{BASE}/{endpoint}"
    try:
        r = requests.get(url, auth=AUTH, params=params, timeout=30)
    except requests.ConnectionError:
        print("  ERROR: sin conexion")
        return None
    if r.status_code != 200:
        print(f"  ERROR {r.status_code}: {r.text[:120]}")
        return None
    try:
        return r.json()
    except Exception:
        return None


def compute_hr_zones(hr_stream, sport_key, configs):
    """Cuenta segundos en cada zona para el deporte dado."""
    c = configs.get(sport_key, configs.get("run"))
    v1, v2, rcp, fm = c["vt1"], c["vt2"], c["rcp"], c["fcmax"]
    limits = [v1, v2, rcp, fm]   # 4 umbrales definen 5 zonas
    zones  = [0] * 5
    for hr in hr_stream:
        if hr is None or hr <= 0:
            continue
        idx = 0
        for lim in limits:
            if hr >= lim:
                idx += 1
            else:
                break
        zones[idx] += 1
    return zones


def fetch_hr_zones_by_sport(activity_id, sport_key, configs):
    """Llama a la API de streams y calcula zonas."""
    data = api_get(f"activity/{activity_id}/streams", params={"types": "heartrate"})
    if not data or not isinstance(data, list):
        return None
    hr_stream = None
    for s in data:
        if s.get("type") == "heartrate":
            hr_stream = s.get("data")
            break
    if not hr_stream:
        return None
    c     = configs.get(sport_key, configs.get("run"))
    zones = compute_hr_zones(hr_stream, sport_key, configs)
    return json.dumps({"sport": sport_key, "zones": zones, "config": c})


# ── Sync actividades ──────────────────────────────────────
def sync_activities(conn, date_from, date_to, fetch_streams, configs):
    print(f"\n  Actividades {date_from} -> {date_to} ...")
    data = api_get(f"athlete/{ATHLETE_ID}/activities",
                   params={"oldest": date_from, "newest": date_to})
    if not data or not isinstance(data, list):
        print("  Sin datos de actividades")
        return 0

    # IDs que ya tienen hr_zone_times_by_sport
    done = {str(r[0]) for r in conn.execute(
        "SELECT id FROM activities WHERE hr_zone_times_by_sport IS NOT NULL")}

    count = streams = 0
    for idx, act in enumerate(data, 1):
        act_id   = str(act.get("id", ""))
        sport_raw = (act.get("type") or act.get("sport_type", "")).lower()
        sport_key = SPORT_MAP.get(sport_raw, "run")

        hrz_json = None
        has_hr   = act.get("average_heartrate") or act.get("max_heartrate")
        if fetch_streams and has_hr and act_id not in done:
            name = (act.get("name") or "")[:35]
            print(f"    [{idx}/{len(data)}] zonas FC: {name}", flush=True)
            hrz_json = fetch_hr_zones_by_sport(act_id, sport_key, configs)
            if hrz_json:
                streams += 1

        tss = act.get("icu_training_load") or act.get("tss")
        row = {
            "id":           act_id,
            "date":         (act.get("start_date_local") or act.get("start_date", ""))[:10],
            "name":         act.get("name", ""),
            "sport":        act.get("type") or act.get("sport_type", ""),
            "duration_sec": act.get("moving_time") or act.get("elapsed_time"),
            "distance_m":   act.get("distance"),
            "tss":          tss,
            "ctl":          act.get("ctl"),
            "atl":          act.get("atl"),
            "tsb":          act.get("tsb"),
            "avg_power_w":  act.get("average_watts"),
            "norm_power_w": act.get("normalized_power"),
            "avg_hr":       act.get("average_heartrate"),
            "max_hr":       act.get("max_heartrate"),
            "avg_cadence":  act.get("average_cadence"),
            "elevation_m":  act.get("total_elevation_gain"),
            "calories":     act.get("calories"),
            "avg_pace_ms":  act.get("average_speed"),
            "eftp":         act.get("eFTP") or act.get("ftp"),
            "hrz":          hrz_json,
        }
        if not row["date"]:
            continue
        conn.execute("""
            INSERT INTO activities
                (id,date,name,sport,duration_sec,distance_m,tss,ctl,atl,tsb,
                 avg_power_w,norm_power_w,avg_hr,max_hr,avg_cadence,
                 elevation_m,calories,avg_pace_ms,eftp,hr_zone_times_by_sport)
            VALUES
                (:id,:date,:name,:sport,:duration_sec,:distance_m,:tss,:ctl,:atl,:tsb,
                 :avg_power_w,:norm_power_w,:avg_hr,:max_hr,:avg_cadence,
                 :elevation_m,:calories,:avg_pace_ms,:eftp,:hrz)
            ON CONFLICT(id) DO UPDATE SET
                date=excluded.date, name=excluded.name, sport=excluded.sport,
                duration_sec=excluded.duration_sec, distance_m=excluded.distance_m,
                tss=excluded.tss, ctl=excluded.ctl, atl=excluded.atl, tsb=excluded.tsb,
                avg_power_w=excluded.avg_power_w, norm_power_w=excluded.norm_power_w,
                avg_hr=excluded.avg_hr, max_hr=excluded.max_hr,
                avg_cadence=excluded.avg_cadence, elevation_m=excluded.elevation_m,
                calories=excluded.calories, avg_pace_ms=excluded.avg_pace_ms,
                eftp=excluded.eftp,
                hr_zone_times_by_sport=COALESCE(
                    excluded.hr_zone_times_by_sport,
                    activities.hr_zone_times_by_sport)
        """, row)
        count += 1

    conn.commit()
    print(f"  OK {count} actividades ({streams} con zonas FC por deporte)")
    return count


# ── Sync wellness ─────────────────────────────────────────
def sync_wellness(conn, date_from, date_to):
    print(f"\n  Wellness {date_from} -> {date_to} ...")
    data = api_get(f"athlete/{ATHLETE_ID}/wellness",
                   params={"oldest": date_from, "newest": date_to})
    if data is None:
        print("  Sin datos de wellness")
        return 0
    if isinstance(data, dict):
        data = data.get("wellness") or data.get("data") or []
    if not isinstance(data, list):
        return 0

    count = 0
    for day in data:
        date_val = (day.get("id") or day.get("date") or "")[:10]
        if not date_val:
            continue
        ctl = day.get("ctl")
        atl = day.get("atl")
        tsb = day.get("tsb")
        if tsb is None and ctl is not None and atl is not None:
            tsb = round(ctl - atl, 1)
        eftp = None
        for si in (day.get("sportInfo") or []):
            if si.get("type") in ("Ride", "VirtualRide") and si.get("eftp"):
                eftp = round(si["eftp"], 1)
                break
        conn.execute("""
            INSERT OR REPLACE INTO wellness
                (date,ctl,atl,tsb,eftp,ramprate,ctl_load,atl_load,
                 sleep_secs,sleep_score,hrv,hrv_baseline,rhr,
                 stress_avg,respiration,spo2,steps)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            date_val, ctl, atl, tsb, eftp,
            day.get("rampRate"), day.get("ctlLoad"), day.get("atlLoad"),
            day.get("sleepSecs"), day.get("sleepScore"),
            day.get("hrv"), day.get("hrvBaseline"),
            day.get("restingHR") or day.get("rhr"),
            day.get("avgStress"), day.get("avgWakingRespiration"),
            day.get("avgSpo2"), day.get("steps"),
        ))
        count += 1

    conn.commit()
    print(f"  OK {count} dias de wellness")
    return count


# ── Main ──────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days",       type=int, default=14,
                        help="Dias hacia atras (default 14)")
    parser.add_argument("--full",       action="store_true",
                        help="Descarga desde 2025-01-01")
    parser.add_argument("--no-streams", action="store_true",
                        help="No descarga streams de FC (mas rapido)")
    args = parser.parse_args()

    date_from = "2025-01-01" if args.full else \
                (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
    date_to   = datetime.now().strftime("%Y-%m-%d")

    print(f"\n{'='*55}")
    print(f"  VITAL FORM — Sync Intervals.icu")
    print(f"  DB:      {DB_PATH}")
    print(f"  Periodo: {date_from}  a  {date_to}")
    print(f"{'='*55}")

    conn    = get_conn()
    configs = load_sport_configs(conn)
    print(f"\n  Umbrales cargados:")
    for k, v in configs.items():
        print(f"    {k:12s} vt1={v['vt1']} vt2={v['vt2']} rcp={v['rcp']} fcmax={v['fcmax']}")

    acts = sync_activities(conn, date_from, date_to, not args.no_streams, configs)
    well = sync_wellness(conn, date_from, date_to)

    try:
        conn.execute(
            "INSERT INTO sync_log (source,records_added,date_from,date_to) VALUES (?,?,?,?)",
            ("intervals_sync_now", acts + well, date_from, date_to))
        conn.commit()
    except Exception:
        pass
    conn.close()

    print(f"\n{'='*55}")
    print(f"  Sync completo: {acts} actividades, {well} dias wellness")
    print(f"  Recarga el dashboard para ver los datos actualizados.")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
