-- Reference schema. Runtime uses SQLAlchemy create_all.
-- PostgreSQL production; SQLite is a development fallback.

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login TIMESTAMPTZ,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ
);

CREATE TABLE domains (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    hostname VARCHAR(255),
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    catch_all_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    catch_all_destination VARCHAR(320),
    dkim_selector VARCHAR(64) NOT NULL DEFAULT 'mail',
    dmarc_policy VARCHAR(16) NOT NULL DEFAULT 'none',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE aliases (
    id SERIAL PRIMARY KEY,
    domain_id INTEGER NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    local_part VARCHAR(64) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (domain_id, local_part)
);

CREATE TABLE destinations (
    id SERIAL PRIMARY KEY,
    alias_id INTEGER NOT NULL REFERENCES aliases(id) ON DELETE CASCADE,
    email VARCHAR(320) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (alias_id, email)
);

CREATE TABLE mail_events (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_type VARCHAR(32) NOT NULL,
    queue_id VARCHAR(32),
    message_id VARCHAR(255),
    sender VARCHAR(320),
    recipient VARCHAR(320),
    destination VARCHAR(320),
    size INTEGER,
    status VARCHAR(32),
    response TEXT,
    spam_score VARCHAR(32),
    extra TEXT
);

CREATE TABLE mail_queue (
    id SERIAL PRIMARY KEY,
    queue_id VARCHAR(32) UNIQUE NOT NULL,
    sender VARCHAR(320),
    recipient VARCHAR(320),
    status VARCHAR(32) NOT NULL DEFAULT 'deferred',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    attempts INTEGER NOT NULL DEFAULT 0,
    next_retry TIMESTAMPTZ,
    size INTEGER,
    reason TEXT
);

CREATE TABLE dns_checks (
    id SERIAL PRIMARY KEY,
    domain_id INTEGER NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    check_type VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL,
    expected TEXT,
    actual TEXT,
    message TEXT,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(64) NOT NULL,
    target VARCHAR(255),
    ip VARCHAR(64),
    user_agent VARCHAR(255),
    details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE api_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(64) NOT NULL,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used TIMESTAMPTZ,
    expires_at TIMESTAMPTZ
);

CREATE TABLE system_settings (
    key VARCHAR(64) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
