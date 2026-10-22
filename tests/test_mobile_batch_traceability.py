"""Automated tests for mobile development batch traceability, import, and skill extraction."""
import json
import sqlite3
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.scraping.link_extractor import LinkExtractor
from src.cleaning.clean_jobs import clean_raw_dataframe
from src.database.connection import initialize_database
from src.database.repository import (
    import_jobs_dataframe,
    get_master_jobs,
    get_import_runs,
    record_extraction_run,
    store_extracted_skills,
    get_extracted_skills_dataset,
)
from src.extraction.run_extraction import run_extraction


SAMPLE_HTML_LISTING = """
<html>
<body>
<nav>
  <a href="/jobs/quality-assurance/">Quality Assurance</a>
  <a href="/jobs/mobile-development/">Mobile Development</a>
  <a href="/jobs/software-engineering/">Software Engineering</a>
</nav>
<main>
  <div class="job-card">
    <a href="/job/15215/android-engineer-at-softvil-technologies/">Android Engineer</a>
  </div>
  <div class="job-card">
    <a href="https://itpro.lk/job/14993/mobile-developer-react-native-at-deepsea-coders/">Mobile Developer React Native</a>
  </div>
  <div class="job-card">
    <a href="/job/15086/senior-flutter-developer-at-bistec-global-services/">Senior Flutter Developer</a>
  </div>
</main>
</body>
</html>
"""


def test_link_extractor_mobile_category_filtering():
    """Verify link extractor catches /job/ detail links and ignores /jobs/ category navigation."""
    extractor = LinkExtractor()
    links = extractor.extract_job_links("https://itpro.lk/jobs/mobile-development/", SAMPLE_HTML_LISTING)
    
    assert len(links) == 3
    assert "https://itpro.lk/job/15215/android-engineer-at-softvil-technologies/" in links
    assert "https://itpro.lk/job/14993/mobile-developer-react-native-at-deepsea-coders/" in links
    assert "https://itpro.lk/job/15086/senior-flutter-developer-at-bistec-global-services/" in links
    
    # Assert navigation categories are excluded
    for link in links:
        assert "/jobs/quality-assurance" not in link
        assert "/jobs/mobile-development" not in link


def test_mobile_raw_to_clean_pipeline():
    """Verify cleaning preserves valid mobile IT jobs and produces clean team records."""
    raw_data = [
        {
            "job_id": "itpro.lk_15215",
            "source_job_id": "15215",
            "job_title_raw": "Android Engineer",
            "company_raw": "Softvil Technologies",
            "country_raw": "Sri Lanka",
            "location_raw": "Colombo",
            "job_description_raw": "<p>We are seeking an Android Engineer with Java, OOP, Git, and REST API experience.</p>",
            "requirements_raw": "Java, Android SDK, Git",
            "posted_date_raw": "2026-10-15",
            "closing_date_raw": "2026-11-15",
            "source_platform": "itpro.lk",
            "source_hostname": "itpro.lk",
            "source_url": "https://itpro.lk/job/15215/android-engineer-at-softvil-technologies/",
            "classification_status": "it",
            "collection_batch_id": "test_mobile_batch",
            "scraped_at": "2026-10-22T10:00:00Z",
        },
        {
            "job_id": "itpro.lk_14993",
            "source_job_id": "14993",
            "job_title_raw": "Mobile Developer (React Native)",
            "company_raw": "DeepSea Coders",
            "country_raw": "Sri Lanka",
            "location_raw": "Remote",
            "job_description_raw": "<p>Building mobile applications with React, TypeScript, JavaScript, and Node.js.</p>",
            "requirements_raw": "React Native, TypeScript",
            "posted_date_raw": "2026-10-16",
            "closing_date_raw": "2026-11-16",
            "source_platform": "itpro.lk",
            "source_hostname": "itpro.lk",
            "source_url": "https://itpro.lk/job/14993/mobile-developer-react-native-at-deepsea-coders/",
            "classification_status": "it",
            "collection_batch_id": "test_mobile_batch",
            "scraped_at": "2026-10-22T10:00:00Z",
        },
        {
            "job_id": "itpro.lk_99999",
            "source_job_id": "99999",
            "job_title_raw": "Tea Factory Packing Assistant",
            "company_raw": "Tea Co",
            "country_raw": "Sri Lanka",
            "location_raw": "Kandy",
            "job_description_raw": "<p>Packing tea bags into export boxes. Manual labor only.</p>",
            "requirements_raw": "None",
            "posted_date_raw": "2026-10-16",
            "closing_date_raw": "2026-11-16",
            "source_platform": "itpro.lk",
            "source_hostname": "itpro.lk",
            "source_url": "https://itpro.lk/job/99999/tea-packer/",
            "classification_status": "non_it",
            "collection_batch_id": "test_mobile_batch",
            "scraped_at": "2026-10-22T10:00:00Z",
        },
    ]
    raw_df = pd.DataFrame(raw_data)
    df_internal, df_team, stats = clean_raw_dataframe(raw_df)

    assert len(df_internal) == 3
    assert len(df_team) == 2
    assert "itpro.lk_15215" in df_team["job_id"].values
    assert "itpro.lk_14993" in df_team["job_id"].values
    assert "itpro.lk_99999" not in df_team["job_id"].values
    assert stats["filtered_non_it"] == 1


