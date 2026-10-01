PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    source_platform TEXT,
    source_hostname TEXT,
    source_url TEXT NOT NULL,
    job_title TEXT,
    company_name TEXT,
    location TEXT,
    country TEXT,
    posting_date TEXT,
    job_description TEXT,
    content_hash TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source_url)
);

CREATE INDEX IF NOT EXISTS idx_jobs_country ON jobs(country);
CREATE INDEX IF NOT EXISTS idx_jobs_posting_date ON jobs(posting_date);
CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(job_title);

CREATE TABLE IF NOT EXISTS job_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    job_title TEXT,
    company_name TEXT,
    location TEXT,
    country TEXT,
    posting_date TEXT,
    job_description TEXT,
    observed_at TEXT NOT NULL,
    import_run_id TEXT,
    FOREIGN KEY(job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
    UNIQUE(job_id, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_job_versions_job_id
    ON job_versions(job_id);

CREATE TABLE IF NOT EXISTS import_runs (
    import_run_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    input_rows INTEGER NOT NULL DEFAULT 0,
    inserted_jobs INTEGER NOT NULL DEFAULT 0,
    updated_jobs INTEGER NOT NULL DEFAULT 0,
    skipped_duplicates INTEGER NOT NULL DEFAULT 0,
    failed_rows INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running',
    notes TEXT
);

CREATE TABLE IF NOT EXISTS extraction_runs (
    run_id TEXT PRIMARY KEY,
    run_type TEXT NOT NULL,
    model_name TEXT,
    model_version TEXT,
    taxonomy_version TEXT,
    semantic_threshold REAL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    source_batch_id TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS skills (
    skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name TEXT NOT NULL UNIQUE,
    category TEXT,
    taxonomy_version TEXT,
    aliases_json TEXT
);

CREATE TABLE IF NOT EXISTS extracted_skills (
    mention_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    method TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    canonical_skill_id INTEGER,
    original_span TEXT,
    confidence REAL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
    FOREIGN KEY(run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
    FOREIGN KEY(canonical_skill_id) REFERENCES skills(skill_id),
    UNIQUE(job_id, run_id, method, skill_name)
);

CREATE INDEX IF NOT EXISTS idx_extracted_skills_job_id
    ON extracted_skills(job_id);
CREATE INDEX IF NOT EXISTS idx_extracted_skills_run_id
    ON extracted_skills(run_id);
CREATE INDEX IF NOT EXISTS idx_extracted_skills_method
    ON extracted_skills(method);
