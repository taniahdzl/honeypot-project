CREATE TABLE IF NOT EXISTS cowrie_events (
    id SERIAL PRIMARY KEY,
    event_time TIMESTAMPTZ,
    src_ip TEXT,
    event_type TEXT,
    username TEXT,
    password TEXT,
    command TEXT,
    raw_json JSONB,
    source_hash TEXT
);

-- Índice único parcial para deduplicación (permite NULL en datos seed)
CREATE UNIQUE INDEX IF NOT EXISTS cowrie_events_source_hash_idx
    ON cowrie_events (source_hash)
    WHERE source_hash IS NOT NULL;

-- Índices de rendimiento
CREATE INDEX IF NOT EXISTS cowrie_events_event_time_idx ON cowrie_events (event_time DESC);
CREATE INDEX IF NOT EXISTS cowrie_events_src_ip_idx     ON cowrie_events (src_ip);
CREATE INDEX IF NOT EXISTS cowrie_events_event_type_idx ON cowrie_events (event_type);

-- Datos de ejemplo para demo / presentación (volumen DB nuevo solo la primera vez)
INSERT INTO cowrie_events (event_time, src_ip, event_type, username, password, command)
VALUES
    (NOW() - INTERVAL '3 hours',   '203.0.113.44', 'cowrie.login.failed',   'root',  'password', NULL),
    (NOW() - INTERVAL '2 hours',   '203.0.113.44', 'cowrie.login.failed',   'admin', 'admin123', NULL),
    (NOW() - INTERVAL '90 minutes','198.51.100.20', 'cowrie.login.failed',   'root',  '123456',   NULL),
    (NOW() - INTERVAL '1 hour',    '198.51.100.20', 'cowrie.command.input',  'root',  NULL,       'uname -a'),
    (NOW() - INTERVAL '40 minutes','198.51.100.20', 'cowrie.command.input',  'root',  NULL,       'cat /etc/passwd'),
    (NOW() - INTERVAL '30 minutes','203.0.113.10',  'cowrie.login.failed',   'test',  'test',     NULL),
    (NOW() - INTERVAL '15 minutes','203.0.113.10',  'cowrie.session.connect', NULL,   NULL,       NULL);

-- Cliente GUI (TablePlus, etc.) en modo sólo lectura para demos sin tocar escritura API
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'honeypot_readonly') THEN
    CREATE ROLE honeypot_readonly WITH LOGIN PASSWORD 'honeypass_ro';
  END IF;
END
$$;

DO $$
BEGIN
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO honeypot_readonly', current_database());
END;
$$;

GRANT USAGE ON SCHEMA public TO honeypot_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO honeypot_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO honeypot_readonly;