def test_master_db_import_idempotence_and_traceability():
    """Verify database import records batch run ID and avoids duplicates on re-import."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_master.sqlite3"
        initialize_database(db_path=db_path)

        clean_records = [
            {
                "job_id": "itpro.lk_15215",
                "job_title_raw": "Android Engineer",
                "company": "Softvil Technologies",
                "country": "Sri Lanka",
                "location": "Colombo",
                "job_description": "We are seeking an Android Engineer with Java, OOP, Git, and REST API experience.",
                "requirements": "Java, Git",
                "posted_date": "2026-10-15",
                "closing_date": "2026-11-15",
                "source_platform": "itpro.lk",
                "source_url": "https://itpro.lk/job/15215/android-engineer-at-softvil-technologies/",
            },
            {
                "job_id": "itpro.lk_14993",
                "job_title_raw": "Mobile Developer (React Native)",
                "company": "DeepSea Coders",
                "country": "Sri Lanka",
                "location": "Remote",
                "job_description": "Building mobile applications with React, TypeScript, JavaScript, and Node.js.",
                "requirements": "React Native, TypeScript",
                "posted_date": "2026-10-16",
                "closing_date": "2026-11-16",
                "source_platform": "itpro.lk",
                "source_url": "https://itpro.lk/job/14993/mobile-developer-react-native-at-deepsea-coders/",
            },
        ]
        clean_df = pd.DataFrame(clean_records)

        # Initial import
        res1 = import_jobs_dataframe(clean_df, source_name="Batch batch_mobile_test", db_path=db_path, batch_id="batch_mobile_test")
        assert res1["inserted_jobs"] == 2
        assert res1["skipped_duplicates"] == 0
        run_id_1 = res1["import_run_id"]
        assert run_id_1 is not None

        # Re-import identical dataframe (idempotent duplicate detection)
        res2 = import_jobs_dataframe(clean_df, source_name="Batch batch_mobile_test", db_path=db_path, batch_id="batch_mobile_test")
        assert res2["inserted_jobs"] == 0
        assert res2["skipped_duplicates"] == 2

        # Verify get_master_jobs includes import_run_id
        master_jobs = get_master_jobs(db_path=db_path)
        assert len(master_jobs) == 2
        assert "import_run_id" in master_jobs.columns
        assert set(master_jobs["import_run_id"]) == {run_id_1}

        # Verify filter by import_run_id
        filtered_batch = get_master_jobs(db_path=db_path, import_run_id=run_id_1)
        assert len(filtered_batch) == 2

        runs_df = get_import_runs(db_path=db_path)
        assert len(runs_df) == 2
        assert run_id_1 in runs_df["import_run_id"].values


def test_skill_extraction_correct_association_and_provenance():
    """Verify that skills extracted are strictly associated with the originating job."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_master.sqlite3"
        initialize_database(db_path=db_path)

        jobs_data = [
            {
                "job_id": "job_android",
                "job_title_raw": "Android Engineer",
                "company": "Softvil",
                "country": "Sri Lanka",
                "location": "Colombo",
                "job_description": "Strong background in Java, Object-Oriented Programming, Git, and REST API.",
                "requirements": "",
                "posted_date": "2026-10-15",
                "closing_date": "",
                "source_platform": "itpro.lk",
                "source_url": "https://itpro.lk/job/job_android",
            },
            {
                "job_id": "job_react_native",
                "job_title_raw": "Mobile Developer React Native",
                "company": "DeepSea",
                "country": "Sri Lanka",
                "location": "Remote",
                "job_description": "Requires React, TypeScript, JavaScript, and Node.js backend integration.",
                "requirements": "",
                "posted_date": "2026-10-15",
                "closing_date": "",
                "source_platform": "itpro.lk",
                "source_url": "https://itpro.lk/job/job_react_native",
            },
        ]
        df = pd.DataFrame(jobs_data)
        import_jobs_dataframe(df, db_path=db_path)

        # Run extraction
        taxonomy_path = Path(__file__).resolve().parents[1] / "config" / "skill_taxonomy.json"
        extracted = run_extraction(
            input_df=df,
            taxonomy_path=taxonomy_path,
            semantic_threshold=0.58,
        )

        run_id = record_extraction_run(
            run_type="lexical_and_semantic",
            model_name="SBERT",
            semantic_threshold=0.58,
            source_batch_id="test_batch",
            db_path=db_path,
        )

        store_extracted_skills(extracted, run_id=run_id, method="lexical", skills_column="lexical_skills", db_path=db_path)
        store_extracted_skills(extracted, run_id=run_id, method="semantic", skills_column="semantic_skills", db_path=db_path)

        # Query integrated dataset
        dataset = get_extracted_skills_dataset(run_id=run_id, db_path=db_path)
        assert len(dataset) == 2

        android_row = dataset[dataset["job_id"] == "job_android"].iloc[0]
        react_row = dataset[dataset["job_id"] == "job_react_native"].iloc[0]

        android_lex = json.loads(android_row["lexical_skills"])
        react_lex = json.loads(react_row["lexical_skills"])

        # Java and OOP must belong to Android, NOT to React Native
        assert "Java" in android_lex
        assert "Java" not in react_lex

        # React and TypeScript must belong to React Native, NOT to Android
        assert "React" in react_lex
        assert "TypeScript" in react_lex
        assert "React" not in android_lex
        assert "TypeScript" not in android_lex
