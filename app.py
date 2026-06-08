import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

# ════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════

st.set_page_config(
    page_title="VITAL FORM",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Rutas
DB_PATH = Path("data/triathlon.db")
if not DB_PATH.exists():
    st.error(f"❌ Base de datos no encontrada en {DB_PATH}")
    st.stop()

# ════════════════════════════════════════════════════════
# FUNCIONES DE DATOS
# ════════════════════════════════════════════════════════

@st.cache_resource
def get_db_connection():
    """Conectar a la BD local"""
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)

def load_wellness_data_latest(limit=180):
    """Cargar últimos N días de wellness para datos actuales"""
    conn = get_db_connection()
    query = """
        SELECT date, ctl, atl, tsb, eftp, hrv, rhr, sleep_secs
        FROM wellness
        WHERE date IS NOT NULL
        ORDER BY date DESC
        LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=(limit,))
    
    if df.empty:
        return pd.DataFrame()
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    df['sleep_hrs'] = df['sleep_secs'] / 3600
    return df

def load_bodycomp_data_latest(limit=180):
    """Cargar últimos N días de composición corporal para datos actuales"""
    conn = get_db_connection()
    query = """
        SELECT date, weight_kg, body_fat_pct, muscle_mass_kg, 
               skeletal_muscle_kg, tbw_pct, visceral_fat
        FROM body_composition
        WHERE date IS NOT NULL
        ORDER BY date DESC
        LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=(limit,))
    
    if df.empty:
        return pd.DataFrame()
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    return df

def load_wellness_data_filtered(start_date, end_date):
    """Cargar datos de wellness en rango de fechas"""
    conn = get_db_connection()
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
    """Cargar datos de composición corporal en rango de fechas"""
    conn = get_db_connection()
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
    """Cargar datos de actividades en rango de fechas"""
    conn = get_db_connection()
    query = """
        SELECT date, name, sport, duration_sec, tss, distance_m
        FROM activities
        WHERE date IS NOT NULL AND date >= ? AND date <= ?
        ORDER BY date DESC
    """
    df = pd.read_sql_query(query, conn, params=(start_date.isoformat(), end_date.isoformat()))
    
    if df.empty:
        return pd.DataFrame()
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    return df

def get_date_range(period):
    """Calcula el rango de fechas según el período seleccionado"""
    today = datetime.now().date()
    
    if period == "this_week":
        monday = today - timedelta(days=today.weekday())
        return monday, today
    elif period == "last_week":
        today_weekday = today.weekday()
        monday_last_week = today - timedelta(days=today_weekday + 7)
        sunday_last_week = monday_last_week + timedelta(days=6)
        return monday_last_week, sunday_last_week
    else:
        start_date = today - timedelta(days=period)
        return start_date, today

# ════════════════════════════════════════════════════════
# FUNCIONES DE TSB ZONES
# ════════════════════════════════════════════════════════

def get_tsb_zone(tsb_value):
    """Determinar zona TSB basado en rango exacto"""
    if tsb_value >= 10:
        return {
            'zone': 'Pico de forma',
            'range': '+10 a +20',
            'action': 'Carrera o sesión de calidad máxima',
            'emoji': '🏆',
            'color': '🟢'
        }
    elif tsb_value >= 3:      # 3 <= TSB < 10
        return {
            'zone': 'Fresco',
            'range': '+3 a +10',
            'action': 'Entrenamiento normal con calidad',
            'emoji': '✅',
            'color': '🟢'
        }
    elif tsb_value >= -5:     # -5 <= TSB < 3  →  cubre 0, -1, -2, -3, -4, -5
        return {
            'zone': 'Cargado',
            'range': '0 a -5',
            'action': 'Entrenar pero monitorear sensaciones',
            'emoji': '⚡',
            'color': '🟡'
        }
    elif tsb_value >= -15:    # -15 <= TSB < -5  →  cubre -6, -7 … -15
        return {
            'zone': 'Fatiga normal',
            'range': '-5 a -15',
            'action': 'Reducir intensidad, mantener volumen moderado',
            'emoji': '⚠️',
            'color': '🟠'
        }
    elif tsb_value >= -25:    # -25 <= TSB < -15
        return {
            'zone': 'Fatiga alta',
            'range': '-15 a -25',
            'action': 'Solo Z1-Z2, sin sesiones de calidad',
            'emoji': '⚠️',
            'color': '🟠'
        }
    elif tsb_value >= -35:    # -35 <= TSB < -25
        return {
            'zone': 'Zona de riesgo',
            'range': '-25 a -35',
            'action': 'Descanso activo únicamente',
            'emoji': '🛑',
            'color': '🔴'
        }
    else:                     # TSB < -35
        return {
            'zone': 'Peligro real',
            'range': 'Debajo de -35',
            'action': 'Descanso completo obligatorio',
            'emoji': '🚨',
            'color': '🔴'
        }

