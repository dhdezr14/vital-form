-- ============================================================
-- TRIATHLON DASHBOARD — Schema SQLite
-- Fuentes: Intervals.icu, Fitdays (manual), Training Peaks (manual)
-- ============================================================

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ------------------------------------------------------------
-- ACTIVIDADES (desde Intervals.icu)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activities (
    id              TEXT PRIMARY KEY,   -- ID de Intervals.icu
    date            TEXT NOT NULL,      -- YYYY-MM-DD
    name            TEXT,
    sport           TEXT,               -- Ride, Run, Swim, VirtualRide
    duration_sec    INTEGER,
    distance_m      REAL,
    tss             REAL,
    ctl             REAL,
    atl             REAL,
    tsb             REAL,
    avg_power_w     REAL,
    norm_power_w    REAL,
    avg_hr          REAL,
    max_hr          REAL,
    avg_cadence     REAL,
    elevation_m     REAL,
    calories        REAL,
    avg_pace_ms     REAL,               -- m/s para running
    eftp            REAL,               -- eFTP del día
    hr_zone_times   TEXT,               -- JSON array [Z1..Z7] en segundos
    created_at      TEXT DEFAULT (datetime('now'))
);

-- ------------------------------------------------------------
-- WELLNESS / RECUPERACIÓN (desde Intervals.icu)
-- Sueño, HRV, body battery, stress
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wellness (
    date            TEXT PRIMARY KEY,   -- YYYY-MM-DD
    ctl             REAL,
    atl             REAL,
    tsb             REAL,
    eftp            REAL,
    ramprate        REAL,
    ctl_load        REAL,
    atl_load        REAL,
    sleep_secs      INTEGER,
    sleep_score     REAL,
    hrv             REAL,               -- VFC ms
    hrv_baseline    REAL,
    rhr             REAL,               -- FC reposo
    body_battery_low  INTEGER,
    body_battery_high INTEGER,
    stress_avg      REAL,
    respiration     REAL,
    spo2            REAL,
    steps           INTEGER,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- ------------------------------------------------------------
-- COMPOSICIÓN CORPORAL (Fitdays — carga manual via imagen)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS body_composition (
    date            TEXT PRIMARY KEY,   -- YYYY-MM-DD
    weight_kg       REAL,
    body_fat_pct    REAL,
    muscle_mass_kg  REAL,
    skeletal_muscle_kg REAL,
    tbw_pct         REAL,               -- Agua corporal total %
    visceral_fat    INTEGER,
    bmr_kcal        INTEGER,
    bone_mass_kg    REAL,
    body_age        INTEGER,
    bmi             REAL,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- ------------------------------------------------------------
-- PLANIFICACIÓN SEMANAL (Training Peaks — carga manual)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS weekly_plan (
    week_start      TEXT PRIMARY KEY,   -- YYYY-MM-DD (lunes)
    week_end        TEXT,
    planned_tss     REAL,
    actual_tss      REAL,
    planned_hours   REAL,
    actual_hours    REAL,
    phase           TEXT,               -- Base, Build, Peak, Race, Recovery
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- ------------------------------------------------------------
-- SYNC LOG — para no re-descargar lo ya descargado
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sync_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT,               -- intervals, fitdays, training_peaks
    synced_at       TEXT DEFAULT (datetime('now')),
    records_added   INTEGER,
    date_from       TEXT,
    date_to         TEXT,
    notes           TEXT
);

-- ------------------------------------------------------------
-- ÍNDICES
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(date);
CREATE INDEX IF NOT EXISTS idx_activities_sport ON activities(sport);
CREATE INDEX IF NOT EXISTS idx_wellness_date ON wellness(date);
CREATE INDEX IF NOT EXISTS idx_body_comp_date ON body_composition(date);
