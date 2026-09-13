"""
Statistical Metrics Aggregator for Information Extraction Benchmark.
Academic Research Component for Regional Comparative IT Labor-Market Analysis.

Features:
- Separate metrics for Extraction Coverage (Completeness) vs. Extraction Correctness (Accuracy).
- Exact agreement rate vs. Normalized agreement rate.
- Numeric error metrics: Mean Absolute Error (MAE), Median AE with compatibility exclusion tracking.
- Multi-label evaluation for canonical skills: micro-averaged, macro-averaged, and per-label support.
- Wilson score 95% confidence intervals for proportions.
- Multidimensional stratification by Country, Platform, and Extraction Method with sample sizes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple

from src.evaluation.comparator import RecordEvaluationResult, FieldEvaluationResult


def wilson_score_interval(successes: int, trials: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Calculates Wilson score confidence interval for a binomial proportion.
    
    Robust for small sample sizes and extreme probabilities (0 or 1).
    """
    if trials <= 0:
        return 0.0, 0.0

    # z-value for 95% confidence is ~1.95996
    z = 1.959963984540054
    p_hat = successes / trials
    denominator = 1.0 + (z ** 2) / trials
    centre_adjusted_probability = p_hat + (z ** 2) / (2.0 * trials)
    adjusted_std_dev = math.sqrt((p_hat * (1.0 - p_hat) + (z ** 2) / (4.0 * trials)) / trials)

    lower_bound = (centre_adjusted_probability - z * adjusted_std_dev) / denominator
    upper_bound = (centre_adjusted_probability + z * adjusted_std_dev) / denominator

    return round(max(0.0, lower_bound), 4), round(min(1.0, upper_bound), 4)


@dataclass
class FieldMetricSummary:
    """Detailed statistical summary for a single field across evaluated records."""
    field_name: str
    eligible_references: int = 0      # Verified reference count
    matched_predictions: int = 0      # Predictions present (extracted)
    correct_values: int = 0           # True Positives
    incorrect_values: int = 0         # False Positives (content error)
    missing_predictions: int = 0      # False Negatives (omission)
    exact_matches: int = 0            # Exact raw string matches

    exact_agreement_rate: float = 0.0       # Exact / Eligible
    normalized_agreement_rate: float = 0.0  # Correct / Eligible (Unconditional Recall)
    extraction_coverage: float = 0.0        # Matched Predictions / Eligible (Completeness)
    extraction_correctness: float = 0.0     # Correct / Matched Predictions (Precision)
    precision: float = 0.0                  # Correct / (Correct + Incorrect)
    recall: float = 0.0                     # Correct / Eligible
    f1_score: float = 0.0                   # Harmonic mean of precision and recall

    wilson_ci_lower: float = 0.0
    wilson_ci_upper: float = 0.0

    # Unavailable field discipline (Negative Predictive Value)
    unavailable_references: int = 0
    correct_absence: int = 0                # True Negatives
    over_extracted: int = 0                 # Hallucinations on unavailable fields
    hallucination_rate: float = 0.0

    ambiguous_references: int = 0
    not_reviewed_references: int = 0

    @property
    def verified_total(self) -> int:
        return self.eligible_references

    @verified_total.setter
    def verified_total(self, value: int):
        self.eligible_references = value

    @property
    def ambiguous_total(self) -> int:
        return self.ambiguous_references

    @ambiguous_total.setter
    def ambiguous_total(self, value: int):
        self.ambiguous_references = value

    @property
    def unavailable_total(self) -> int:
        return self.unavailable_references

    @unavailable_total.setter
    def unavailable_total(self, value: int):
        self.unavailable_references = value

    # Numeric salary metrics (only for salary_min, salary_max)
    is_numeric: bool = False
    comparable_count: int = 0
    excluded_unavailable_count: int = 0
    excluded_incompatible_count: int = 0
    mae: Optional[float] = None
    median_ae: Optional[float] = None

    def compute_statistics(self, numeric_errors: Optional[List[float]] = None):
        """Calculates derived rates, confidence intervals, and numeric errors."""
        # 1. Exact & Normalized Agreement Rates
        if self.eligible_references > 0:
            self.exact_agreement_rate = round(self.exact_matches / self.eligible_references, 4)
            self.normalized_agreement_rate = round(self.correct_values / self.eligible_references, 4)
            self.extraction_coverage = round(self.matched_predictions / self.eligible_references, 4)
            self.recall = self.normalized_agreement_rate

            # 95% Wilson Confidence Interval on normalized agreement
            lo, hi = wilson_score_interval(self.correct_values, self.eligible_references)
            self.wilson_ci_lower = lo
            self.wilson_ci_upper = hi
        else:
            self.exact_agreement_rate = 0.0
            self.normalized_agreement_rate = 0.0
            self.extraction_coverage = 0.0
            self.recall = 0.0
            self.wilson_ci_lower = 0.0
            self.wilson_ci_upper = 0.0

        # 2. Extraction Correctness & Precision
        if self.matched_predictions > 0:
            self.extraction_correctness = round(self.correct_values / self.matched_predictions, 4)
        else:
            self.extraction_correctness = 0.0

        extracted_eval = self.correct_values + self.incorrect_values
        if extracted_eval > 0:
            self.precision = round(self.correct_values / extracted_eval, 4)
        else:
            self.precision = 0.0

        # 3. F1-Score
        if (self.precision + self.recall) > 0:
            self.f1_score = round(2 * (self.precision * self.recall) / (self.precision + self.recall), 4)
        else:
            self.f1_score = 0.0

        # 4. Hallucination Rate
        if self.unavailable_references > 0:
            self.hallucination_rate = round(self.over_extracted / self.unavailable_references, 4)
        else:
            self.hallucination_rate = 0.0

        # 5. Numeric Errors (MAE and Median AE)
        if numeric_errors:
            self.comparable_count = len(numeric_errors)
            self.mae = round(sum(numeric_errors) / len(numeric_errors), 2)
            sorted_err = sorted(numeric_errors)
            mid = len(sorted_err) // 2
            if len(sorted_err) % 2 == 0:
                self.median_ae = round((sorted_err[mid - 1] + sorted_err[mid]) / 2.0, 2)
            else:
                self.median_ae = round(sorted_err[mid], 2)