# ════════════════════════════════════════════════════════
# FUNCIONES DE VISUALIZACIÓN
# ════════════════════════════════════════════════════════

def plot_carga(df):
    """Gráfico de evolución CTL/ATL/TSB"""
    if df.empty:
        st.info("Sin datos disponibles")
        return
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['ctl'],
        name='CTL (Fitness)',
        mode='lines',
        line=dict(color='#3b82f6', width=2),
        hovertemplate='<b>%{x|%d %b}</b><br>CTL: %{y:.1f}<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['atl'],
        name='ATL (Fatiga)',
        mode='lines',
        line=dict(color='#f97316', width=2),
        hovertemplate='<b>%{x|%d %b}</b><br>ATL: %{y:.1f}<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['tsb'],
        name='TSB (Forma)',
        mode='lines',
        line=dict(color='#22c55e', width=2, dash='dash'),
        hovertemplate='<b>%{x|%d %b}</b><br>TSB: %{y:.1f}<extra></extra>'
    ))
    
    fig.add_hrect(y0=85, y1=90, fillcolor='#10b981', opacity=0.1, layer='below')
    
    fig.update_layout(
        title='',
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=0, b=0),
        height=350,
        font=dict(size=12),
        xaxis=dict(showgrid=True, gridwidth=0.5, gridcolor='rgba(0,0,0,0.05)'),
        yaxis=dict(showgrid=True, gridwidth=0.5, gridcolor='rgba(0,0,0,0.05)'),
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

def plot_hrv_rhr(df):
    """Gráfico HRV y FC Reposo"""
    if df.empty:
        st.info("Sin datos disponibles")
        return
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['hrv'],
        name='HRV (ms)',
        mode='lines',
        line=dict(color='#0ea5e9', width=2),
        yaxis='y1',
        hovertemplate='<b>%{x|%d %b}</b><br>HRV: %{y:.0f} ms<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['rhr'],
        name='FC Reposo (bpm)',
        mode='lines',
        line=dict(color='#ec4899', width=2),
        yaxis='y2',
        hovertemplate='<b>%{x|%d %b}</b><br>FC: %{y:.0f} bpm<extra></extra>'
    ))
    
    fig.update_layout(
        title='',
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=0, b=0),
        height=350,
        font=dict(size=12),
        yaxis=dict(title='HRV (ms)', showgrid=True, gridwidth=0.5),
        yaxis2=dict(title='FC (bpm)', overlaying='y', side='right', showgrid=False),
        xaxis=dict(showgrid=True, gridwidth=0.5, gridcolor='rgba(0,0,0,0.05)'),
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

