import streamlit as st
import pandas as pd
import sqlite3
import json
from datetime import datetime, timedelta
import plotly.graph_objects as go
from pathlib import Path

# ════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════

st.set_page_config(
    page_title="VITAL FORM",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Paleta de colores armonizada con el logo
COLORS = {
    "blue":        "#0ea5e9",
    "blue_dark":   "#0c4a6e",
    "blue_light":  "#e0f2fe",
    "teal":        "#0d9488",
    "green":       "#22c55e",
    "green_light": "#dcfce7",
    "orange":      "#f97316",
    "red":         "#ef4444",
    "pink":        "#ec4899",
    "gray":        "#6b7280",
    "gray_light":  "#f1f5f9",
}

RACE_DATE = datetime(2026, 10, 4)

DB_PATH = Path("data/triathlon.db")
if not DB_PATH.exists():
    st.error(f"❌ Base de datos no encontrada en {DB_PATH}")
    st.stop()

# ════════════════════════════════════════════════════════
# CSS GLOBAL
# ════════════════════════════════════════════════════════

def inject_css():
    st.markdown("""
    <style>
    /* Header personalizado */
    .vf-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 0;
        margin-bottom: 1.5rem;
        border-bottom: 1px solid rgba(14, 165, 233, 0.2);
    }
    .vf-logo { display: flex; align-items: center; gap: 14px; }
    .vf-icon-box {
        width: 48px; height: 48px;
        border-radius: 12px;
        background: #e0f2fe;
        border: 1.5px solid #0ea5e9;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
    }
    .vf-brand { display: flex; flex-direction: column; gap: 2px; }
    .vf-name {
        font-size: 22px; font-weight: 600;
        line-height: 1; letter-spacing: -0.5px;
    }
    .vf-vital { color: var(--color-text-primary); }
    .vf-form  { color: #0ea5e9; }
    .vf-tagline {
        font-size: 10px; font-weight: 500;
        letter-spacing: 3px; color: #22c55e;
        text-transform: uppercase;
    }
    .vf-bars { display: flex; gap: 4px; margin-top: 3px; }
    .vf-bar { display: block; height: 2px; width: 20px; border-radius: 1px; }
    .vf-pills { display: flex; align-items: center; gap: 8px; }
    .vf-pill {
        font-size: 11px; font-weight: 500;
        padding: 5px 12px; border-radius: 20px;
        letter-spacing: 0.3px; white-space: nowrap;
    }
    .pill-race {
        background: #e0f2fe; color: #0c4a6e;
        border: 1px solid #0ea5e9;
    }
    .pill-days {
        background: #dcfce7; color: #166534;
        border: 1px solid #22c55e;
    }

    /* Métricas con colores semánticos */
    [data-testid="stMetricDelta"] svg { display: none; }

    /* Secciones */
    .vf-section {
        font-size: 10px; font-weight: 600;
        letter-spacing: 2.5px; text-transform: uppercase;
        color: #6b7280; margin: 0 0 0.75rem;
    }

    /* Ocultar menú hamburguesa */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# HEADER CON LOGO
# ════════════════════════════════════════════════════════

def render_header():
    days_left = (RACE_DATE - datetime.now()).days

    st.markdown(f"""
    <div class="vf-header">
        <div class="vf-logo">
            <div class="vf-icon-box">
                <svg width="30" height="30" viewBox="0 0 30 30" fill="none">
                    <polyline points="4,23 15,7 26,23"
                        stroke="#0ea5e9" stroke-width="2.5"
                        stroke-linecap="round" stroke-linejoin="round"/>
                    <circle cx="15" cy="7" r="3.5" fill="#22c55e"/>
                    <rect x="4" y="25" width="22" height="2.5" rx="1.25" fill="#e0f2fe"/>
                    <rect x="4" y="25" width="14" height="2.5" rx="1.25" fill="#0ea5e9"/>
                </svg>
            </div>
            <div class="vf-brand">
                <div class="vf-name">
                    <span class="vf-vital">VITAL&nbsp;</span><span class="vf-form">FORM</span>
                </div>
                <div class="vf-tagline">Performance Tracker</div>
                <div class="vf-bars">
                    <span class="vf-bar" style="background:#22c55e"></span>
                    <span class="vf-bar" style="background:#0ea5e9"></span>
                    <span class="vf-bar" style="background:#0d9488"></span>
                </div>
            </div>
        </div>
        <div class="vf-pills">
            <span class="vf-pill pill-race">🏁 70.3 Ticoman · 4 oct 2026</span>
            <span class="vf-pill pill-days">⏱ {days_left} días</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# FUNCIONES DE DATOS
# ════════════════════════════════════════════════════════

@st.cache_resource
def get_db_connection(db_path: str = str(DB_PATH)):
    return sqlite3.connect(db_path, check_same_thread=False)

def load_wellness_data_latest(limit=180):
    conn = get_db_connection(str(DB_PATH))
    query = """
        SELECT date, ctl, atl, tsb, eftp, hrv, rhr, sleep_secs
        FROM wellness
        WHERE date IS NOT NULL
        ORDER BY date DESC LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=(limit,))
    if df.empty:
        return pd.DataFrame()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    df['sleep_hrs'] = df['sleep_secs'] / 3600
    return df

def load_bodycomp_data_latest(limit=180):
    conn = get_db_connection(str(DB_PATH))
    query = """
        SELECT date, weight_kg, body_fat_pct, muscle_mass_kg,
               skeletal_muscle_kg, tbw_pct, visceral_fat
        FROM body_composition
        WHERE date IS NOT NULL
        ORDER BY date DESC LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=(limit,))
    if df.empty:
        return pd.DataFrame()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    return df

def load_wellness_data_filtered(start_date, end_date):
    conn = get_db_connection(str(DB_PATH))
    query = """
        SELECT date, ctl, atl, tsb, eftp, hrv, rhr, sleep_secs
        FROM wellness
        WHERE date IS NOT NULL AND date >= ? AND date <= ?
        ORDER BY date
    """
    df = pd.read_sql_query(query, conn, params=(start_date.isoformat(), end_date.isoformat()))
    if df.empty:
        return pd.DataFrame()
    df['date'] = pd.to_datetime(df['date'])
    df['sleep_hrs'] = df['sleep_secs'] / 3600
    return df

def load_bodycomp_data_filtered(start_date, end_date):
    conn = get_db_connection(str(DB_PATH))
    query = """
        SELECT date, weight_kg, body_fat_pct, muscle_mass_kg,
               skeletal_muscle_kg, tbw_pct, visceral_fat
        FROM body_composition
        WHERE date IS NOT NULL AND date >= ? AND date <= ?
        ORDER BY date
    """
    df = pd.read_sql_query(query, conn, params=(start_date.isoformat(), end_date.isoformat()))
    if df.empty:
        return pd.DataFrame()
    df['date'] = pd.to_datetime(df['date'])
    return df

def load_activities_data_filtered(start_date, end_date):
    conn = get_db_connection(str(DB_PATH))
    query = """
        SELECT date, name, sport, duration_sec, tss, distance_m
        FROM activities
        WHERE date IS NOT NULL AND date >= ? AND date <= ?
        ORDER BY date
    """
    df = pd.read_sql_query(query, conn, params=(start_date.isoformat(), end_date.isoformat()))
    if df.empty:
        return pd.DataFrame()
    df['date'] = pd.to_datetime(df['date'])
    return df

def _load_sport_config():
    """Lee umbrales por deporte desde sport_config. Usa defaults si no existe."""
    defaults = {
        "run":  {"vt1": 122, "vt2": 150, "rcp": 163, "fcmax": 170},
        "ride": {"vt1": 110, "vt2": 127, "rcp": 150, "fcmax": 162},
    }
    try:
        conn = get_db_connection(str(DB_PATH))
        rows = conn.execute(
            "SELECT sport, vt1_bpm, vt2_bpm, rcp_bpm, fcmax_bpm FROM sport_config"
        ).fetchall()
        for r in rows:
            defaults[r[0].lower()] = {
                "vt1": r[1], "vt2": r[2], "rcp": r[3], "fcmax": r[4]
            }
    except Exception:
        pass
    return defaults


RUN_SPORTS  = {'run', 'running', 'trailrun', 'treadmill'}
BIKE_SPORTS = {'ride', 'virtualride', 'cycling', 'mountainbikeride', 'ebikeride', 'handcycle'}

# Nombre → (emoji, clave sport_config)
SPORT_DEFS = {
    'Run':   ('🏃', 'run'),
    'Bike':  ('🚴', 'ride'),
    'Otros': ('⚡', 'run'),   # usa umbrales run como proxy
}


@st.cache_data(ttl=300)
def load_hr_zones_by_sport(start_iso: str, end_iso: str):
    """
    Lee hr_zone_times_by_sport para el período y agrupa en Run / Bike / Otros.
    Devuelve dict: { 'Run': [z1..z5_secs], 'Bike': [...], 'Otros': [...] }
    """
    # Verificar que la columna existe
    try:
        conn = get_db_connection(str(DB_PATH))
        cols = [r[1] for r in conn.execute("PRAGMA table_info(activities)").fetchall()]
        if "hr_zone_times_by_sport" not in cols:
            return {}
    except Exception:
        return {}

    try:
        df = pd.read_sql_query(
            """SELECT sport, hr_zone_times_by_sport
               FROM activities
               WHERE date >= ? AND date <= ?
                 AND hr_zone_times_by_sport IS NOT NULL""",
            conn,
            params=(start_iso, end_iso),
        )
    except Exception:
        return {}

    if df.empty:
        return {}

    zones_by_sport: dict[str, list[float]] = {}

    for _, row in df.iterrows():
        try:
            data = json.loads(row["hr_zone_times_by_sport"])
            zones = data.get("zones", [])
            if len(zones) < 5:
                continue
        except Exception:
            continue

        sport_raw = (row["sport"] or "").lower().strip()
        if sport_raw in RUN_SPORTS:
            bucket = "Run"
        elif sport_raw in BIKE_SPORTS:
            bucket = "Bike"
        else:
            bucket = "Otros"

        if bucket not in zones_by_sport:
            zones_by_sport[bucket] = [0.0] * 5
        for i in range(5):
            zones_by_sport[bucket][i] += zones[i]

    return zones_by_sport


def get_date_range(period):
    today = datetime.now().date()
    if period == "this_week":
        return today - timedelta(days=today.weekday()), today
    elif period == "last_week":
        monday = today - timedelta(days=today.weekday() + 7)
        return monday, monday + timedelta(days=6)
    else:
        return today - timedelta(days=period), today

# ════════════════════════════════════════════════════════
# TSB ZONES
# ════════════════════════════════════════════════════════

def get_tsb_zone(tsb_value):
    if tsb_value >= 10:
        return {'zone': 'Pico de forma',  'range': '+10 a +20', 'action': 'Carrera o sesión de calidad máxima',          'color': '🟢'}
    elif tsb_value >= 3:
        return {'zone': 'Fresco',         'range': '+3 a +10',  'action': 'Entrenamiento normal con calidad',             'color': '🟢'}
    elif tsb_value >= -5:
        return {'zone': 'Cargado',        'range': '0 a -5',    'action': 'Entrenar pero monitorear sensaciones',         'color': '🟡'}
    elif tsb_value >= -15:
        return {'zone': 'Fatiga normal',  'range': '-5 a -15',  'action': 'Reducir intensidad, mantener volumen moderado','color': '🟠'}
    elif tsb_value >= -25:
        return {'zone': 'Fatiga alta',    'range': '-15 a -25', 'action': 'Solo Z1-Z2, sin sesiones de calidad',          'color': '🟠'}
    elif tsb_value >= -35:
        return {'zone': 'Zona de riesgo', 'range': '-25 a -35', 'action': 'Descanso activo únicamente',                   'color': '🔴'}
    else:
        return {'zone': 'Peligro real',   'range': '< -35',     'action': 'Descanso completo obligatorio',                'color': '🔴'}

# ════════════════════════════════════════════════════════
# CÁLCULOS
# ════════════════════════════════════════════════════════

def calculate_ramp_rate(wellness_df):
    if len(wellness_df) < 2:
        return 0
    latest = wellness_df.iloc[-1]
    seven_ago = wellness_df[wellness_df['date'] <= latest['date'] - timedelta(days=7)]
    if seven_ago.empty:
        return 0
    return latest['ctl'] - seven_ago.iloc[-1]['ctl']

def calculate_hrv_rhr_ratio(wellness_last):
    if wellness_last.empty:
        return 0
    hrv = wellness_last['hrv'].values[0]
    rhr = wellness_last['rhr'].values[0]
    return (hrv / rhr * 100) if rhr else 0

def calculate_period_summary(activities_df):
    if activities_df.empty:
        return {'total_time': 0, 'sessions': 0, 'total_tss': 0, 'tss_per_day': 0, 'sport_breakdown': {}}

    sport_mapping = {
        'ride': 'Bike', 'virtualride': 'Bike', 'cycling': 'Bike', 'bike': 'Bike',
        'run': 'Run', 'running': 'Run',
        'swim': 'Swim', 'swimming': 'Swim',
        'hiit': 'Fuerza', 'strength': 'Fuerza', 'strengthtraining': 'Fuerza',
        'workout': 'Fuerza', 'highintensityintervaltraining': 'Fuerza',
    }
    df = activities_df.copy()
    df['sport_consolidated'] = df['sport'].str.lower().map(lambda x: sport_mapping.get(x, 'Otros'))
    total_time = df['duration_sec'].sum() / 3600
    sessions   = len(df)
    total_tss  = df['tss'].sum()
    days       = (df['date'].max() - df['date'].min()).days + 1
    breakdown  = df.groupby('sport_consolidated')['duration_sec'].sum()
    total_t    = breakdown.sum()
    sport_pct  = {s: (t / total_t * 100) for s, t in breakdown.items()}
    return {'total_time': total_time, 'sessions': sessions, 'total_tss': total_tss,
            'tss_per_day': total_tss / max(days, 1), 'sport_breakdown': sport_pct}

# ════════════════════════════════════════════════════════
# ALERTAS
# ════════════════════════════════════════════════════════

def show_alerts(wellness_last, bodycomp_last, wellness_df):
    alerts = []

    if not wellness_last.empty:
        ctl = wellness_last['ctl'].values[0]
        if ctl < 85:
            alerts.append(f"🟡 **CTL en desarrollo:** {ctl:.0f} → Faltan {85-ctl:.0f} puntos para rango óptimo")
        else:
            alerts.append(f"✅ **CTL en rango:** {ctl:.0f} puntos")

    if not wellness_last.empty and len(wellness_df) > 0:
        sleep_avg = wellness_df['sleep_hrs'].tail(7).mean()
        if sleep_avg < 7:
            alerts.append(f"🟡 **Sueño insuficiente:** {sleep_avg:.1f}h promedio < 7h → Prioriza descanso")
        else:
            alerts.append(f"✅ **Sueño adecuado:** {sleep_avg:.1f}h promedio")

    if not wellness_last.empty and len(wellness_df) > 0:
        hrv_avg = wellness_df['hrv'].tail(7).mean()
        if hrv_avg > 50:
            alerts.append(f"ℹ️ **Recuperación excelente:** HRV promedio {hrv_avg:.0f} ms → Continúa con plan")
        else:
            alerts.append(f"🟡 **HRV bajo:** {hrv_avg:.0f} ms → Monitorear recuperación")

    if not wellness_last.empty:
        tsb = wellness_last['tsb'].values[0]
        z = get_tsb_zone(tsb)
        alerts.append(f"{z['color']} **TSB:** {z['zone']} — {z['action']}")

    if alerts:
        st.warning("⚠️ ESTADO DEL ATLETA", icon="⚠️")
        for a in alerts:
            st.markdown(f"• {a}")

    if not bodycomp_last.empty:
        tbw = bodycomp_last['tbw_pct'].values[0]
        if tbw < 64.5:
            st.error(f"🔴 **TBW crítico:** {tbw:.1f}% (target ≥64.5%) → Aumentar ingesta de agua")

    if not wellness_last.empty:
        tsb = wellness_last['tsb'].values[0]
        if tsb < -25:
            z = get_tsb_zone(tsb)
            st.error(f"🔴 **CRÍTICO:** TSB {tsb:.1f} ({z['zone']}) → {z['action']}")

# ════════════════════════════════════════════════════════
# GRÁFICOS — paleta armonizada
# ════════════════════════════════════════════════════════

PLOT_LAYOUT = dict(
    hovermode='x unified',
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=0, r=0, t=0, b=0),
    height=300,
    font=dict(size=12),
    xaxis=dict(showgrid=True, gridwidth=0.5, gridcolor='rgba(14,165,233,0.08)'),
    yaxis=dict(showgrid=True, gridwidth=0.5, gridcolor='rgba(14,165,233,0.08)'),
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
)

