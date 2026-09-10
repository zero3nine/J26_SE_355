"""
Statistical Metrics Aggregator for Information Extraction Benchmark.
Academic Research Component for Regional Comparative IT Labor-Market Analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Set, Tuple

from src.evaluation.comparator import RecordEvaluationResult, FieldEvaluationResult


@dataclass
class FieldMetricSummary:
    """Statistical summary for a single field across all evaluated records."""
    field_name: str
    verified_total: int = 0
    correct: int = 0
    incorrect: int = 0
    missing_prediction: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0

    unavailable_total: int = 0
    correct_absence: int = 0
    over_extracted: int = 0
    hallucination_rate: float = 0.0

    ambiguous_total: int = 0
    not_reviewed_total: int = 0

    def compute_rates(self):
        """Calculates precision, recall, F1, and hallucination rate."""
        # Precision = TP / (TP + FP)
        extracted = self.correct + self.incorrect
        self.precision = round(self.correct / extracted, 4) if extracted > 0 else 0.0

        # Recall = TP / (TP + FN) = TP / verified_total
        self.recall = round(self.correct / self.verified_total, 4) if self.verified_total > 0 else 0.0

        # F1 = 2 * P * R / (P + R)
        if (self.precision + self.recall) > 0:
            self.f1_score = round(2 * (self.precision * self.recall) / (self.precision + self.recall), 4)
        else:
            self.f1_score = 0.0

        # Hallucination Rate = Over-extracted / Unavailable
        if self.unavailable_total > 0:
            self.hallucination_rate = round(self.over_extracted / self.unavailable_total, 4)
        else:
            self.hallucination_rate = 0.0


@dataclass
class StratifiedMetricGroup:
    """Group of metrics stratified by a dimension (e.g. Country, Platform, Method)."""
    group_name: str
    dimension: str
    total_records: int = 0
    fully_correct_records: int = 0
    field_metrics: Dict[str, FieldMetricSummary] = field(default_factory=dict)

    @property
    def exact_match_rate(self) -> float:
        return round(self.fully_correct_records / self.total_records, 4) if self.total_records > 0 else 0.0


@dataclass
class GlobalEvaluationMetrics:
    """Complete evaluation metrics structure."""
    timestamp: str
    total_benchmark_records: int
    total_predictions_loaded: int
    matched_records_count: int
    unmatched_benchmark_count: int
    extra_predictions_count: int

    fully_correct_records: int = 0
    exact_match_rate: float = 0.0
    macro_f1: float = 0.0
    macro_precision: float = 0.0
    macro_recall: float = 0.0

    field_metrics: Dict[str, FieldMetricSummary] = field(default_factory=dict)
    by_country: Dict[str, StratifiedMetricGroup] = field(default_factory=dict)
    by_platform: Dict[str, StratifiedMetricGroup] = field(default_factory=dict)
    by_method: Dict[str, StratifiedMetricGroup] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Converts entire structure to dictionary for JSON output."""
        return {
            "metadata": {
                "timestamp": self.timestamp,
                "total_benchmark_records": self.total_benchmark_records,
                "total_predictions_loaded": self.total_predictions_loaded,
                "matched_records_count": self.matched_records_count,
                "unmatched_benchmark_count": self.unmatched_benchmark_count,
                "extra_predictions_count": self.extra_predictions_count,
                "fully_correct_records": self.fully_correct_records,
                "exact_match_rate": self.exact_match_rate,
                "macro_f1": self.macro_f1,
                "macro_precision": self.macro_precision,
                "macro_recall": self.macro_recall,
            },
            "field_metrics": {k: asdict(v) for k, v in self.field_metrics.items()},
            "by_country": {
                k: {
                    "group_name": v.group_name,
                    "total_records": v.total_records,
                    "fully_correct_records": v.fully_correct_records,
                    "exact_match_rate": v.exact_match_rate,
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
                }
                for k, v in self.by_platform.items()
            },
            "by_method": {
                k: {
                    "group_name": v.group_name,
                    "total_records": v.total_records,
                    "fully_correct_records": v.fully_correct_records,
                    "exact_match_rate": v.exact_match_rate,
                }
                for k, v in self.by_method.items()
            }
        }


