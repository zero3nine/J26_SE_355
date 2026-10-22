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
    work_mode TEXT,
    salary_disclosed INTEGER DEFAULT 0,
    salary_text_raw TEXT,
    salary_type TEXT,
    salary_min_normalized REAL,
    salary_max_normalized REAL,
    salary_currency_normalized TEXT,
    salary_period_normalized TEXT,
    salary_normalization_status TEXT,
    salary_normalization_method TEXT,
    classification_status TEXT DEFAULT 'it',
    is_benchmark_verified INTEGER DEFAULT 0,
    source_validation_status TEXT,
    role_id TEXT,
    role_name TEXT,
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
    work_mode TEXT,
    salary_disclosed INTEGER DEFAULT 0,
    salary_min_normalized REAL,
    salary_max_normalized REAL,
    salary_currency_normalized TEXT,
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

CREATE TABLE IF NOT EXISTS benchmark_jobs (
    benchmark_id TEXT PRIMARY KEY,
    source_url TEXT NOT NULL,
    source_platform TEXT,
    country TEXT,
    collection_context TEXT,
    extraction_method TEXT,
    expected_job_title_raw TEXT,
    expected_company_raw TEXT,
    expected_location_raw TEXT,
    expected_country_normalized TEXT,
    expected_city_normalized TEXT,
    expected_work_mode TEXT,
    expected_posted_date TEXT,
    expected_closing_date TEXT,
    expected_description_snippet TEXT,
    expected_description_hash TEXT,
    expected_description_min_len INTEGER,
    expected_salary_disclosed INTEGER,
    expected_salary_text_raw TEXT,
    expected_salary_type TEXT,
    expected_salary_min REAL,
    expected_salary_max REAL,
    expected_salary_currency TEXT,
    expected_salary_period TEXT,
    expected_skills TEXT,
    status_job_title TEXT,
    status_company TEXT,
    status_location TEXT,
    status_work_mode TEXT,
    status_posted_date TEXT,
    status_closing_date TEXT,
    status_description TEXT,
    status_salary TEXT,
    status_skills TEXT,
    verification_timestamp TEXT,
    verified_by TEXT,
    evidence_source TEXT,
    reviewer_notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_benchmark_jobs_country ON benchmark_jobs(country);
CREATE INDEX IF NOT EXISTS idx_benchmark_jobs_platform ON benchmark_jobs(source_platform);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    run_id TEXT PRIMARY KEY,
    is_latest INTEGER DEFAULT 0,
    timestamp TEXT NOT NULL,
    total_benchmark INTEGER,
    matched_records INTEGER,
    exact_match_rate REAL,
    macro_coverage REAL,
    macro_correctness REAL,
    is_synthetic INTEGER DEFAULT 0,
    metrics_json TEXT,
    report_markdown TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evaluation_errors (
    error_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    benchmark_id TEXT,
    field_name TEXT,
    country TEXT,
    source_platform TEXT,
    extraction_method TEXT,
    expected_raw TEXT,
    expected_normalized TEXT,
    predicted_raw TEXT,
    predicted_normalized TEXT,
    error_category TEXT,
    error_type TEXT,
    discrepancy_details TEXT,
    source_url TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES evaluation_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_eval_errors_run_id ON evaluation_errors(run_id);
CREATE INDEX IF NOT EXISTS idx_eval_errors_field ON evaluation_errors(field_name);
