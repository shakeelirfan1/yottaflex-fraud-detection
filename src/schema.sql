PRAGMA foreign_keys = ON;
-- Logical schema for normalized storage. The CSV files preserve labelled exception
-- cases for validation; load into staging tables first if enforcing FKs strictly.
CREATE TABLE IF NOT EXISTS claimant (
  claimant_id TEXT PRIMARY KEY,
  full_name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  phone TEXT NOT NULL,
  address_id TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS policy (
  policy_id TEXT PRIMARY KEY,
  claimant_id TEXT NOT NULL REFERENCES claimant(claimant_id),
  policy_type TEXT NOT NULL CHECK (policy_type IN ('auto','home','health')),
  effective_date TEXT NOT NULL,
  expiry_date TEXT NOT NULL,
  premium_amount REAL NOT NULL CHECK (premium_amount >= 0),
  status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS provider (
  provider_id TEXT PRIMARY KEY,
  provider_name TEXT NOT NULL,
  provider_type TEXT NOT NULL CHECK (provider_type IN ('repairer','medical','assessor')),
  phone TEXT NOT NULL,
  address_id TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS incident (
  incident_id TEXT PRIMARY KEY,
  incident_date TEXT NOT NULL,
  incident_type TEXT NOT NULL,
  narrative TEXT NOT NULL,
  location_id TEXT NOT NULL,
  reported_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS claim (
  claim_id TEXT PRIMARY KEY,
  claimant_id TEXT NOT NULL REFERENCES claimant(claimant_id),
  policy_id TEXT NOT NULL REFERENCES policy(policy_id),
  incident_id TEXT NOT NULL REFERENCES incident(incident_id),
  provider_id TEXT NOT NULL REFERENCES provider(provider_id),
  filed_at TEXT NOT NULL,
  claimed_amount REAL NOT NULL CHECK (claimed_amount >= 0),
  approved_amount REAL NOT NULL CHECK (approved_amount >= 0 AND approved_amount <= claimed_amount),
  status TEXT NOT NULL CHECK (status IN ('submitted','under_review','approved','rejected','paid')),
  issue_type TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS invoice (
  invoice_id TEXT PRIMARY KEY,
  invoice_number TEXT NOT NULL,
  claim_id TEXT NOT NULL REFERENCES claim(claim_id),
  provider_id TEXT NOT NULL REFERENCES provider(provider_id),
  invoice_date TEXT NOT NULL,
  invoice_amount REAL NOT NULL CHECK (invoice_amount >= 0),
  currency TEXT NOT NULL,
  status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_invoice_number ON invoice(invoice_number);
CREATE TABLE IF NOT EXISTS payment (
  payment_id TEXT PRIMARY KEY,
  claim_id TEXT NOT NULL REFERENCES claim(claim_id),
  invoice_id TEXT NOT NULL REFERENCES invoice(invoice_id),
  payment_date TEXT NOT NULL,
  payment_amount REAL NOT NULL CHECK (payment_amount >= 0),
  status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS relationship_edge (
  edge_id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL,
  source_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  relationship_type TEXT NOT NULL,
  effective_from TEXT NOT NULL,
  effective_to TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fraud_indicator (
  indicator_id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  indicator_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
  created_at TEXT NOT NULL,
  evidence TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS investigation (
  investigation_id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  opened_at TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('open','needs_review','closed')),
  assigned_to TEXT NOT NULL,
  resolution TEXT NOT NULL DEFAULT ''
);
-- Production extension: append-only claim_status_event and investigation_event tables
-- should record every transition with event_id, entity ID, from/to state, timestamp,
-- actor, reason and correlation ID. Never overwrite audit history.
