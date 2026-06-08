# ============================================================
# VITAL FORM — Configuración
# Copia este archivo como config.py y completa tus datos
# NO subas config.py a GitHub
# ============================================================

ATHLETE_ID = "i347382"
API_KEY = "4xkunn4sy3cls8dfl3ep7r8zx"   # Reemplazar con tu API key de Intervals.icu

DB_PATH = "data/triathlon.db"

# Athlete profile
ATHLETE_WEIGHT_KG = 82
ATHLETE_FTP_W = 273
ATHLETE_MAX_HR = 162

# Zonas de FC de laboratorio (5 zonas, basadas en ergoespirometría)
# VT1=110bpm, VT2=127bpm, RCP=150bpm, FCmax=162bpm
# Cada zona: (límite inferior, límite superior) en bpm
HR_ZONES = [
    {"name": "Z1", "label": "Recuperación", "min": 0,   "max": 110, "color": "#9ca3af"},
    {"name": "Z2", "label": "Aeróbico",     "min": 110, "max": 127, "color": "#3b82f6"},
    {"name": "Z3", "label": "Tempo",        "min": 127, "max": 150, "color": "#22c55e"},
    {"name": "Z4", "label": "Umbral",       "min": 150, "max": 162, "color": "#f97316"},
    {"name": "Z5", "label": "VO2max",       "min": 162, "max": 999, "color": "#ef4444"},
]

# Race target
RACE_DATE = "2026-10-04"
RACE_NAME = "70.3 Ticoman"
