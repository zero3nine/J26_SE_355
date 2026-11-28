# Synthetic research fixtures

Use these files to exercise the extraction interface and temporal analysis. The job file contains 1,416 synthetic advertisements. The labels contain skill IDs keyed by the synthetic job IDs. Keep these inputs and outputs separate from empirical samples and the working master database.

Run from the repository root with the [research environment](../README.md#run-the-admin-portal-with-local-python) active. Semantic commands need the model locally and may download it on first use.

```powershell
python -m src.extraction.run_lexical test_data/synthetic_clean_jobs_temporal_forecast_test.csv
python -m src.extraction.run_semantic test_data/synthetic_clean_jobs_temporal_forecast_test.csv
python -m src.extraction.run_extraction test_data/synthetic_clean_jobs_temporal_forecast_test.csv tmp/synthetic_jobs_extracted.csv --semantic-threshold 0.45
python -m src.extraction.evaluation.evaluate test_data/synthetic_clean_jobs_temporal_forecast_test.csv test_data/synthetic_ground_truth.csv --semantic-threshold 0.45
```

The combined command writes the synthetic enriched CSV under `tmp/`. Omit `--persist-db` for this smoke test. You can also run `src.extraction.evaluation.calibrate` with the same two fixture paths to exercise threshold selection. Scores from these fixtures describe synthetic cases.
