"""
Evaluation package for scraping data quality and information extraction accuracy.
"""

from src.evaluation.schema import (
    BenchmarkRecord,
    BENCHMARK_SCHEMA_COLUMNS,
    ALLOWED_STATUSES,
    ALLOWED_COUNTRIES,
    ALLOWED_WORK_MODES,
    load_benchmark_dataset,
    validate_benchmark_records,
)
from src.evaluation.comparator import compare_records
from src.evaluation.metrics import compute_evaluation_metrics
from src.evaluation.reporter import generate_markdown_report, export_metrics_json

__all__ = [
    "BenchmarkRecord",
    "BENCHMARK_SCHEMA_COLUMNS",
    "ALLOWED_STATUSES",
    "ALLOWED_COUNTRIES",
    "ALLOWED_WORK_MODES",
    "load_benchmark_dataset",
    "validate_benchmark_records",
    "compare_records",
    "compute_evaluation_metrics",
    "generate_markdown_report",
    "export_metrics_json",
]
