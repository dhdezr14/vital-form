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
        # Lunes de esta semana hasta hoy
        monday = today - timedelta(days=today.weekday())
        return monday, today
    elif period == "last_week":
        # Lunes de semana pasada hasta domingo de semana pasada
        today_weekday = today.weekday()
        monday_last_week = today - timedelta(days=today_weekday + 7)
        sunday_last_week = monday_last_week + timedelta(days=6)
        return monday_last_week, sunday_last_week
    else:
        # Últimos N días
        start_date = today - timedelta(days=period)
        return start_date, today

# ════════════════════════════════════════════════════════
# FUNCIONES DE VISUALIZACIÓN
# ════════════════════════════════════════════════════════

def plot_carga(df):
    """Gráfico de evolución CTL/ATL/TSB (líneas estilo Intervals)"""
    if df.empty:
        st.info("Sin datos disponibles")
        return
    
    fig = go.Figure()
    
    # CTL
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['ctl'],
        name='CTL (Fitness)',
        mode='lines',
        line=dict(color='#3b82f6', width=2),
        hovertemplate='<b>%{x|%d %b}</b><br>CTL: %{y:.1f}<extra></extra>'
    ))
    
    # ATL
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['atl'],
        name='ATL (Fatiga)',
        mode='lines',
        line=dict(color='#f97316', width=2),
        hovertemplate='<b>%{x|%d %b}</b><br>ATL: %{y:.1f}<extra></extra>'
    ))
    
    # TSB (punteado)
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['tsb'],
        name='TSB (Forma)',
        mode='lines',
        line=dict(color='#22c55e', width=2, dash='dash'),
        hovertemplate='<b>%{x|%d %b}</b><br>TSB: %{y:.1f}<extra></extra>'
    ))
    
    # Rango óptimo para CTL (sombreado)
    fig.add_hrect(y0=85, y1=90, fillcolor='#10b981', opacity=0.1, layer='below', 
                  annotation_text='Rango óptimo CTL', annotation_position='right')
    
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
# FUNCIONES DE CARDS Y ALERTAS
# ════════════════════════════════════════════════════════

