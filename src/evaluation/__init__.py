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
from src.evaluation.comparator import (
    compare_records,
    compare_single_record,
    FieldEvaluationResult,
    RecordEvaluationResult,
    normalize_text_for_comparison,
    normalize_company_name,
    normalize_date_to_iso,
    normalize_float,
    normalize_currency_code,
    normalize_pay_period,
)
from src.evaluation.metrics import (
    compute_evaluation_metrics,
    wilson_score_interval,
    FieldMetricSummary,
    MultiLabelSkillMetrics,
    StratifiedMetricGroup,
    GlobalEvaluationMetrics,
)
from src.evaluation.reporter import (
    generate_markdown_report,
    export_metrics_json,
    export_field_errors_csv,
    export_stratified_summary_csv,
    export_reproducibility_record,
)

__all__ = [
    "BenchmarkRecord",
    "BENCHMARK_SCHEMA_COLUMNS",
    "ALLOWED_STATUSES",
    "ALLOWED_COUNTRIES",
    "ALLOWED_WORK_MODES",
    "load_benchmark_dataset",
    "validate_benchmark_records",
    "compare_records",
    "compare_single_record",
    "FieldEvaluationResult",
    "RecordEvaluationResult",
    "normalize_text_for_comparison",
    "normalize_company_name",
    "normalize_date_to_iso",
    "normalize_float",
    "normalize_currency_code",
    "normalize_pay_period",
    "compute_evaluation_metrics",
    "wilson_score_interval",
    "FieldMetricSummary",
    "MultiLabelSkillMetrics",
    "StratifiedMetricGroup",
    "GlobalEvaluationMetrics",
    "generate_markdown_report",
    "export_metrics_json",
    "export_field_errors_csv",
    "export_stratified_summary_csv",
    "export_reproducibility_record",
]
