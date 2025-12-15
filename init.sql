-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create projects table
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    utility_type TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create categories table for extensible node types
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    node_type TEXT NOT NULL,
    category_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, node_type, category_name)
);

-- Create consumer_category_settings table for icon/color customization
CREATE TABLE IF NOT EXISTS consumer_category_settings (
    id SERIAL PRIMARY KEY,
    category_name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    icon_name TEXT NOT NULL DEFAULT 'box-fill',
    color TEXT NOT NULL DEFAULT '#868e96',
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default consumer categories
INSERT INTO consumer_category_settings (category_name, display_name, icon_name, color, sort_order) VALUES
    ('Lighting', 'Lighting', 'lightbulb-fill', '#ffd43b', 1),
    ('HVAC', 'HVAC', 'snow', '#74c0fc', 2),
    ('Elevator', 'Elevator', 'arrows-expand', '#a9e34b', 3),
    ('Pumps', 'Pumps', 'gear-fill', '#63e6be', 4),
    ('Ventilation', 'Ventilation', 'fan', '#b197fc', 5),
    ('Outlets', 'Outlets', 'plug-fill', '#ffa94d', 6),
    ('Equipment', 'Equipment', 'tools', '#ff8787', 7),
    ('Other', 'Other', 'box-fill', '#868e96', 100)
ON CONFLICT (category_name) DO NOTHING;

-- Create readings table for timeseries data
CREATE TABLE IF NOT EXISTS readings (
    time TIMESTAMPTZ NOT NULL,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    node_id TEXT NOT NULL,
    value NUMERIC NOT NULL,
    unit TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert readings to hypertable
SELECT create_hypertable('readings', 'time', if_not_exists => TRUE);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_readings_project_node ON readings(project_id, node_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_categories_project ON categories(project_id, node_type);
CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);

-- Create continuous aggregate for daily readings
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_readings
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS day,
    project_id,
    node_id,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    COUNT(*) AS reading_count
FROM readings
GROUP BY day, project_id, node_id
WITH NO DATA;

-- Add refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('daily_readings',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Optional: Add retention policy (uncomment if needed)
-- SELECT add_retention_policy('readings', INTERVAL '2 years', if_not_exists => TRUE);
