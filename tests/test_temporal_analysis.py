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

    def test_zero_fill_preserves_sample_threshold_and_missing_periods(self):
        for frequency, start_frequency in [("M", "MS"), ("Q", "QS")]:
            with self.subTest(frequency=frequency):
                periods = pd.date_range("2020-01-01", periods=5, freq=start_frequency)
                jobs = pd.DataFrame([
                    {"job_id": f"{index}-{job}", "posting_date": period}
                    for index, (period, count) in enumerate(zip(periods, [2, 1, 2, 0, 2]))
                    for job in range(count)
                ])
                mentions = jobs[jobs["job_id"].isin(["0-0", "1-0", "4-0"])].assign(skill_name="Python")

                series, denominators = ta.build_demand_series(
                    mentions, jobs_df=jobs, min_jobs=2, frequency=frequency,
                )
                full = ta.expand_zero_demand_periods(series, denominators, frequency=frequency)

                self.assertEqual(full["period"].tolist(), list(periods[[0, 2, 4]]))
                self.assertEqual(full["demand_rate"].tolist(), [50.0, 0.0, 50.0])
                self.assertEqual(denominators["eligible_jobs"].tolist(), [2, 1, 2, 2])

    def test_matched_methods_average_same_calendar_with_genuine_zeros(self):
        months = pd.date_range("2020-01-01", periods=5, freq="MS")
        jobs = pd.DataFrame([
            {"job_id": f"{index}-{job}", "posting_date": month}
            for index, (month, count) in enumerate(zip(months, [2, 2, 1, 0, 2]))
            for job in range(count)
        ])
        mentions = jobs.set_index("job_id").loc[["0-0", "1-0", "2-0", "4-0"]].reset_index().assign(
            method=["lexical", "semantic", "lexical", "semantic"],
            skill_name=["Python", "Python", "Python", "Java"],
        )
        lexical, semantic = ta.matched_method_demand_series(mentions, jobs, min_jobs=2)

        for series in (lexical, semantic):
            self.assertEqual(sorted(series["period"].unique()), list(months[[0, 1, 4]]))
            self.assertEqual(len(series), 6)
        self.assertEqual(
            lexical[lexical["skill_name"].eq("Python")]["demand_rate"].tolist(), [50.0, 0.0, 0.0],
        )
        self.assertEqual(
            semantic[semantic["skill_name"].eq("Python")]["demand_rate"].tolist(), [0.0, 50.0, 0.0],
        )
        comparison, _ = ta.representation_comparison(lexical, semantic, "Lexical", "Semantic")
        self.assertAlmostEqual(comparison.set_index("skill_name").loc["Python", "Lexical"], 50 / 3)
        self.assertAlmostEqual(comparison.set_index("skill_name").loc["Python", "Semantic"], 50 / 3)
        self.assertEqual(comparison.set_index("skill_name").loc["Java", "Lexical"], 0)

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

    def test_random_forest_is_compared_on_same_periods_as_baselines_when_available(self):
        series, eligible = ta.build_demand_series(self.raw_df, jobs_df=self.jobs_df, min_jobs=1)
        full = ta.expand_zero_demand_periods(series, eligible)
        evaluation, note = ta.evaluate_forecast_baselines(full, "TypeScript", min_train=8)
        self.assertIn("MAE", evaluation.columns)
        if "Random Forest" in evaluation["model"].tolist():
            self.assertEqual(evaluation["evaluated_periods"].nunique(), 1)
            self.assertIn("same target periods", note)
            rf = evaluation.loc[evaluation["model"].eq("Random Forest")].iloc[0]
            self.assertGreaterEqual(float(rf["MAE"]), 0.0)
            self.assertGreaterEqual(float(rf["RMSE"]), 0.0)
            self.assertGreaterEqual(float(rf["directional_accuracy"]), 0.0)
            self.assertLessEqual(float(rf["directional_accuracy"]), 1.0)


if __name__ == "__main__":
    unittest.main()
