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

    def test_mixed_posting_dates_share_one_eligible_population(self):
        jobs = pd.DataFrame({
            "job_id": ["first", "second", "third", "invalid"],
            "posting_date": ["2026-01-03", "2026-01-04T12:00:00+05:30", "2026-01-05T13:00:00+05:30", "invalid"],
        })
        mentions = pd.DataFrame({
            "job_id": ["second", "third", "outside", "invalid"],
            "posting_date": ["2026-01-04T12:00:00+05:30", "2026-01-05T13:00:00+05:30", "2026-01-06T12:00:00+05:30", "2026-01-07"],
            "skill_name": "Python",
        })
        for frequency in ("M", "Q"):
            for job_rows in (jobs, jobs.iloc[::-1]):
                with self.subTest(frequency=frequency, first_job=job_rows.iloc[0]["job_id"]):
                    series, eligible = ta.build_demand_series(mentions, jobs_df=job_rows, frequency=frequency)
                    self.assertEqual(eligible["eligible_jobs"].tolist(), [3])
                    self.assertEqual(series["jobs_mentioning_skill"].tolist(), [2])
                    self.assertAlmostEqual(series.iloc[0]["demand_rate"], 200 / 3)

    def test_eligible_periods_are_available_without_mentions(self):
        series, eligible = ta.build_demand_series(self.raw_df.iloc[:0], jobs_df=self.jobs_df)
        self.assertTrue(series.empty)
        self.assertIn("period", series.columns)
        self.assertEqual(len(eligible), 30)

    def test_mention_does_not_spread_to_an_unmentioned_period(self):
        jobs = pd.DataFrame({"job_id": ["same", "same"], "posting_date": ["2026-01-03", "2026-02-01"]})
        mentions = jobs.iloc[:1].assign(skill_name="Python")
        series, eligible = ta.build_demand_series(mentions, jobs_df=jobs)
        full = ta.expand_zero_demand_periods(series, eligible)
        self.assertEqual(full["demand_rate"].tolist(), [100.0, 0.0])

    def test_period_series_is_monthly_and_complete(self):
        series, eligible = ta.build_demand_series(self.raw_df, jobs_df=self.jobs_df, min_jobs=1)
        full = ta.expand_zero_demand_periods(series, eligible)
        self.assertEqual(full["period"].nunique(), 30)
        self.assertEqual(len(full), 30)

    def test_trailing_observed_zero_demand_precedes_forecast(self):
        for frequency, start_frequency in [("M", "MS"), ("Q", "QS")]:
            with self.subTest(frequency=frequency):
                periods = pd.date_range("2020-01-01", periods=13, freq=start_frequency)
                jobs = pd.DataFrame({"job_id": list(range(12)), "posting_date": periods[:-1]})
                mentions = jobs.iloc[:8].assign(skill_name="Python")
                series, eligible = ta.build_demand_series(mentions, jobs_df=jobs, frequency=frequency)
                full = ta.expand_zero_demand_periods(series, eligible, frequency=frequency)

                self.assertEqual(full["period"].tolist(), periods[:-1].tolist())
                self.assertEqual(full["demand_rate"].tolist(), [100.0] * 8 + [0.0] * 4)
                forecast, _ = ta.forecast_skill(full, "Python", horizon=1, frequency=frequency)
                self.assertEqual(forecast["period"].tolist(), [periods[-1]])

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

    def test_method_overlap_excludes_zero_demand_skills(self):
        lexical = pd.DataFrame({"skill_name": ["Python", "JavaScript"], "demand_rate": [20.0, 0.0]})
        semantic = lexical.assign(demand_rate=[0.0, 20.0])
        _, stats = ta.representation_comparison(lexical, semantic, "Lexical", "Semantic")
        self.assertEqual(stats["top_k_overlap"], 0.0)
        self.assertEqual(stats["top_k_union_count"], 2)

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

    def test_forecast_suppressed_if_latest_observed_period_is_below_threshold(self):
        jobs = self.jobs_df.iloc[:-9]
        series, eligible = ta.build_demand_series(self.raw_df, jobs_df=jobs, min_jobs=5)
        full = ta.expand_zero_demand_periods(series, eligible)
        forecast, note = ta.forecast_skill(
            full, "TypeScript", latest_observed_period=eligible["period"].max(),
        )
        self.assertTrue(forecast.empty)
        self.assertIn("latest observed period", note)

    def test_horizon_validation_uses_only_contiguous_history(self):
        months = pd.date_range("2020-01-01", periods=15, freq="MS")
        series = pd.DataFrame({"period": months, "skill_name": "Python", "demand_rate": range(15)})
        with_gap = series.drop(index=4)

        one_step, _ = ta.evaluate_forecast_baselines(with_gap, "Python", horizon=1)
        self.assertEqual(set(one_step["evaluated_periods"]), {2})
        three_steps, _ = ta.evaluate_forecast_baselines(with_gap, "Python", horizon=3)
        forecast, note = ta.forecast_skill(with_gap, "Python", horizon=3)
        self.assertTrue(three_steps.empty)
        self.assertTrue(forecast.empty)
        self.assertIn("consecutive", note)

    def test_backtests_each_displayed_horizon_against_same_forecast_method(self):
        series = pd.DataFrame({
            "period": pd.date_range("2020-01-01", periods=14, freq="MS"),
            "skill_name": "Python", "demand_rate": range(14),
        })
        scores, _ = ta.evaluate_forecast_baselines(series, "Python", horizon=3)
        self.assertEqual(scores["horizon"].unique().tolist(), [1, 2, 3])
        self.assertEqual(set(scores["evaluated_periods"]), {4})
        last_value = scores.loc[scores["model"].eq("Last-value baseline")]
        self.assertEqual(last_value["MAE"].tolist(), [1.0, 2.0, 3.0])
        linear = scores.loc[scores["model"].eq("Linear-trend baseline")]
        self.assertTrue((linear["MAE"] < 1e-10).all())

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