@dataclass
class MultiLabelSkillMetrics:
    """Metrics for canonical multi-label skill extraction."""
    total_evaluated_ads: int = 0
    ads_with_verified_skills: int = 0
    micro_precision: float = 0.0
    micro_recall: float = 0.0
    micro_f1: float = 0.0
    macro_precision: float = 0.0
    macro_recall: float = 0.0
    macro_f1: float = 0.0
    per_label_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class StratifiedMetricGroup:
    """Evaluation summary stratified across a dimension (Country, Platform, Method)."""
    group_name: str
    dimension: str
    total_records: int = 0
    fully_correct_records: int = 0
    exact_match_rate: float = 0.0
    wilson_ci_lower: float = 0.0
    wilson_ci_upper: float = 0.0
    is_small_sample: bool = False
    field_metrics: Dict[str, FieldMetricSummary] = field(default_factory=dict)

    def compute_rates(self):
        if self.total_records > 0:
            self.exact_match_rate = round(self.fully_correct_records / self.total_records, 4)
            self.wilson_ci_lower, self.wilson_ci_upper = wilson_score_interval(
                self.fully_correct_records, self.total_records
            )
            self.is_small_sample = self.total_records < 10
        else:
            self.exact_match_rate = 0.0
            self.wilson_ci_lower = 0.0
            self.wilson_ci_upper = 0.0
            self.is_small_sample = True


