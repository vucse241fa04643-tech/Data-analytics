-- =====================================================================
-- Agent 63 – Application Authentication Credential Storage
-- Phase: Controlled Application Authentication Schema Addition
--
-- Security classification: HIGHLY_SENSITIVE / HARD DENY.
-- Excluded from Schema Registry analytics allowlists.
-- Stores salted password hashes and cryptographic parameters.
-- =====================================================================

CREATE TABLE IF NOT EXISTS identity.auth_credential (
    user_id UUID PRIMARY KEY REFERENCES identity.app_user(user_id) ON DELETE CASCADE,
    password_hash TEXT NOT NULL,
    algorithm VARCHAR(32) NOT NULL DEFAULT 'argon2id',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_auth_credential_user_id ON identity.auth_credential(user_id);
