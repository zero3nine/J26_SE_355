"""Small regression tests for temporal demand calculations and forecasting."""
import importlib.util
from pathlib import Path
import unittest

import pandas as pd

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "analytics" / "temporal_analysis.py"
spec = importlib.util.spec_from_file_location("temporal_analysis", MODULE_PATH)
ta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ta)


class TemporalAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.jobs = []
        self.mentions = []
        for month_index, period in enumerate(pd.date_range("2020-01-01", periods=30, freq="MS")):
            for j in range(10):
                job_id = f"{month_index:02d}-{j:02d}"
                self.jobs.append({
                    "job_id": job_id, "posting_date": period + pd.Timedelta(days=j),
                    "country": "Sri Lanka", "source_platform": "TopJobs",
                    "job_title": "Software Engineer", "source_url": "",
                })
                # Gradually increasing mention rate; remaining jobs are still
                # included in the denominator.
                if j < min(9, 1 + month_index // 4):
                    self.mentions.append({
                        "job_id": job_id, "posting_date": period + pd.Timedelta(days=j),
                        "country": "Sri Lanka", "source_platform": "TopJobs",
                        "job_title": "Software Engineer", "skill_name": "TypeScript",
                        "method": "lexical",
                    })
        self.jobs_df = pd.DataFrame(self.jobs)
        self.raw_df = pd.DataFrame(self.mentions)

    def test_denominator_includes_jobs_without_skill_mentions(self):
        series, eligible = ta.build_demand_series(self.raw_df, jobs_df=self.jobs_df, min_jobs=1)
        self.assertEqual(int(eligible.iloc[0]["eligible_jobs"]), 10)
        self.assertAlmostEqual(float(series.iloc[0]["demand_rate"]), 10.0)

    def test_period_series_is_monthly_and_complete(self):
        series, eligible = ta.build_demand_series(self.raw_df, jobs_df=self.jobs_df, min_jobs=1)
        full = ta.expand_zero_demand_periods(series, eligible)
        self.assertEqual(full["period"].nunique(), 30)
        self.assertEqual(len(full), 30)

    def test_forecast_has_requested_horizon_and_bounded_rates(self):
        series, eligible = ta.build_demand_series(self.raw_df, jobs_df=self.jobs_df, min_jobs=1)
        full = ta.expand_zero_demand_periods(series, eligible)
        forecast, _ = ta.forecast_skill(full, "TypeScript", horizon=3, min_periods=8)
        self.assertEqual(len(forecast), 3)
        numeric = forecast.select_dtypes(include="number")
        self.assertTrue(((numeric >= 0) & (numeric <= 100)).all().all())

    def test_rolling_origin_evaluation_returns_metrics(self):
        series, eligible = ta.build_demand_series(self.raw_df, jobs_df=self.jobs_df, min_jobs=1)
        full = ta.expand_zero_demand_periods(series, eligible)
        evaluation, _ = ta.evaluate_forecast_baselines(full, "TypeScript", min_train=8)
        self.assertIn("MAE", evaluation.columns)
        self.assertIn("RMSE", evaluation.columns)
        self.assertTrue((evaluation["evaluated_periods"] > 0).all())


if __name__ == "__main__":
    unittest.main()