@dataclass
class GlobalEvaluationMetrics:
    """Global evaluation metrics object encapsulating field and stratified summaries."""
    timestamp: str
    total_benchmark_records: int
    total_predictions_loaded: int
    matched_records_count: int
    unmatched_benchmark_count: int
    extra_predictions_count: int

    fully_correct_records: int = 0
    exact_match_rate: float = 0.0
    exact_match_ci_lower: float = 0.0
    exact_match_ci_upper: float = 0.0

    macro_coverage: float = 0.0
    macro_correctness: float = 0.0
    macro_precision: float = 0.0
    macro_recall: float = 0.0
    macro_f1: float = 0.0

    field_metrics: Dict[str, FieldMetricSummary] = field(default_factory=dict)
    skill_metrics: Optional[MultiLabelSkillMetrics] = None
    by_country: Dict[str, StratifiedMetricGroup] = field(default_factory=dict)
    by_platform: Dict[str, StratifiedMetricGroup] = field(default_factory=dict)
    by_method: Dict[str, StratifiedMetricGroup] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes structure to dictionary for machine-readable JSON output."""
        return {
            "metadata": {
                "timestamp": self.timestamp,
                "unit_of_analysis": "Individual Job Advertisement (Record-level cluster)",
                "total_benchmark_records": self.total_benchmark_records,
                "total_predictions_loaded": self.total_predictions_loaded,
                "matched_records_count": self.matched_records_count,
                "unmatched_benchmark_count": self.unmatched_benchmark_count,
                "extra_predictions_count": self.extra_predictions_count,
                "fully_correct_records": self.fully_correct_records,
                "exact_match_rate": self.exact_match_rate,
                "exact_match_95_ci": [self.exact_match_ci_lower, self.exact_match_ci_upper],
                "macro_coverage": self.macro_coverage,
                "macro_correctness": self.macro_correctness,
                "macro_precision": self.macro_precision,
                "macro_recall": self.macro_recall,
                "macro_f1": self.macro_f1,
            },
            "field_metrics": {k: asdict(v) for k, v in self.field_metrics.items()},
            "skill_metrics": asdict(self.skill_metrics) if self.skill_metrics else None,
            "by_country": {
                k: {
                    "group_name": v.group_name,
                    "total_records": v.total_records,
                    "fully_correct_records": v.fully_correct_records,
                    "exact_match_rate": v.exact_match_rate,
                    "exact_match_95_ci": [v.wilson_ci_lower, v.wilson_ci_upper],
                    "is_small_sample": v.is_small_sample,
                    "field_metrics": {fk: asdict(fv) for fk, fv in v.field_metrics.items()}
                }
                for k, v in self.by_country.items()
            },
            "by_platform": {
                k: {
                    "group_name": v.group_name,
                    "total_records": v.total_records,
                    "fully_correct_records": v.fully_correct_records,
                    "exact_match_rate": v.exact_match_rate,
                    "exact_match_95_ci": [v.wilson_ci_lower, v.wilson_ci_upper],
                    "is_small_sample": v.is_small_sample,
                }
                for k, v in self.by_platform.items()
            },
            "by_method": {
                k: {
                    "group_name": v.group_name,
                    "total_records": v.total_records,
                    "fully_correct_records": v.fully_correct_records,
                    "exact_match_rate": v.exact_match_rate,
                    "exact_match_95_ci": [v.wilson_ci_lower, v.wilson_ci_upper],
                    "is_small_sample": v.is_small_sample,
                }
                for k, v in self.by_method.items()
            }
        }


def _compute_multi_label_skill_metrics(records: List[RecordEvaluationResult]) -> MultiLabelSkillMetrics:
    """Computes micro- and macro-averaged metrics for multi-label skill extraction."""
    total_tp = 0
    total_fp = 0
    total_fn = 0
    ads_with_skills = 0

    per_label_tp: Dict[str, int] = {}
    per_label_fp: Dict[str, int] = {}
    per_label_fn: Dict[str, int] = {}
    per_label_support: Dict[str, int] = {}

    for rec in records:
        fres = rec.field_results.get("skills")
        if not fres or fres.reference_status != "verified":
            continue

        ads_with_skills += 1
        exp_set = fres.expected_normalized if isinstance(fres.expected_normalized, set) else set()
        pred_set = fres.predicted_normalized if isinstance(fres.predicted_normalized, set) else set()

        tp_set = exp_set & pred_set
        fp_set = pred_set - exp_set
        fn_set = exp_set - pred_set

        total_tp += len(tp_set)
        total_fp += len(fp_set)
        total_fn += len(fn_set)

        for s in exp_set:
            per_label_support[s] = per_label_support.get(s, 0) + 1
            if s in pred_set:
                per_label_tp[s] = per_label_tp.get(s, 0) + 1
            else:
                per_label_fn[s] = per_label_fn.get(s, 0) + 1

        for s in fp_set:
            per_label_fp[s] = per_label_fp.get(s, 0) + 1

    # Micro averages
    micro_p = round(total_tp / (total_tp + total_fp), 4) if (total_tp + total_fp) > 0 else 0.0
    micro_r = round(total_tp / (total_tp + total_fn), 4) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = round(2 * (micro_p * micro_r) / (micro_p + micro_r), 4) if (micro_p + micro_r) > 0 else 0.0

    # Macro averages
    per_label_res: Dict[str, Dict[str, Any]] = {}
    label_precisions = []
    label_recalls = []
    label_f1s = []

    for label, support in per_label_support.items():
        tp = per_label_tp.get(label, 0)
        fp = per_label_fp.get(label, 0)
        fn = per_label_fn.get(label, 0)

        p = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
        r = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        f1 = round(2 * (p * r) / (p + r), 4) if (p + r) > 0 else 0.0

        label_precisions.append(p)
        label_recalls.append(r)
        label_f1s.append(f1)

        per_label_res[label] = {
            "support": support,
            "tp": tp, "fp": fp, "fn": fn,
            "precision": p, "recall": r, "f1": f1
        }

    macro_p = round(sum(label_precisions) / len(label_precisions), 4) if label_precisions else 0.0
    macro_r = round(sum(label_recalls) / len(label_recalls), 4) if label_recalls else 0.0
    macro_f1 = round(sum(label_f1s) / len(label_f1s), 4) if label_f1s else 0.0

    return MultiLabelSkillMetrics(
        total_evaluated_ads=len(records),
        ads_with_verified_skills=ads_with_skills,
        micro_precision=micro_p,
        micro_recall=micro_r,
        micro_f1=micro_f1,
        macro_precision=macro_p,
        macro_recall=macro_r,
        macro_f1=macro_f1,
        per_label_metrics=per_label_res
    )


def _aggregate_field_metrics(records: List[RecordEvaluationResult]) -> Dict[str, FieldMetricSummary]:
    """Helper aggregating outcomes across records for all discrete fields."""
    summaries: Dict[str, FieldMetricSummary] = {}
    numeric_err_accumulator: Dict[str, List[float]] = {}

    for rec in records:
        for fld_name, fres in rec.field_results.items():
            if fld_name not in summaries:
                s = FieldMetricSummary(field_name=fld_name)
                if fld_name in ("salary_min", "salary_max"):
                    s.is_numeric = True
                    numeric_err_accumulator[fld_name] = []
                summaries[fld_name] = s
            s = summaries[fld_name]

            if fres.reference_status == "verified":
                s.eligible_references += 1
                if fres.predicted_raw is not None and str(fres.predicted_raw).strip() != "":
                    s.matched_predictions += 1

                if fres.is_exact_match:
                    s.exact_matches += 1

                if fres.status == "correct":
                    s.correct_values += 1
                    if s.is_numeric and fres.numeric_error is not None:
                        numeric_err_accumulator[fld_name].append(fres.numeric_error)
                elif fres.status in ("incorrect", "incompatible_currency", "incompatible_pay_period"):
                    s.incorrect_values += 1
                    if fres.status in ("incompatible_currency", "incompatible_pay_period"):
                        s.excluded_incompatible_count += 1
                    elif s.is_numeric and fres.numeric_error is not None:
                        numeric_err_accumulator[fld_name].append(fres.numeric_error)
                elif fres.status == "missing_prediction":
                    s.missing_predictions += 1

            elif fres.reference_status == "unavailable":
                s.unavailable_references += 1
                if s.is_numeric:
                    s.excluded_unavailable_count += 1
                if fres.status == "correct_absence":
                    s.correct_absence += 1
                elif fres.status == "over_extracted":
                    s.over_extracted += 1

            elif fres.reference_status == "ambiguous":
                s.ambiguous_references += 1
            elif fres.reference_status == "not_reviewed":
                s.not_reviewed_references += 1

    for fname, s in summaries.items():
        errs = numeric_err_accumulator.get(fname)
        s.compute_statistics(numeric_errors=errs)

    return summaries


def compute_evaluation_metrics(
    results: List[RecordEvaluationResult],
    total_benchmarks: int,
    total_predictions: int,
    unmatched_benchmarks: int,
    extra_predictions: int,
    timestamp: str = ""
) -> GlobalEvaluationMetrics:
    """Computes comprehensive global and stratified evaluation metrics."""
    from datetime import datetime, timezone
    ts = timestamp or datetime.now(timezone.utc).isoformat()

    global_fields = _aggregate_field_metrics(results)
    fully_correct = sum(1 for r in results if r.is_fully_correct)
    matched_count = len(results)

    em_rate = round(fully_correct / matched_count, 4) if matched_count > 0 else 0.0
    em_lo, em_hi = wilson_score_interval(fully_correct, matched_count)

    # Macro averages across eligible verified fields
    eligible_fields = [s for s in global_fields.values() if s.eligible_references > 0]
    macro_cov = round(sum(s.extraction_coverage for s in eligible_fields) / len(eligible_fields), 4) if eligible_fields else 0.0
    macro_cor = round(sum(s.extraction_correctness for s in eligible_fields) / len(eligible_fields), 4) if eligible_fields else 0.0
    macro_p = round(sum(s.precision for s in eligible_fields) / len(eligible_fields), 4) if eligible_fields else 0.0
    macro_r = round(sum(s.recall for s in eligible_fields) / len(eligible_fields), 4) if eligible_fields else 0.0
    macro_f1 = round(sum(s.f1_score for s in eligible_fields) / len(eligible_fields), 4) if eligible_fields else 0.0

    # Multi-label skills
    skill_metrics = _compute_multi_label_skill_metrics(results)

    # Stratify by Country
    by_country: Dict[str, StratifiedMetricGroup] = {}
    countries = {r.country for r in results if r.country}
    for c in sorted(list(countries)):
        subset = [r for r in results if r.country == c]
        grp = StratifiedMetricGroup(
            group_name=c, dimension="country", total_records=len(subset),
            fully_correct_records=sum(1 for r in subset if r.is_fully_correct),
            field_metrics=_aggregate_field_metrics(subset)
        )
        grp.compute_rates()
        by_country[c] = grp

    # Stratify by Platform
    by_platform: Dict[str, StratifiedMetricGroup] = {}
    platforms = {r.source_platform for r in results if r.source_platform}
    for p in sorted(list(platforms)):
        subset = [r for r in results if r.source_platform == p]
        grp = StratifiedMetricGroup(
            group_name=p, dimension="platform", total_records=len(subset),
            fully_correct_records=sum(1 for r in subset if r.is_fully_correct),
            field_metrics=_aggregate_field_metrics(subset)
        )
        grp.compute_rates()
        by_platform[p] = grp

    # Stratify by Extraction Method
    by_method: Dict[str, StratifiedMetricGroup] = {}
    methods = {r.extraction_method for r in results if r.extraction_method}
    for m in sorted(list(methods)):
        subset = [r for r in results if r.extraction_method == m]
        grp = StratifiedMetricGroup(
            group_name=m, dimension="extraction_method", total_records=len(subset),
            fully_correct_records=sum(1 for r in subset if r.is_fully_correct),
            field_metrics=_aggregate_field_metrics(subset)
        )
        grp.compute_rates()
        by_method[m] = grp

    return GlobalEvaluationMetrics(
        timestamp=ts,
        total_benchmark_records=total_benchmarks,
        total_predictions_loaded=total_predictions,
        matched_records_count=matched_count,
        unmatched_benchmark_count=unmatched_benchmarks,
        extra_predictions_count=extra_predictions,
        fully_correct_records=fully_correct,
        exact_match_rate=em_rate,
        exact_match_ci_lower=em_lo,
        exact_match_ci_upper=em_hi,
        macro_coverage=macro_cov,
        macro_correctness=macro_cor,
        macro_precision=macro_p,
        macro_recall=macro_r,
        macro_f1=macro_f1,
        field_metrics=global_fields,
        skill_metrics=skill_metrics,
        by_country=by_country,
        by_platform=by_platform,
        by_method=by_method,
    )