def _aggregate_field_metrics(records: List[RecordEvaluationResult]) -> Dict[str, FieldMetricSummary]:
    """Helper to aggregate field outcomes across a subset of records."""
    summaries: Dict[str, FieldMetricSummary] = {}

    for rec in records:
        for fld_name, fld_res in rec.field_results.items():
            if fld_name not in summaries:
                summaries[fld_name] = FieldMetricSummary(field_name=fld_name)
            s = summaries[fld_name]

            if fld_res.reference_status == "verified":
                s.verified_total += 1
                if fld_res.status == "correct":
                    s.correct += 1
                elif fld_res.status == "incorrect":
                    s.incorrect += 1
                elif fld_res.status == "missing_prediction":
                    s.missing_prediction += 1

            elif fld_res.reference_status == "unavailable":
                s.unavailable_total += 1
                if fld_res.status == "correct_absence":
                    s.correct_absence += 1
                elif fld_res.status == "over_extracted":
                    s.over_extracted += 1

            elif fld_res.reference_status == "ambiguous":
                s.ambiguous_total += 1
            elif fld_res.reference_status == "not_reviewed":
                s.not_reviewed_total += 1

    for s in summaries.values():
        s.compute_rates()

    return summaries


def compute_evaluation_metrics(
    results: List[RecordEvaluationResult],
    total_benchmarks: int,
    total_predictions: int,
    unmatched_benchmarks: int,
    extra_predictions: int,
    timestamp: str = ""
) -> GlobalEvaluationMetrics:
    """Computes global and stratified evaluation metrics from record comparison results."""
    from datetime import datetime, timezone
    ts = timestamp or datetime.now(timezone.utc).isoformat()

    global_fields = _aggregate_field_metrics(results)
    fully_correct = sum(1 for r in results if r.is_fully_correct)
    matched_count = len(results)

    em_rate = round(fully_correct / matched_count, 4) if matched_count > 0 else 0.0

    # Macro averages across verified fields
    verified_fields = [s for s in global_fields.values() if s.verified_total > 0]
    macro_f1 = round(sum(s.f1_score for s in verified_fields) / len(verified_fields), 4) if verified_fields else 0.0
    macro_p = round(sum(s.precision for s in verified_fields) / len(verified_fields), 4) if verified_fields else 0.0
    macro_r = round(sum(s.recall for s in verified_fields) / len(verified_fields), 4) if verified_fields else 0.0

    # Stratify by Country
    by_country: Dict[str, StratifiedMetricGroup] = {}
    countries = {r.country for r in results if r.country}
    for c in sorted(list(countries)):
        subset = [r for r in results if r.country == c]
        group = StratifiedMetricGroup(
            group_name=c,
            dimension="country",
            total_records=len(subset),
            fully_correct_records=sum(1 for r in subset if r.is_fully_correct),
            field_metrics=_aggregate_field_metrics(subset)
        )
        by_country[c] = group

    # Stratify by Platform
    by_platform: Dict[str, StratifiedMetricGroup] = {}
    platforms = {r.source_platform for r in results if r.source_platform}
    for p in sorted(list(platforms)):
        subset = [r for r in results if r.source_platform == p]
        group = StratifiedMetricGroup(
            group_name=p,
            dimension="platform",
            total_records=len(subset),
            fully_correct_records=sum(1 for r in subset if r.is_fully_correct),
            field_metrics=_aggregate_field_metrics(subset)
        )
        by_platform[p] = group

    # Stratify by Extraction Method
    by_method: Dict[str, StratifiedMetricGroup] = {}
    methods = {r.extraction_method for r in results if r.extraction_method}
    for m in sorted(list(methods)):
        subset = [r for r in results if r.extraction_method == m]
        group = StratifiedMetricGroup(
            group_name=m,
            dimension="extraction_method",
            total_records=len(subset),
            fully_correct_records=sum(1 for r in subset if r.is_fully_correct),
            field_metrics=_aggregate_field_metrics(subset)
        )
        by_method[m] = group

    return GlobalEvaluationMetrics(
        timestamp=ts,
        total_benchmark_records=total_benchmarks,
        total_predictions_loaded=total_predictions,
        matched_records_count=matched_count,
        unmatched_benchmark_count=unmatched_benchmarks,
        extra_predictions_count=extra_predictions,
        fully_correct_records=fully_correct,
        exact_match_rate=em_rate,
        macro_f1=macro_f1,
        macro_precision=macro_p,
        macro_recall=macro_r,
        field_metrics=global_fields,
        by_country=by_country,
        by_platform=by_platform,
        by_method=by_method,
    )
