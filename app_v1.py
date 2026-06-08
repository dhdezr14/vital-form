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

@st.cache_data(ttl=3600)
def load_wellness_data(days_back=90):
    """Cargar datos de wellness desde BD"""
    conn = get_db_connection()
    query = """
        SELECT date, ctl, atl, tsb, eftp, hrv, rhr, sleep_secs
        FROM wellness
        WHERE date IS NOT NULL
        ORDER BY date DESC
        LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=(days_back,))
    
    if df.empty:
        return pd.DataFrame()
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    df['sleep_hrs'] = df['sleep_secs'] / 3600
    return df

@st.cache_data(ttl=3600)
def load_bodycomp_data(days_back=90):
    """Cargar datos de composición corporal"""
    conn = get_db_connection()
    query = """
        SELECT date, weight_kg, body_fat_pct, muscle_mass_kg, 
               skeletal_muscle_kg, tbw_pct, visceral_fat
        FROM body_composition
        WHERE date IS NOT NULL
        ORDER BY date DESC
        LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=(days_back,))
    
    if df.empty:
        return pd.DataFrame()
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    return df

@st.cache_data(ttl=3600)
@st.cache_data(ttl=3600)
def load_activities_data(days_back=90):
    """Cargar datos de actividades"""
    conn = get_db_connection()
    
    # Calcular fecha límite
    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    query = """
        SELECT date, name, sport, duration_sec, tss, distance_m
        FROM activities
        WHERE date IS NOT NULL AND date >= ?
        ORDER BY date DESC
    """
    df = pd.read_sql_query(query, conn, params=(cutoff_date,))
    
    if df.empty:
        return pd.DataFrame()
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    return df

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

def show_alerts(wellness_last, bodycomp_last):
    """Mostrar cuadro de alertas"""
    alerts = []
    
    if not bodycomp_last.empty:
        tbw = bodycomp_last['tbw_pct'].values[0]
        if tbw < 64.5:
            alerts.append(f"🔴 **TBW crítico:** {tbw:.1f}% (target ≥64.5%) → Aumentar ingesta de agua")
    
    if not wellness_last.empty:
        ctl = wellness_last['ctl'].values[0]
        if ctl < 85:
            points_needed = 85 - ctl
            alerts.append(f"🟡 **CTL en desarrollo:** {ctl:.0f} → Faltan {points_needed:.0f} puntos para rango óptimo")
    
    if alerts:
        with st.container():
            st.warning("⚠️ ALERTAS DE RENDIMIENTO", icon="⚠️")
            for alert in alerts:
                st.markdown(f"• {alert}")

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
            "Últimos 7 días": 7,
            "Últimos 30 días": 30,
            "Últimos 60 días": 60,
            "Últimos 90 días": 90,
        }
        selected_period = st.selectbox(
            "Período",
            options=list(period_options.keys()),
            index=1,
            label_visibility="collapsed"
        )
        days = period_options[selected_period]
    
    with col3:
        if st.button("🔄 Actualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Cargar datos
    wellness_df = load_wellness_data(days)
    bodycomp_df = load_bodycomp_data(days)
    
    if wellness_df.empty or bodycomp_df.empty:
        st.warning("⚠️ No hay datos disponibles. Verifica la base de datos.")
        return
    
    wellness_last = wellness_df.tail(1)
    bodycomp_last = bodycomp_df.tail(1)
    
    # Objetivos
    st.subheader("🎯 Objetivos Ticoman")
    show_objectives(wellness_last, bodycomp_last)
    
    st.divider()
    
    # Alertas
    show_alerts(wellness_last, bodycomp_last)
    
    st.divider()
    
    # Gráfico de carga
    st.subheader("📈 Evolución de Carga")
    plot_carga(wellness_df)
    
    st.divider()
    
    # Recuperación
    st.subheader("🔋 Recuperación")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if not wellness_last.empty:
            hrv = wellness_last['hrv'].values[0]
            st.metric("HRV", f"{hrv:.0f} ms", "Variabilidad cardíaca")
    
    with col2:
        if not wellness_last.empty:
            rhr = wellness_last['rhr'].values[0]
            st.metric("FC Reposo", f"{rhr:.0f} bpm", "Frecuencia cardíaca")
    
    with col3:
        if not wellness_last.empty:
            sleep_hrs = wellness_last['sleep_hrs'].values[0]
            st.metric("SUEÑO", f"{sleep_hrs:.1f} h", "Horas (target ≥7.5h)")
    
    with col4:
        if not wellness_last.empty:
            sleep_avg = wellness_df['sleep_hrs'].tail(7).mean()
            st.metric("PROMEDIO 7D", f"{sleep_avg:.1f} h", "Tendencia de sueño")
    
    plot_hrv_rhr(wellness_df)
    
    st.divider()
    
    # Composición corporal
    st.subheader("❤️ Salud General")
    plot_composicion(bodycomp_df)
    
    st.divider()
    
    # Resumen por Período
    st.subheader("📊 Resumen por período")
    
    activities_df = load_activities_data(days)
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
    
    # Distribución por deporte
    st.markdown("**Distribución por deporte**")
    if summary['sport_breakdown']:
        sport_icons = {
            'Swim': 'natacion',
            'Run': 'carrera',
            'Bike': 'bici',
            'Fuerza': 'fuerza',
        }
        
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

    st.markdown("**Tiempo en Zonas de FC**")
    
    # Datos de zonas con colores y rangos
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
            # Barra HTML personalizada con color
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
