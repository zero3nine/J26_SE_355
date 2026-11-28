# Lexical and semantic skill extraction

Both methods use title, description, and requirements from the cleaned jobs and share the vocabulary in `config/skill_taxonomy.json`. Lexical extraction matches taxonomy aliases. Semantic extraction scores candidate text against taxonomy skill descriptions using Sentence Transformers.

Run the commands from the repository root after following the [local setup guide](../../README.md#run-the-admin-portal-with-local-python). Replace the example paths with the cleaned jobs and matching human annotations for your run.

The standalone lexical command works with `requirements-admin.txt`. Semantic and combined extraction, calibration, and evaluation require `requirements-extraction.txt` as well. The full `requirements.txt` installs both. For Docker, see [Enable semantic extraction in Docker](../../README.md#enable-semantic-extraction-in-docker).

```powershell
python -m src.extraction.run_lexical data/processed/jobs_clean.csv
python -m src.extraction.run_semantic data/processed/jobs_clean.csv
python -m src.extraction.run_extraction data/processed/jobs_clean.csv data/processed/jobs_extracted.csv --semantic-threshold 0.45
```

The first two commands print per-job predictions. The combined command writes an enriched CSV with `lexical_skills` and `semantic_skills`. It writes to SQLite only if you pass `--persist-db`. In Streamlit, publish cleaned jobs to **Master Dataset**, run extraction from **Master database**, then click **Save lexical and semantic results** to link mentions to the master jobs.

Use annotated calibration data to choose a semantic threshold. To estimate accuracy, evaluate the chosen threshold on a separate annotated sample using the same `job_id` values as its input CSV.

```powershell
python -m src.extraction.evaluation.calibrate calibration_jobs.csv calibration_labels.csv
python -m src.extraction.evaluation.evaluate heldout_jobs.csv heldout_labels.csv --semantic-threshold 0.45
```

Set the evaluation flag to the chosen value. The standalone semantic CLI defaults to 0.50, while the combined CLI defaults to 0.45. Record the threshold, model, taxonomy, and input cohort with the results. Use the [synthetic fixtures](../../test_data/README.md) for smoke tests and the [extraction follow-ups](TODO.md) for implementation gaps.
