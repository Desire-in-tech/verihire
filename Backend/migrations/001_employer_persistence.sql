-- Employer-scoped persistence for VeriHire.
-- Safe to run more than once. Credentials stay in the provider environment.
-- This file contains no secret values.

CREATE TABLE IF NOT EXISTS employers (
  employer_id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  employer_id TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  FOREIGN KEY (employer_id) REFERENCES employers (employer_id)
);

CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  employer_id TEXT NOT NULL,
  title TEXT NOT NULL,
  company TEXT NOT NULL,
  description TEXT NOT NULL,
  criteria_json TEXT NOT NULL,
  verification_status TEXT NOT NULL,
  is_active INTEGER NOT NULL,
  FOREIGN KEY (employer_id) REFERENCES employers (employer_id)
);

CREATE TABLE IF NOT EXISTS cv_uploads (
  upload_id TEXT PRIMARY KEY,
  employer_id TEXT NOT NULL,
  job_id TEXT NOT NULL,
  cv_source TEXT NOT NULL,
  extracted_text TEXT NOT NULL,
  extracted_data_json TEXT NOT NULL,
  matching_results_json TEXT NOT NULL,
  proof_results_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (employer_id) REFERENCES employers (employer_id),
  FOREIGN KEY (job_id) REFERENCES jobs (job_id)
);

CREATE INDEX IF NOT EXISTS sessions_employer_idx ON sessions (employer_id);
CREATE INDEX IF NOT EXISTS jobs_employer_idx ON jobs (employer_id);
CREATE INDEX IF NOT EXISTS cv_uploads_employer_idx ON cv_uploads (employer_id);
