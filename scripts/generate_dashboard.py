#!/usr/bin/env python3
"""
generate_dashboard.py — Lee SQLite e inyecta datos en el dashboard HTML
Uso: python generate_dashboard.py
"""
import sqlite3, json, sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent))

try:
    from config import DB_PATH
    try:
        from config import HR_ZONES
    except ImportError:
        HR_ZONES = [
            {"name":"Z1","label":"Recuperación","min":0,"max":110,"color":"#9ca3af"},
            {"name":"Z2","label":"Aeróbico","min":110,"max":127,"color":"#3b82f6"},
            {"name":"Z3","label":"Tempo","min":127,"max":150,"color":"#22c55e"},
            {"name":"Z4","label":"Umbral","min":150,"max":162,"color":"#f97316"},
            {"name":"Z5","label":"VO2max","min":162,"max":999,"color":"#ef4444"},
        ]
except ImportError:
    DB_PATH = "data/triathlon.db"
    HR_ZONES = []

DASHBOARD = Path(__file__).parent.parent / "dashboard" / "index.html"

# ── EVENTOS DE CARRERA ─────────────────────────────────────────
# Edita esta lista para agregar/quitar carreras
EVENTS = [
    {"name": "21k La Paz–Ciudad Colón", "date": "2026-06-07", "distance": "21k"},
    {"name": "70.3 Ticoman",            "date": "2026-10-04", "distance": "70.3"},
    {"name": "Maratón Nov 23",          "date": "2026-11-23", "distance": "42k"},
]

def get_conn():
    if not Path(DB_PATH).exists():
        print(f"ERROR: No existe {DB_PATH}")
        return None
    return sqlite3.connect(DB_PATH)

def wellness(conn, days=90):
    d0 = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute("""
        SELECT date, ctl, atl, tsb, hrv, rhr,
               sleep_secs, stress_avg, ramprate, eftp
        FROM wellness WHERE date >= ? ORDER BY date
    """, (d0,)).fetchall()
    keys = ["date","ctl","atl","tsb","hrv","rhr","sleep_secs",
            "stress_avg","ramprate","eftp"]
    return [dict(zip(keys, r)) for r in rows]

def activities(conn, days=180):
    """Exporta actividades crudas (incluye zonas FC) para filtrado client-side por presets."""
    d0 = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute("""
        SELECT id,date,name,sport,duration_sec,distance_m,tss,
               avg_power_w,avg_hr,max_hr,avg_cadence,elevation_m,avg_pace_ms,
               hr_zone_times
        FROM activities WHERE date >= ? ORDER BY date DESC
    """, (d0,)).fetchall()
    keys = ["id","date","name","sport","duration_sec","distance_m","tss",
            "avg_power_w","avg_hr","max_hr","avg_cadence","elevation_m","avg_pace_ms",
            "hr_zone_times"]
    out = []
    for r in rows:
        d = dict(zip(keys, r))
        # Parsear zonas de JSON string a lista
        if d["hr_zone_times"]:
            try: d["hr_zone_times"] = json.loads(d["hr_zone_times"])
            except Exception: d["hr_zone_times"] = None
        out.append(d)
    return out

def body_comp(conn):
    rows = conn.execute("""
        SELECT date,weight_kg,body_fat_pct,muscle_mass_kg,
               skeletal_muscle_kg,tbw_pct,visceral_fat,bmr_kcal,body_age
        FROM body_composition ORDER BY date
    """).fetchall()
    keys = ["date","weight_kg","body_fat_pct","muscle_mass_kg",
            "skeletal_muscle_kg","tbw_pct","visceral_fat","bmr_kcal","body_age"]
    return [dict(zip(keys, r)) for r in rows]

def weekly_tss(conn, weeks=16):
    rows = conn.execute("""
        SELECT strftime('%Y-W%W', date) week, SUM(tss) tss,
               COUNT(*) acts, SUM(duration_sec) secs
        FROM activities
        WHERE date >= date('now', ?)
        GROUP BY week ORDER BY week
    """, (f"-{weeks*7} days",)).fetchall()
    return [{"week":r[0], "tss":round(r[1] or 0,1), "activities":r[2],
             "hours":round((r[3] or 0)/3600,1)} for r in rows]

def main():
    conn = get_conn()
    if not conn:
        return

    data = {
        "generated_at":      datetime.now().isoformat(),
        "events":            EVENTS,
        "hr_zones":          HR_ZONES,
        "wellness_recent":   wellness(conn),
        "activities_recent": activities(conn),
        "body_comp":         body_comp(conn),
        "weekly_tss":        weekly_tss(conn),
    }
    conn.close()

    html   = DASHBOARD.read_text(encoding="utf-8")
    M0, M1 = "// <<<DATA_START>>>", "// <<<DATA_END>>>"
    si = html.find(M0)
    ei = html.find(M1)
    if si == -1 or ei == -1:
        print("ERROR: marcadores DATA no encontrados en HTML"); return
    ei += len(M1)
    injection = (f"{M0}\nwindow.__DASHBOARD_DATA__ = {json.dumps(data, ensure_ascii=False, default=str)};\n"
                 f"const DATA = window.__DASHBOARD_DATA__;\n{M1}")
    DASHBOARD.write_text(html[:si] + injection + html[ei:], encoding="utf-8")

    w  = data["wellness_recent"]
    bc = data["body_comp"]
    lw = w[-1] if w else {}
    print(f"\n{'='*52}")
    print(f"  Dashboard generado  →  dashboard/index.html")
    print(f"{'='*52}")
    print(f"  Wellness:     {len(w)} días")
    print(f"  Actividades:  {len(data['activities_recent'])}")
    print(f"  Body comp:    {len(bc)} mediciones")
    print(f"  CTL:  {lw.get('ctl','—')}  |  ATL: {lw.get('atl','—')}  |  TSB: {lw.get('tsb','—')}")
    if not w:
        print("\n  ⚠  Sin datos de Intervals. Intenta:")
        print("     python scripts\\sync_intervals.py --full --debug")
    print(f"{'='*52}\n")

if __name__ == "__main__":
    main()
