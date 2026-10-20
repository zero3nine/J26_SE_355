import json
import sqlite3

import pytest

from src.database.connection import SCHEMA_PATH
from src.roles import db_loader as L
from src.roles.distinctiveness import run_distinctiveness_analysis
from src.roles.role_skill_analysis import build_role_skill_frequency_table, classify_roles

@pytest.fixture
def conn(tmp_path):
    c = sqlite3.connect(tmp_path / "test.sqlite3")
    c.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    yield c
    c.close()

def add_job(c, job_id, title, country="LK", source="itpro", first_seen="2026-01-01T00:00:00"):
    c.execute(
        "INSERT INTO jobs (job_id, source_platform, source_url, job_title, country, job_description,"
        " content_hash, first_seen_at, last_seen_at, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (job_id, source, f"http://x/{job_id}", title, country, f"{title} role", "h",
         first_seen, first_seen, first_seen, first_seen),
    )

def add_run(c, run_id, started="2026-02-01T00:00:00"):
    c.execute("INSERT INTO extraction_runs (run_id, run_type, started_at) VALUES (?,?,?)",
              (run_id, "lexical_and_semantic", started))

def add_skill(c, job_id, run_id, method, name):
    c.execute("INSERT INTO extracted_skills (job_id, run_id, method, skill_name, created_at)"
              " VALUES (?,?,?,?,?)", (job_id, run_id, method, name, "2026-02-01T00:00:00"))

@pytest.fixture
def filled(conn):
    add_job(conn, "j1", "Python Developer", "LK", "itpro")
    add_job(conn, "j2", "DevOps Engineer", "LK", "itpro")
    add_job(conn, "j3", "Data Analyst", "SG", "other")
    add_job(conn, "j4", "QA Engineer", "LK", "itpro")           
    add_job(conn, "j5", "Late Job", "LK", "itpro", first_seen="2026-03-01T00:00:00")
    add_run(conn, "run-old", "2026-01-15T00:00:00")
    add_run(conn, "run-new", "2026-02-01T00:00:00")
    for m in ("lexical", "semantic"):
        add_skill(conn, "j1", "run-new", m, "python")
    add_skill(conn, "j1", "run-new", "lexical", "git")
    add_skill(conn, "j2", "run-new", "lexical", "docker")
    add_skill(conn, "j3", "run-new", "semantic", "sql")
    add_skill(conn, "j1", "run-old", "lexical", "java")
    conn.commit()
    return conn

def test_loads_only_postings_with_skills_by_default(filled):
    df = L.load_extracted_jobs(filled, "run-new")
    assert list(df["job_id"]) == ["j1", "j2", "j3"]

def test_skills_are_split_by_method_and_run(filled):
    df = L.load_extracted_jobs(filled, "run-new").set_index("job_id")
    assert json.loads(df.loc["j1", "lexical_skills"]) == ["git", "python"]
    assert json.loads(df.loc["j1", "semantic_skills"]) == ["python"]
    assert json.loads(df.loc["j2", "semantic_skills"]) == []
    assert "java" not in df.loc["j1", "lexical_skills"]         

def test_empty_postings_option_uses_the_time_of_the_run(filled):
    df = L.load_extracted_jobs(filled, "run-new", include_jobs_without_skills=True)
    ids = list(df["job_id"])
    assert "j4" in ids                                           
    assert "j5" not in ids                                       
    assert json.loads(df.set_index("job_id").loc["j4", "lexical_skills"]) == []

def test_country_and_source_filters(filled):
    assert list(L.load_extracted_jobs(filled, "run-new", countries=["SG"])["job_id"]) == ["j3"]
    assert list(L.load_extracted_jobs(filled, "run-new", sources=["itpro"])["job_id"]) == ["j1", "j2"]

def test_summary_runs_and_filter_values(filled):
    s = L.database_summary(filled)
    assert (s["jobs"], s["countries"], s["runs"], s["mentions"]) == (5, 2, 2, 6)
    runs = L.list_extraction_runs(filled)
    assert list(runs["run_id"]) == ["run-new", "run-old"]       
    assert L.list_filter_values(filled, "country") == ["LK", "SG"]
    with pytest.raises(ValueError):
        L.list_filter_values(filled, "job_title; DROP TABLE jobs")

def test_empty_database_does_not_crash(conn):
    assert L.database_summary(conn)["jobs"] == 0
    assert L.list_extraction_runs(conn).empty
    assert L.load_extracted_jobs(conn, "nope").empty

def test_loaded_table_flows_through_the_real_pipeline(filled):
    df = L.load_extracted_jobs(filled, "run-new")
    roles = classify_roles(df)
    freq = build_role_skill_frequency_table(roles)
    assert not freq.empty
    result = run_distinctiveness_analysis(roles, freq, n_resamples=10, top_k=3)
    assert not result["distinctiveness"].empty