def plot_composicion(df):
    """Gráfico de composición corporal"""
    if df.empty:
        st.info("Sin datos disponibles")
        return
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['weight_kg'],
        name='Peso (kg)',
        mode='lines+markers',
        line=dict(color='#fc4c02', width=2),
        yaxis='y1',
        hovertemplate='<b>%{x|%d %b}</b><br>Peso: %{y:.1f} kg<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['body_fat_pct'],
        name='Grasa (%)',
        mode='lines+markers',
        line=dict(color='#ec4899', width=2),
        yaxis='y2',
        hovertemplate='<b>%{x|%d %b}</b><br>Grasa: %{y:.1f}%<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['tbw_pct'],
        name='TBW (%)',
        mode='lines+markers',
        line=dict(color='#0ea5e9', width=2),
        yaxis='y3',
        hovertemplate='<b>%{x|%d %b}</b><br>TBW: %{y:.1f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title='',
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=0, b=0),
        height=350,
        font=dict(size=12),
        yaxis=dict(title='Peso (kg)', showgrid=True, gridwidth=0.5),
        yaxis2=dict(title='Grasa (%)', overlaying='y', side='right', showgrid=False),
        yaxis3=dict(title='TBW (%)', overlaying='y', side='right', anchor='free', position=1.0, showgrid=False),
        xaxis=dict(showgrid=True, gridwidth=0.5, gridcolor='rgba(0,0,0,0.05)'),
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ════════════════════════════════════════════════════════
# FUNCIONES DE ALERTAS Y MÉTRICAS
# ════════════════════════════════════════════════════════

def show_alerts(wellness_last, bodycomp_last, wellness_df):
    """Mostrar estado del atleta: CTL → Sueño → HRV → TSB"""
    alerts = []

    # 1. CTL
    if not wellness_last.empty:
        ctl = wellness_last['ctl'].values[0]
        if ctl < 85:
            points_needed = 85 - ctl
            alerts.append(f"🟡 **CTL en desarrollo:** {ctl:.0f} → Faltan {points_needed:.0f} puntos para rango óptimo")
        else:
            alerts.append(f"✅ **CTL en rango:** {ctl:.0f} puntos")

    # 2. Sueño
    if not wellness_last.empty and len(wellness_df) > 0:
        sleep_avg = wellness_df['sleep_hrs'].tail(7).mean()
        if sleep_avg < 7:
            alerts.append(f"🟡 **Sueño insuficiente:** {sleep_avg:.1f}h promedio < 7h → Prioriza descanso")
        else:
            alerts.append(f"✅ **Sueño adecuado:** {sleep_avg:.1f}h promedio")

    # 3. HRV
    if not wellness_last.empty and len(wellness_df) > 0:
        hrv_avg = wellness_df['hrv'].tail(7).mean()
        if hrv_avg > 50:
            alerts.append(f"ℹ️ **Recuperación excelente:** HRV promedio {hrv_avg:.0f} ms → Continúa con plan")
        else:
            alerts.append(f"🟡 **HRV bajo:** {hrv_avg:.0f} ms → Monitorear recuperación")

    # 4. TSB — siempre al final, con interpretación del rango
    if not wellness_last.empty:
        tsb = wellness_last['tsb'].values[0]
        tsb_zone = get_tsb_zone(tsb)
        alerts.append(f"{tsb_zone['color']} **TSB:** {tsb_zone['zone']} — {tsb_zone['action']}")

    # Mostrar bloque de alertas
    if alerts:
        st.warning("⚠️ ESTADO DEL ATLETA", icon="⚠️")
        for alert in alerts:
            st.markdown(f"• {alert}")

    # Alertas críticas separadas (TBW, TSB peligro)
    if not bodycomp_last.empty:
        tbw = bodycomp_last['tbw_pct'].values[0]
        if tbw < 64.5:
            st.error(f"🔴 **TBW crítico:** {tbw:.1f}% (target ≥64.5%) → Aumentar ingesta de agua")

    if not wellness_last.empty:
        tsb = wellness_last['tsb'].values[0]
        if tsb < -25:
            st.error(f"🔴 **CRÍTICO:** TSB {tsb:.1f} ({get_tsb_zone(tsb)['zone']}) → {get_tsb_zone(tsb)['action']}")

def calculate_ramp_rate(wellness_df):
    """Calcular Ramp Rate"""
    if len(wellness_df) < 2:
        return 0
    
    latest = wellness_df.iloc[-1]
    seven_days_ago = wellness_df[wellness_df['date'] <= latest['date'] - timedelta(days=7)]
    
    if seven_days_ago.empty:
        return 0
    
    ctl_7d_ago = seven_days_ago.iloc[-1]['ctl']
    ctl_now = latest['ctl']
    ramp_rate = ctl_now - ctl_7d_ago
    
    return ramp_rate