def plot_carga(df):
    if df.empty:
        st.info("Sin datos disponibles")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['ctl'], name='CTL (Fitness)',
        mode='lines', line=dict(color=COLORS['blue'], width=2.5),
        hovertemplate='<b>%{x|%d %b}</b><br>CTL: %{y:.1f}<extra></extra>'))
    fig.add_trace(go.Scatter(x=df['date'], y=df['atl'], name='ATL (Fatiga)',
        mode='lines', line=dict(color=COLORS['orange'], width=2),
        hovertemplate='<b>%{x|%d %b}</b><br>ATL: %{y:.1f}<extra></extra>'))
    fig.add_trace(go.Scatter(x=df['date'], y=df['tsb'], name='TSB (Forma)',
        mode='lines', line=dict(color=COLORS['green'], width=2, dash='dash'),
        hovertemplate='<b>%{x|%d %b}</b><br>TSB: %{y:.1f}<extra></extra>'))
    fig.add_hrect(y0=85, y1=90, fillcolor=COLORS['blue'], opacity=0.06, layer='below',
        annotation_text="CTL target", annotation_font_size=10)
    fig.update_layout(**PLOT_LAYOUT)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

def plot_hrv_rhr(df):
    if df.empty:
        st.info("Sin datos disponibles")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['hrv'], name='HRV (ms)',
        mode='lines', line=dict(color=COLORS['blue'], width=2.5), yaxis='y1',
        hovertemplate='<b>%{x|%d %b}</b><br>HRV: %{y:.0f} ms<extra></extra>'))
    fig.add_trace(go.Scatter(x=df['date'], y=df['rhr'], name='FC Reposo',
        mode='lines', line=dict(color=COLORS['pink'], width=2), yaxis='y2',
        hovertemplate='<b>%{x|%d %b}</b><br>FC: %{y:.0f} bpm<extra></extra>'))
    layout = {**PLOT_LAYOUT,
        'yaxis': dict(title='HRV (ms)', showgrid=True, gridwidth=0.5, gridcolor='rgba(14,165,233,0.08)'),
        'yaxis2': dict(title='FC (bpm)', overlaying='y', side='right', showgrid=False)}
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

