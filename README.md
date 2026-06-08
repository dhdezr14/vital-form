# VITAL FORM - Streamlit Dashboard

Dashboard interactivo de entrenamiento para atletas de triatlón.

## Instalación

### 1. Requisitos previos

- Python 3.10+ instalado
- Base de datos SQLite (`data/triathlon.db`) con tablas de wellness y body_composition

### 2. Setup inicial

```bash
# Crear entorno virtual (recomendado)
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En Mac/Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Estructura de carpetas esperada

```
vital-form-streamlit/
├── app.py
├── requirements.txt
├── README.md
└── data/
    └── triathlon.db          # Tu base de datos SQLite
```

**Importante:** Copia tu archivo `triathlon.db` desde la carpeta `vital-form` a la subcarpeta `data/`

## Uso

### Ejecutar localmente

```bash
streamlit run app.py
```

La app se abrirá automáticamente en `http://localhost:8501`

### Uso en la app

1. **Selecciona el período:** Últ. 7/30/60/90 días
2. **Botón Actualizar:** Recarga datos de la BD
3. **Navega por las secciones:**
   - 🎯 Objetivos (Peso, Grasa, TBW, CTL)
   - ⚠️ Alertas automáticas
   - 📈 Evolución de Carga (CTL/ATL/TSB)
   - 🔋 Recuperación (HRV, FC Reposo)
   - ❤️ Composición Corporal
   - 📋 Historial de datos

### Interactividad

- **Hover en gráficos:** Ver valores exactos del día
- **Zoom:** Click + arrastra para zoom. Doble click para reset
- **Filtros dinámicos:** Los gráficos se actualizan al cambiar período

## Próximos pasos

### Fase 2: Integración Intervals.icu
```python
# Sincronización automática de datos cada 6 horas
# sync_intervals.py → escribe en SQLite → Streamlit lee
```

### Fase 3: Alertas avanzadas
- Tendencias automáticas (↑ ↓ →)
- Zonas de FC con colores
- Recomendaciones basadas en métricas

### Fase 4: Deployment
```bash
# Deploy en Streamlit Cloud (gratis)
# 1. Push código a GitHub
# 2. Conectar en https://share.streamlit.io
# 3. App accesible desde cualquier lado
```

## Troubleshooting

### Error: "Base de datos no encontrada"
- Verifica que `data/triathlon.db` existe
- Asegúrate de copiar el archivo desde tu carpeta `vital-form` local

### Gráficos vacíos
- Comprueba que hay datos en las tablas: `wellness` y `body_composition`
- Ejecuta: `sqlite3 data/triathlon.db "SELECT COUNT(*) FROM wellness"`

### App lenta
- Usa filtro de período más corto (7 o 30 días)
- Streamlit cachea automáticamente, pero puedes limpiar:
  ```bash
  rm -rf ~/.streamlit/cache
  ```

## Base de datos requerida

### Tabla: wellness
```
date, ctl, atl, tsb, eftp, hrv, rhr, sleep_secs
```

### Tabla: body_composition
```
date, weight_kg, body_fat_pct, muscle_mass_kg, 
skeletal_muscle_kg, tbw_pct, visceral_fat
```

Si tu BD tiene estructura diferente, edita las consultas SQL en `app.py` (función `load_wellness_data()` y `load_bodycomp_data()`).

## Contacto

Dashboard creado para 70.3 Ticoman (4 oct 2026).