def calculate_hrv_rhr_ratio(wellness_last):
    """Calcular ratio HRV/RHR"""
    if wellness_last.empty:
        return 0
    
    hrv = wellness_last['hrv'].values[0]
    rhr = wellness_last['rhr'].values[0]
    
    if rhr == 0:
        return 0
    
    return (hrv / rhr) * 100

def calculate_period_summary(activities_df):
    """Calcular resumen del período"""
    if activities_df.empty:
        return {
            'total_time': 0,
            'sessions': 0,
            'total_tss': 0,
            'tss_per_day': 0,
            'sport_breakdown': {},
        }
    
    sport_mapping = {
        'ride': 'Bike',
        'virtualride': 'Bike',
        'cycling': 'Bike',
        'bike': 'Bike',
        'run': 'Run',
        'running': 'Run',
        'swim': 'Swim',
        'swimming': 'Swim',
        'hiit': 'Fuerza',
        'strength': 'Fuerza',
        'strengthtraining': 'Fuerza',
        'workout': 'Fuerza',
        'highintensityintervaltraining': 'Fuerza',
    }
    
    activities_df = activities_df.copy()
    activities_df['sport_consolidated'] = activities_df['sport'].str.lower().map(
        lambda x: sport_mapping.get(x, 'Otros')
    )
    
    total_time = activities_df['duration_sec'].sum() / 3600
    sessions = len(activities_df)
    total_tss = activities_df['tss'].sum()
    days = (activities_df['date'].max() - activities_df['date'].min()).days + 1
    tss_per_day = total_tss / max(days, 1)
    
    sport_breakdown = activities_df.groupby('sport_consolidated').agg({
        'duration_sec': 'sum'
    }).to_dict()['duration_sec']
    
    total_sport_time = sum(sport_breakdown.values())
    sport_pct = {sport: (time / total_sport_time * 100) for sport, time in sport_breakdown.items()}
    
    return {
        'total_time': total_time,
        'sessions': sessions,
        'total_tss': total_tss,
        'tss_per_day': tss_per_day,
        'sport_breakdown': sport_pct,
    }

# ════════════════════════════════════════════════════════
# MAIN APP
# ════════════════════════════════════════════════════════