def plot_composicion(df):
    if df.empty:
        st.info("Sin datos disponibles")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['weight_kg'], name='Peso (kg)',
        mode='lines+markers', line=dict(color=COLORS['blue'], width=2), yaxis='y1',
        marker=dict(size=5),
        hovertemplate='<b>%{x|%d %b}</b><br>Peso: %{y:.1f} kg<extra></extra>'))
    fig.add_trace(go.Scatter(x=df['date'], y=df['body_fat_pct'], name='Grasa (%)',
        mode='lines+markers', line=dict(color=COLORS['orange'], width=2), yaxis='y2',
        marker=dict(size=5),
        hovertemplate='<b>%{x|%d %b}</b><br>Grasa: %{y:.1f}%<extra></extra>'))
    fig.add_trace(go.Scatter(x=df['date'], y=df['tbw_pct'], name='TBW (%)',
        mode='lines+markers', line=dict(color=COLORS['teal'], width=2), yaxis='y3',
        marker=dict(size=5),
        hovertemplate='<b>%{x|%d %b}</b><br>TBW: %{y:.1f}%<extra></extra>'))
    layout = {**PLOT_LAYOUT, 'height': 320,
        'yaxis':  dict(title='Peso (kg)', showgrid=True, gridwidth=0.5, gridcolor='rgba(14,165,233,0.08)'),
        'yaxis2': dict(title='Grasa (%)', overlaying='y', side='right', showgrid=False),
        'yaxis3': dict(title='TBW (%)', overlaying='y', side='right', anchor='free', position=1.0, showgrid=False)}
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════