def show_objectives(wellness_last, bodycomp_last):
    """Mostrar cards de objetivos"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        weight = bodycomp_last['weight_kg'].values[0] if not bodycomp_last.empty else 0
        target_min, target_max = 80, 81
        progress = min(100, max(0, (target_max - weight) / (target_max - 78) * 100))
        status = "✓ On track" if weight <= target_max else ("⚠️ Ajustar" if weight <= 82 else "❌ Crítico")
        status_color = "🟢" if weight <= target_max else ("🟡" if weight <= 82 else "🔴")
        
        st.metric("PESO", f"{weight:.1f} kg", f"Target: {target_min}-{target_max}kg")
        st.progress(progress / 100)
        st.caption(f"{status_color} {status}")
    
    with col2:
        fat = bodycomp_last['body_fat_pct'].values[0] if not bodycomp_last.empty else 0
        target_min, target_max = 12, 12.5
        progress = min(100, max(0, (fat - 12) / (15 - 12) * 100))
        status = "✓ On track" if fat <= target_max else ("⚠️ Ajustar" if fat <= 13.5 else "❌ Crítico")
        status_color = "🟢" if fat <= target_max else ("🟡" if fat <= 13.5 else "🔴")
        
        st.metric("GRASA", f"{fat:.1f}%", f"Target: {target_min}-{target_max}%")
        st.progress(progress / 100)
        st.caption(f"{status_color} {status}")
    
    with col3:
        tbw = bodycomp_last['tbw_pct'].values[0] if not bodycomp_last.empty else 0
        target_min = 64.5
        progress = min(100, max(0, (tbw - 62) / (66 - 62) * 100))
        status = "✓ On track" if tbw >= target_min else ("⚠️ Atención" if tbw >= 63.5 else "❌ PRIORIDAD")
        status_color = "🟢" if tbw >= target_min else ("🟡" if tbw >= 63.5 else "🔴")
        
        st.metric("TBW", f"{tbw:.1f}%", f"Target: ≥{target_min}%")
        st.progress(progress / 100)
        st.caption(f"{status_color} {status}")
    
    with col4:
        ctl = wellness_last['ctl'].values[0] if not wellness_last.empty else 0
        target_min, target_max = 85, 90
        progress = min(100, max(0, (ctl - 60) / (95 - 60) * 100))
        status = "✓ On track" if (target_min <= ctl <= target_max) else ("En desarrollo" if ctl >= 80 else "Iniciando")
        status_color = "🟢" if (target_min <= ctl <= target_max) else "🟡"
        
        st.metric("CTL", f"{ctl:.0f}", f"Target: {target_min}-{target_max}")
        st.progress(progress / 100)
        st.caption(f"{status_color} {status}")

def show_alerts(wellness_last, bodycomp_last, wellness_df):
    """Mostrar cuadro de alertas"""
    alerts_critical = []
    alerts_warning = []
    alerts_info = []
    
    # ALERTAS CRÍTICAS
    if not bodycomp_last.empty:
        tbw = bodycomp_last['tbw_pct'].values[0]
        if tbw < 64.5:
            alerts_critical.append(f"🔴 **TBW crítico:** {tbw:.1f}% (target ≥64.5%) → Aumentar ingesta de agua")
    
    if not wellness_last.empty:
        tsb = wellness_last['tsb'].values[0]
        if tsb < -10:
            alerts_critical.append(f"🔴 **Sobreentrenado:** TSB {tsb:.1f} < -10 → Reduce 20% carga, toma recovery day")
    
    # ALERTAS AMARILLAS
    if not wellness_last.empty:
        ctl = wellness_last['ctl'].values[0]
        if ctl < 85:
            points_needed = 85 - ctl
            alerts_warning.append(f"🟡 **CTL en desarrollo:** {ctl:.0f} → Faltan {points_needed:.0f} puntos para rango óptimo")
    
    if not wellness_last.empty:
        sleep_avg = wellness_df['sleep_hrs'].tail(7).mean() if len(wellness_df) > 0 else 0
        if sleep_avg < 7:
            alerts_warning.append(f"🟡 **Sueño insuficiente:** {sleep_avg:.1f}h promedio < 7h → Prioriza descanso")
    
    # ALERTAS INFORMATIVAS
    if not wellness_last.empty and len(wellness_df) > 0:
        hrv_avg = wellness_df['hrv'].tail(7).mean()
        if hrv_avg > 50:
            alerts_info.append(f"ℹ️ **Recuperación excelente:** HRV promedio {hrv_avg:.0f} ms → Continúa con plan")
    
    # Mostrar alertas
    if alerts_critical or alerts_warning or alerts_info:
        st.warning("⚠️ ESTADO DEL ATLETA", icon="⚠️")
        for alert in alerts_critical:
            st.markdown(f"• {alert}")
        for alert in alerts_warning:
            st.markdown(f"• {alert}")
        for alert in alerts_info:
            st.markdown(f"• {alert}")
    else:
        st.success("✓ Todo en orden", icon="✓")

# ════════════════════════════════════════════════════════
# FUNCIONES DE RESUMEN
# ════════════════════════════════════════════════════════

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
    
    # Mapeo de deportes a categorías consolidadas
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
    
    # Aplicar mapeo
    activities_df = activities_df.copy()
    activities_df['sport_consolidated'] = activities_df['sport'].str.lower().map(
        lambda x: sport_mapping.get(x, 'Otros')
    )
    
    total_time = activities_df['duration_sec'].sum() / 3600  # en horas
    sessions = len(activities_df)
    total_tss = activities_df['tss'].sum()
    days = (activities_df['date'].max() - activities_df['date'].min()).days + 1
    tss_per_day = total_tss / max(days, 1)
    
    # Desglose por deporte consolidado
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

def calculate_ramp_rate(wellness_df):
    """Calcular Ramp Rate (cambio de CTL en 7 días)"""
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

# ════════════════════════════════════════════════════════
# MAIN APP
# ════════════════════════════════════════════════════════

def main():
    # Header
    st.markdown("# 📊 VITAL FORM")
    st.markdown("Dashboard de entrenamiento - 70.3 Ticoman (4 oct 2026)")
    
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
    
    # Cargar datos
    wellness_df = load_wellness_data_filtered(start_date, end_date)
    bodycomp_df = load_bodycomp_data_filtered(start_date, end_date)
    
    if wellness_df.empty or bodycomp_df.empty:
        st.warning("⚠️ No hay datos disponibles para el período seleccionado. Verifica la base de datos.")
        return
    
    wellness_last = wellness_df.tail(1)
    bodycomp_last = bodycomp_df.tail(1)
    
    # Objetivos
    st.subheader("🎯 Objetivos Ticoman")
    show_objectives(wellness_last, bodycomp_last)
    
    st.divider()
    
    # Alertas
    show_alerts(wellness_last, bodycomp_last, wellness_df)
    
    st.divider()
    
    # Gráfico de carga
    st.subheader("📈 Evolución de Carga")
    plot_carga(wellness_df)
    
    st.divider()
    
    # Carga & Recuperación (2 columnas)
    st.subheader("📊 Carga & Recuperación")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Evolución de Carga (7 días)**")
        
        if not wellness_last.empty:
            ctl_now = wellness_last['ctl'].values[0]
            ctl_7d = wellness_df.iloc[0]['ctl'] if len(wellness_df) > 0 else ctl_now
            ctl_change = ctl_now - ctl_7d
            ctl_trend = "↑" if ctl_change > 0 else ("↓" if ctl_change < 0 else "→")
            
            st.metric("CTL Hoy", f"{ctl_now:.0f}", f"{ctl_trend} {ctl_change:+.1f}")
        
        ramp_rate = calculate_ramp_rate(wellness_df)
        ramp_status = "✓ OK" if ramp_rate <= 15 else "⚠️ Alto"
        st.metric("Ramp Rate", f"{ramp_rate:.1f} pts/sem", ramp_status)
        
        if not wellness_last.empty:
            atl_now = wellness_last['atl'].values[0]
            atl_7d = wellness_df.iloc[0]['atl'] if len(wellness_df) > 0 else atl_now
            atl_change = atl_now - atl_7d
            atl_trend = "↑" if atl_change > 0 else ("↓" if atl_change < 0 else "→")
            
            st.metric("ATL (Fatiga)", f"{atl_now:.0f}", f"{atl_trend} {atl_change:+.1f}")
        
        if not wellness_last.empty:
            tsb_now = wellness_last['tsb'].values[0]
            tsb_7d = wellness_df.iloc[0]['tsb'] if len(wellness_df) > 0 else tsb_now
            tsb_change = tsb_now - tsb_7d
            tsb_trend = "↑" if tsb_change > 0 else ("↓" if tsb_change < 0 else "→")
            
            st.metric("TSB (Forma)", f"{tsb_now:.0f}", f"{tsb_trend} {tsb_change:+.1f}")
    
    with col2:
        st.markdown("**Indicadores de Recuperación**")
        
        if not wellness_last.empty:
            hrv = wellness_last['hrv'].values[0]
            hrv_avg = wellness_df['hrv'].tail(7).mean()
            hrv_trend = "↑" if hrv > hrv_avg else ("↓" if hrv < hrv_avg else "→")
            
            st.metric("HRV (7d avg)", f"{hrv_avg:.0f} ms", f"{hrv_trend} Hoy: {hrv:.0f}")
        
        hrv_rhr_ratio = calculate_hrv_rhr_ratio(wellness_last)
        ratio_status = "✓ Excelente" if hrv_rhr_ratio > 100 else ("✓ Normal" if hrv_rhr_ratio > 50 else "⚠️ Baja")
        st.metric("HRV/RHR Ratio", f"{hrv_rhr_ratio:.1f}", ratio_status)
        
        if not wellness_last.empty:
            rhr = wellness_last['rhr'].values[0]
            rhr_avg = wellness_df['rhr'].tail(7).mean()
            rhr_trend = "↑" if rhr > rhr_avg else ("↓" if rhr < rhr_avg else "→")
            
            st.metric("FC Reposo", f"{rhr:.0f} bpm", f"{rhr_trend} Avg: {rhr_avg:.0f}")
        
        if not wellness_last.empty:
            sleep_hrs = wellness_last['sleep_hrs'].values[0]
            sleep_avg = wellness_df['sleep_hrs'].tail(7).mean()
            sleep_status = "✓ OK" if sleep_avg >= 7.5 else ("⚠️ Bajo" if sleep_avg < 7 else "→ Normal")
            
            st.metric("Sueño (7d avg)", f"{sleep_avg:.1f} h", sleep_status)
    
    st.divider()
    
    # Recuperación detallada
    st.subheader("🔋 Recuperación")
    plot_hrv_rhr(wellness_df)
    
    st.divider()
    
    # Composición corporal
    st.subheader("❤️ Salud General")
    plot_composicion(bodycomp_df)
    
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
    
    # Resumen por Período
    st.subheader("📈 Resumen del Período")
    
    activities_df = load_activities_data_filtered(start_date, end_date)
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
                st.metric(
                    f"{sport}",
                    f"{pct:.0f}%",
                    help=f"{pct:.1f}% del tiempo total"
                )
    else:
        st.info("Sin datos de actividades")
    
    st.divider()
    
    # Tabla de datos
    st.subheader("📋 Historial Wellness")
    st.dataframe(
        wellness_df[['date', 'ctl', 'atl', 'tsb', 'eftp', 'hrv', 'rhr', 'sleep_hrs']]
        .rename(columns={
            'date': 'Fecha',
            'ctl': 'CTL',
            'atl': 'ATL',
            'tsb': 'TSB',
            'eftp': 'eFTP',
            'hrv': 'HRV',
            'rhr': 'FC Rep',
            'sleep_hrs': 'Sueño'
        })
        .sort_values('Fecha', ascending=False)
        .reset_index(drop=True),
        use_container_width=True,
        hide_index=True
    )

if __name__ == "__main__":
    main()