def main():
    # Header
    st.markdown("# 📊 VITAL FORM")
    st.markdown("Dashboard de entrenamiento - 70.3 Ticoman (4 oct 2026)")
    
    # ════════════════════════════════════════════════════════
    # SECCIÓN 1: ESTADO ACTUAL (SIN FILTRO)
    # ════════════════════════════════════════════════════════
    
    # Cargar datos actuales (últimos 180 días)
    wellness_current = load_wellness_data_latest(180)
    bodycomp_current = load_bodycomp_data_latest(180)
    
    if wellness_current.empty or bodycomp_current.empty:
        st.warning("⚠️ No hay datos disponibles. Verifica la base de datos.")
        return
    
    wellness_last = wellness_current.tail(1)
    bodycomp_last = bodycomp_current.tail(1)
    
    # Alertas (PRIMERO)
    st.subheader("⚠️ Estado del Atleta")
    show_alerts(wellness_last, bodycomp_current, wellness_current)
    
    st.divider()
    
    # Carga & Recuperación (3 columnas)
    st.subheader("📊 Carga & Recuperación")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Evolución de Carga**")
        
        if not wellness_last.empty:
            ctl_now = wellness_last['ctl'].values[0]
            ctl_7d = wellness_current.iloc[0]['ctl'] if len(wellness_current) > 0 else ctl_now
            ctl_change = ctl_now - ctl_7d
            ctl_trend = "↑" if ctl_change > 0 else ("↓" if ctl_change < 0 else "→")
            st.metric("CTL Hoy", f"{ctl_now:.0f}", f"{ctl_trend} {ctl_change:+.1f}")
        
        ramp_rate = calculate_ramp_rate(wellness_current)
        ramp_status = "✓ OK" if ramp_rate <= 15 else "⚠️ Alto"
        st.metric("Ramp Rate", f"{ramp_rate:.1f} pts/sem", ramp_status)
        
        if not wellness_last.empty:
            atl_now = wellness_last['atl'].values[0]
            atl_7d = wellness_current.iloc[0]['atl'] if len(wellness_current) > 0 else atl_now
            atl_change = atl_now - atl_7d
            atl_trend = "↑" if atl_change > 0 else ("↓" if atl_change < 0 else "→")
            st.metric("ATL (Fatiga)", f"{atl_now:.0f}", f"{atl_trend} {atl_change:+.1f}")
        
        if not wellness_last.empty:
            tsb_now = wellness_last['tsb'].values[0]
            tsb_7d = wellness_current.iloc[0]['tsb'] if len(wellness_current) > 0 else tsb_now
            tsb_change = tsb_now - tsb_7d
            tsb_trend = "↑" if tsb_change > 0 else ("↓" if tsb_change < 0 else "→")
            st.metric("TSB (Forma)", f"{tsb_now:.0f}", f"{tsb_trend} {tsb_change:+.1f}")
            
            # Solo métrica, sin leyenda aquí
    
    with col2:
        st.markdown("**Indicadores de Recuperación**")
        
        if not wellness_last.empty:
            hrv = wellness_last['hrv'].values[0]
            hrv_avg = wellness_current['hrv'].tail(7).mean()
            hrv_trend = "↑" if hrv > hrv_avg else ("↓" if hrv < hrv_avg else "→")
            st.metric("HRV (7d avg)", f"{hrv_avg:.0f} ms", f"{hrv_trend} Hoy: {hrv:.0f}")
        
        hrv_rhr_ratio = calculate_hrv_rhr_ratio(wellness_last)
        ratio_status = "✓ Excelente" if hrv_rhr_ratio > 100 else ("✓ Normal" if hrv_rhr_ratio > 50 else "⚠️ Baja")
        st.metric("HRV/RHR Ratio", f"{hrv_rhr_ratio:.1f}", ratio_status)
        
        if not wellness_last.empty:
            rhr = wellness_last['rhr'].values[0]
            rhr_avg = wellness_current['rhr'].tail(7).mean()
            rhr_trend = "↑" if rhr > rhr_avg else ("↓" if rhr < rhr_avg else "→")
            st.metric("FC Reposo", f"{rhr:.0f} bpm", f"{rhr_trend} Avg: {rhr_avg:.0f}")
        
        if not wellness_last.empty:
            sleep_hrs = wellness_last['sleep_hrs'].values[0]
            sleep_avg = wellness_current['sleep_hrs'].tail(7).mean()
            sleep_status = "✓ OK" if sleep_avg >= 7.5 else ("⚠️ Bajo" if sleep_avg < 7 else "→ Normal")
            st.metric("Sueño (7d avg)", f"{sleep_avg:.1f} h", sleep_status)
    
    with col3:
        st.markdown("**Composición Corporal**")
        
        if not bodycomp_last.empty:
            weight = bodycomp_last['weight_kg'].values[0]
            weight_trend = "↓" if len(bodycomp_current) > 1 and weight < bodycomp_current.iloc[-2]['weight_kg'] else "→"
            st.metric("Peso", f"{weight:.1f} kg", f"{weight_trend} Target: 80-81kg")
        
        if not bodycomp_last.empty:
            fat = bodycomp_last['body_fat_pct'].values[0]
            fat_trend = "↓" if len(bodycomp_current) > 1 and fat < bodycomp_current.iloc[-2]['body_fat_pct'] else "→"
            st.metric("Grasa", f"{fat:.1f}%", f"{fat_trend} Target: 12-12.5%")
        
        if not bodycomp_last.empty:
            tbw = bodycomp_last['tbw_pct'].values[0]
            tbw_status = "✓ OK" if tbw >= 64.5 else ("⚠️ Bajo" if tbw >= 63.5 else "🔴 Crítico")
            st.metric("TBW", f"{tbw:.1f}%", f"{tbw_status}")
        
        if not bodycomp_last.empty:
            mm = bodycomp_last['skeletal_muscle_kg'].values[0]
            mm_trend = "↑" if len(bodycomp_current) > 1 and mm > bodycomp_current.iloc[-2]['skeletal_muscle_kg'] else "→"
            st.metric("Masa Muscular", f"{mm:.1f} kg", f"{mm_trend} Floor: 40kg")
    
    st.divider()
    
    # ════════════════════════════════════════════════════════
    # SECCIÓN 2: DATOS FILTRADOS POR PERÍODO
    # ════════════════════════════════════════════════════════
    
    # Filtro de período
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        period_options = {
            "Esta semana": "this_week",
            "Semana pasada": "last_week",
            "Últimos 7 días": 7,
            "Últimos 30 días": 30,
            "Últimos 60 días": 60,
            "Últimos 90 días": 90,
        }
        selected_period = st.selectbox(
            "Período",
            options=list(period_options.keys()),
            index=2,
            label_visibility="collapsed"
        )
        period_key = period_options[selected_period]
    
    with col3:
        if st.button("🔄 Actualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Calcular rango de fechas
    start_date, end_date = get_date_range(period_key)
    
    # Cargar datos filtrados
    wellness_df = load_wellness_data_filtered(start_date, end_date)
    activities_df = load_activities_data_filtered(start_date, end_date)
    
    # Resumen por Período
    st.subheader("📈 Resumen del Período")
    summary = calculate_period_summary(activities_df)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Tiempo Total", f"{summary['total_time']:.1f}h", "horas")
    with col2:
        st.metric("Sesiones", f"{summary['sessions']}", "entrenamientos")
    with col3:
        st.metric("Carga Total (TSS)", f"{summary['total_tss']:.0f}", "TSS")
    with col4:
        st.metric("TSS/día promedio", f"{summary['tss_per_day']:.0f}", "TSS/día")
    
    st.markdown("**Distribución por deporte**")
    if summary['sport_breakdown']:
        cols = st.columns(len(summary['sport_breakdown']))
        for idx, (sport, pct) in enumerate(summary['sport_breakdown'].items()):
            with cols[idx]:
                st.metric(f"{sport}", f"{pct:.0f}%", help=f"{pct:.1f}% del tiempo total")
    else:
        st.info("Sin datos de actividades")
    
    st.divider()
    
    # Zonas de FC
    st.subheader("⏱️ Tiempo en Zonas de FC")
    
    zones_data = [
        {'name': 'Z1', 'range': '<110 bpm', 'time': 180, 'color': '#9ca3af'},
        {'name': 'Z2', 'range': '110–127 bpm', 'time': 312, 'color': '#3b82f6'},
        {'name': 'Z3', 'range': '127–150 bpm', 'time': 663, 'color': '#22c55e'},
        {'name': 'Z4', 'range': '150–162 bpm', 'time': 175, 'color': '#f97316'},
        {'name': 'Z5', 'range': '>162 bpm', 'time': 0, 'color': '#ef4444'},
    ]
    
    total_zone_time = sum(z['time'] for z in zones_data)
    
    for zone in zones_data:
        time_min = zone['time']
        pct = (time_min / total_zone_time * 100) if total_zone_time > 0 else 0
        hours = time_min // 60
        mins = time_min % 60
        
        col1, col2, col3, col4 = st.columns([1.2, 2.5, 0.6, 1])
        
        with col1:
            st.caption(f"**{zone['name']}** {zone['range']}")
        
        with col2:
            html_bar = f"""
            <div style="background-color: #333; border-radius: 4px; height: 24px; overflow: hidden; width: 100%;">
                <div style="background-color: {zone['color']}; height: 100%; width: {pct}%; border-radius: 4px;"></div>
            </div>
            """
            st.markdown(html_bar, unsafe_allow_html=True)
        
        with col3:
            st.caption(f"**{pct:.0f}%**")
        
        with col4:
            st.caption(f"{hours}h {mins}m")
    
    st.divider()
    
    # Gráficos de evolución
    st.subheader("📊 Gráficos de Evolución")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Evolución de Carga**")
        plot_carga(wellness_df)
    
    with col2:
        st.markdown("**Recuperación (HRV & FC)**")
        plot_hrv_rhr(wellness_df)
    
    st.markdown("**Composición Corporal**")
    bodycomp_df = load_bodycomp_data_filtered(start_date, end_date)
    plot_composicion(bodycomp_df)

if __name__ == "__main__":
    main()