def main():
    inject_css()
    render_header()

    wellness_current = load_wellness_data_latest(180)
    bodycomp_current = load_bodycomp_data_latest(180)

    if wellness_current.empty or bodycomp_current.empty:
        st.warning("⚠️ No hay datos disponibles. Verifica la base de datos.")
        return

    wellness_last = wellness_current.tail(1)
    bodycomp_last = bodycomp_current.tail(1)

    # ── ESTADO DEL ATLETA ──────────────────────────────
    st.subheader("⚠️ Estado del Atleta")
    show_alerts(wellness_last, bodycomp_current, wellness_current)
    st.divider()

    # ── CARGA & RECUPERACIÓN ───────────────────────────
    st.subheader("📊 Carga & Recuperación")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Evolución de Carga**")
        if not wellness_last.empty:
            ctl_now   = wellness_last['ctl'].values[0]
            ctl_7d    = wellness_current.iloc[0]['ctl']
            ctl_delta = ctl_now - ctl_7d
            st.metric("CTL Hoy", f"{ctl_now:.0f}",
                      f"{'↑' if ctl_delta>0 else '↓'} {ctl_delta:+.1f}")

        ramp = calculate_ramp_rate(wellness_current)
        st.metric("Ramp Rate", f"{ramp:.1f} pts/sem",
                  "✓ OK" if ramp <= 15 else "⚠️ Alto")

        if not wellness_last.empty:
            atl_now   = wellness_last['atl'].values[0]
            atl_7d    = wellness_current.iloc[0]['atl']
            atl_delta = atl_now - atl_7d
            st.metric("ATL (Fatiga)", f"{atl_now:.0f}",
                      f"{'↑' if atl_delta>0 else '↓'} {atl_delta:+.1f}")

            tsb_now   = wellness_last['tsb'].values[0]
            tsb_7d    = wellness_current.iloc[0]['tsb']
            tsb_delta = tsb_now - tsb_7d
            st.metric("TSB (Forma)", f"{tsb_now:.0f}",
                      f"{'↑' if tsb_delta>0 else '↓'} {tsb_delta:+.1f}")

    with col2:
        st.markdown("**Indicadores de Recuperación**")
        if not wellness_last.empty:
            hrv     = wellness_last['hrv'].values[0]
            hrv_avg = wellness_current['hrv'].tail(7).mean()
            st.metric("HRV (7d avg)", f"{hrv_avg:.0f} ms",
                      f"{'↑' if hrv>hrv_avg else '↓'} Hoy: {hrv:.0f}")

        ratio = calculate_hrv_rhr_ratio(wellness_last)
        st.metric("HRV/RHR Ratio", f"{ratio:.1f}",
                  "✓ Excelente" if ratio > 100 else ("✓ Normal" if ratio > 50 else "⚠️ Baja"))

        if not wellness_last.empty:
            rhr     = wellness_last['rhr'].values[0]
            rhr_avg = wellness_current['rhr'].tail(7).mean()
            st.metric("FC Reposo", f"{rhr:.0f} bpm",
                      f"{'↑' if rhr>rhr_avg else '↓'} Avg: {rhr_avg:.0f}")

            sleep_avg = wellness_current['sleep_hrs'].tail(7).mean()
            st.metric("Sueño (7d avg)", f"{sleep_avg:.1f} h",
                      "✓ OK" if sleep_avg >= 7.5 else ("⚠️ Bajo" if sleep_avg < 7 else "→ Normal"))

    with col3:
        st.markdown("**Composición Corporal**")
        if not bodycomp_last.empty:
            w = bodycomp_last['weight_kg'].values[0]
            st.metric("Peso", f"{w:.1f} kg",
                      f"{'↓' if len(bodycomp_current)>1 and w<bodycomp_current.iloc[-2]['weight_kg'] else '→'} Target: 80–81kg")

            fat = bodycomp_last['body_fat_pct'].values[0]
            st.metric("Grasa", f"{fat:.1f}%",
                      f"{'↓' if len(bodycomp_current)>1 and fat<bodycomp_current.iloc[-2]['body_fat_pct'] else '→'} Target: 12–12.5%")

            tbw = bodycomp_last['tbw_pct'].values[0]
            st.metric("TBW", f"{tbw:.1f}%",
                      "✓ OK" if tbw >= 64.5 else ("⚠️ Bajo" if tbw >= 63.5 else "🔴 Crítico"))

            mm = bodycomp_last['skeletal_muscle_kg'].values[0]
            st.metric("Masa Muscular", f"{mm:.1f} kg",
                      f"{'↑' if len(bodycomp_current)>1 and mm>bodycomp_current.iloc[-2]['skeletal_muscle_kg'] else '→'} Floor: 40kg")

    st.divider()

    # ── PERÍODO ────────────────────────────────────────
    col_p, _, col_btn = st.columns([2, 1, 1])
    with col_p:
        period_options = {
            "Esta semana": "this_week", "Semana pasada": "last_week",
            "Últimos 7 días": 7, "Últimos 30 días": 30,
            "Últimos 60 días": 60, "Últimos 90 días": 90,
        }
        selected = st.selectbox("Período", list(period_options.keys()),
                                index=2, label_visibility="collapsed")
        period_key = period_options[selected]

    with col_btn:
        if st.button("🔄 Actualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    start_date, end_date = get_date_range(period_key)
    wellness_df   = load_wellness_data_filtered(start_date, end_date)
    activities_df = load_activities_data_filtered(start_date, end_date)

    # ── RESUMEN PERÍODO ────────────────────────────────
    st.subheader("📈 Resumen del Período")
    summary = calculate_period_summary(activities_df)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tiempo Total",     f"{summary['total_time']:.1f}h")
    c2.metric("Sesiones",         f"{summary['sessions']}")
    c3.metric("Carga (TSS)",      f"{summary['total_tss']:.0f}")
    c4.metric("TSS/día",          f"{summary['tss_per_day']:.0f}")

    sport_colors = {'Bike': COLORS['blue'], 'Run': COLORS['green'],
                    'Swim': COLORS['teal'], 'Fuerza': COLORS['gray']}

    if summary['sport_breakdown']:
        chips_html = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin:0.5rem 0 1rem;">'
        for sport, pct in summary['sport_breakdown'].items():
            color = sport_colors.get(sport, COLORS['gray'])
            chips_html += (
                f'<span style="display:flex;align-items:center;gap:6px;'
                f'font-size:12px;padding:4px 12px;border-radius:20px;'
                f'border:1px solid rgba(255,255,255,0.15);color:inherit;">'
                f'<span style="width:8px;height:8px;border-radius:50%;background:{color};display:block;flex-shrink:0;"></span>'
                f'{sport} {pct:.0f}%</span>'
            )
        chips_html += '</div>'
        st.markdown(chips_html, unsafe_allow_html=True)

    st.divider()

    # ── ZONAS FC ───────────────────────────────────────
    st.subheader("⏱️ Tiempo en Zonas de FC")

    zone_colors = ['#9ca3af', COLORS['blue'], COLORS['green'], COLORS['orange'], COLORS['red']]
    zone_names  = ['Z1 Recuperación', 'Z2 Aeróbico', 'Z3 Tempo', 'Z4 Umbral', 'Z5 VO2max']

    zones_by_sport = load_hr_zones_by_sport(start_date.isoformat(), end_date.isoformat())
    sport_configs  = _load_sport_config()

    disciplines = [d for d in ['Run', 'Bike', 'Otros'] if d in zones_by_sport]

    if not disciplines:
        st.info("Sin datos de zonas FC para el período seleccionado.")
    else:
        cols = st.columns(len(disciplines))
        for col, discipline in zip(cols, disciplines):
            emoji, cfg_key = SPORT_DEFS[discipline]
            cfg = sport_configs.get(cfg_key, sport_configs.get('run', {}))
            z1 = cfg.get('vt1', 122)
            z2 = cfg.get('vt2', 150)
            z3 = cfg.get('rcp', 163)
            z4 = cfg.get('fcmax', 170)
            zone_ranges = [
                f'<{z1} bpm',
                f'{z1}–{z2} bpm',
                f'{z2}–{z3} bpm',
                f'{z3}–{z4} bpm',
                f'>{z4} bpm',
            ]
            zone_secs   = zones_by_sport[discipline]
            total_secs  = sum(zone_secs)

            with col:
                st.markdown(f"**{emoji} {discipline}**")
                for i, (name, rng, secs, color) in enumerate(
                    zip(zone_names, zone_ranges, zone_secs, zone_colors)
                ):
                    pct   = (secs / total_secs * 100) if total_secs else 0
                    hours = int(secs) // 3600
                    mins  = (int(secs) % 3600) // 60
                    gray  = COLORS['gray']
                    time_str = f"{hours}h {mins:02d}m" if hours else f"{mins}m"
                    c1, c2, c3 = st.columns([1.5, 2.5, 0.9])
                    with c1:
                        st.markdown(
                            f'<span style="font-size:11px;color:{gray};">'
                            f'<b>{name}</b><br>{rng}</span>',
                            unsafe_allow_html=True
                        )
                    with c2:
                        st.markdown(
                            f'<div style="background:rgba(255,255,255,0.08);'
                            f'border-radius:4px;height:18px;overflow:hidden;margin-top:6px;">'
                            f'<div style="background:{color};height:100%;'
                            f'width:{pct:.1f}%;border-radius:4px;"></div></div>',
                            unsafe_allow_html=True
                        )
                    with c3:
                        st.markdown(
                            f'<span style="font-size:11px;color:{gray};">'
                            f'<b>{pct:.0f}%</b><br>{time_str}</span>',
                            unsafe_allow_html=True
                        )

    st.divider()

    # ── GRÁFICOS ───────────────────────────────────────
    st.subheader("📊 Evolución")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("**CTL / ATL / TSB**")
        plot_carga(wellness_df)
    with col_g2:
        st.markdown("**HRV & FC Reposo**")
        plot_hrv_rhr(wellness_df)

    st.markdown("**Composición Corporal**")
    plot_composicion(load_bodycomp_data_filtered(start_date, end_date))

if __name__ == "__main__":
    main()
