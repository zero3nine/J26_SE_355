"""
Evaluation Reporter: Markdown, JSON Metrics, Error CSV, and Reproducibility Records.
Academic Research Component for Information Extraction Quality Benchmark.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.evaluation.metrics import GlobalEvaluationMetrics
from src.evaluation.comparator import RecordEvaluationResult


def generate_markdown_report(
    metrics: GlobalEvaluationMetrics,
    results: List[RecordEvaluationResult],
    benchmark_path: str,
    predictions_path: str,
    match_key: str = "auto"
) -> str:
    """Generates a rigorous academic Markdown evaluation report."""
    md = []
    md.append("# Information Extraction Quality & Benchmark Evaluation Report")
    md.append(f"**Project:** IT Job Market Intelligence Tool (J26_SE_355)  ")
    md.append(f"**Evaluation Timestamp (UTC):** `{metrics.timestamp}`  ")
    md.append(f"**Benchmark Dataset:** `{benchmark_path}`  ")
    md.append(f"**Predictions Source:** `{predictions_path}`  ")
    md.append(f"**Record Alignment Strategy:** `{match_key}`  ")
    md.append(f"**Unit of Analysis:** Individual Job Advertisement (with intra-record field clustering)  ")
    md.append("")
    md.append("---")
    md.append("")

    # 1. Executive Summary
    md.append("## 1. Executive Summary & Core Quality Scorecard")
    md.append("")
    md.append("> [!IMPORTANT]")
    md.append("> **Coverage vs. Correctness Distinction:**")
    md.append("> - **Extraction Coverage (Completeness):** Proportion of eligible reference values captured by the scraper.")
    md.append("> - **Extraction Correctness (Precision):** Proportion of captured predictions that are factually accurate.")
    md.append("> A system that extracts very few values cannot appear reliable merely because its few predictions happen to be accurate.")
    md.append("")

    md.append("| Evaluation Dimension | Metric Value | 95% Confidence Interval | Scientific Interpretation |")
    md.append("| :--- | :---: | :---: | :--- |")
    md.append(f"| **Benchmark Corpus** | `{metrics.total_benchmark_records}` ads | N/A | Total independently verified reference advertisements |")
    md.append(f"| **Predictions Ingested** | `{metrics.total_predictions_loaded}` ads | N/A | Total candidate scraper output records |")
    md.append(f"| **Aligned Evaluations** | `{metrics.matched_records_count}` ads | N/A | Successfully joined record pairs |")
    md.append(f"| **Unmatched Benchmark Ads** | `{metrics.unmatched_benchmark_count}` ads | N/A | Benchmark vacancies missing from prediction file |")
    md.append(f"| **Extra Predictions** | `{metrics.extra_predictions_count}` ads | N/A | Scraper predictions without benchmark ground truth |")
    md.append(
        f"| **Exact Match Advertisements** | `{metrics.fully_correct_records}` / `{metrics.matched_records_count}` (`{metrics.exact_match_rate * 100:.2f}%`) | "
        f"[{metrics.exact_match_ci_lower * 100:.1f}%, {metrics.exact_match_ci_upper * 100:.1f}%] | "
        f"Advertisements where **all** verified fields are extracted correctly and absent fields omitted |"
    )
    md.append(f"| **Macro Extraction Coverage** | `{metrics.macro_coverage * 100:.2f}%` | N/A | Average field completeness across eligible reference attributes |")
    md.append(f"| **Macro Extraction Correctness** | `{metrics.macro_correctness * 100:.2f}%` | N/A | Average conditional accuracy when an attribute was captured |")
    md.append(f"| **Macro Recall (Unconditional)** | `{metrics.macro_recall * 100:.2f}%` | N/A | Overall capture rate of ground-truth reference values |")
    md.append(f"| **Macro F1-Score** | `{metrics.macro_f1 * 100:.2f}%` | N/A | Harmonic mean of macro precision and recall |")
    md.append("")

    # 2. Field-by-Field Quality Matrix
    md.append("## 2. Field-by-Field Agreement and Quality Matrix")
    md.append("")
    md.append("| Evaluated Field | Eligible (N) | Matched Preds | Correct (TP) | Incorrect | Missing (FN) | Exact Agree % | Norm Agree % | 95% Wilson CI | Coverage % | Correctness % | Unavail (N) | Hallucination % |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

    display_fields = [
        "job_title", "employer", "country", "location", "work_mode",
        "posting_date", "closing_date", "job_description", "salary_disclosed",
        "salary_min", "salary_max", "currency", "pay_period", "skills"
    ]

    for fn in display_fields:
        fm = metrics.field_metrics.get(fn)
        if not fm:
            continue
        ci_str = f"[{fm.wilson_ci_lower * 100:.1f}%, {fm.wilson_ci_upper * 100:.1f}%]" if fm.eligible_references > 0 else "N/A"
        exact_str = f"{fm.exact_agreement_rate * 100:.1f}%" if fm.eligible_references > 0 else "N/A"
        norm_str = f"{fm.normalized_agreement_rate * 100:.1f}%" if fm.eligible_references > 0 else "N/A"
        cov_str = f"{fm.extraction_coverage * 100:.1f}%" if fm.eligible_references > 0 else "N/A"
        cor_str = f"{fm.extraction_correctness * 100:.1f}%" if fm.matched_predictions > 0 else "N/A"
        hal_str = f"{fm.hallucination_rate * 100:.1f}%" if fm.unavailable_references > 0 else "0.0%"

        md.append(
            f"| `{fm.field_name}` | {fm.eligible_references} | {fm.matched_predictions} | {fm.correct_values} | "
            f"{fm.incorrect_values} | {fm.missing_predictions} | {exact_str} | {norm_str} | {ci_str} | "
            f"{cov_str} | {cor_str} | {fm.unavailable_references} | {hal_str} |"
        )
    md.append("")

    # 3. Numeric Salary Error Evaluation
    md.append("## 3. Numeric Salary Error Analysis")
    md.append("")
    md.append("> [!NOTE]")
    md.append("> **Currency and Pay-Period Compatibility Policy:**")
    md.append("> Monetary bounds are only compared when currency and pay period match. Incompatible pairs are excluded from numeric error metrics and tracked separately.")
    md.append("")
    md.append("| Metric | Salary Minimum | Salary Maximum |")
    md.append("| :--- | :---: | :---: |")
    s_min = metrics.field_metrics.get("salary_min")
    s_max = metrics.field_metrics.get("salary_max")

    min_mae_str = f"{s_min.mae:,.2f}" if (s_min and s_min.mae is not None) else "N/A"
    max_mae_str = f"{s_max.mae:,.2f}" if (s_max and s_max.mae is not None) else "N/A"
    min_med_str = f"{s_min.median_ae:,.2f}" if (s_min and s_min.median_ae is not None) else "N/A"
    max_med_str = f"{s_max.median_ae:,.2f}" if (s_max and s_max.median_ae is not None) else "N/A"
    min_comp = s_min.comparable_count if s_min else 0
    max_comp = s_max.comparable_count if s_max else 0
    min_incomp = s_min.excluded_incompatible_count if s_min else 0
    max_incomp = s_max.excluded_incompatible_count if s_max else 0
    min_unavail = s_min.excluded_unavailable_count if s_min else 0
    max_unavail = s_max.excluded_unavailable_count if s_max else 0

    md.append(f"| **Comparable Evaluated Pairs** | `{min_comp}` | `{max_comp}` |")
    md.append(f"| **Mean Absolute Error (MAE)** | `{min_mae_str}` | `{max_mae_str}` |")
    md.append(f"| **Median Absolute Error (MedAE)** | `{min_med_str}` | `{max_med_str}` |")
    md.append(f"| **Excluded Incompatible Pairs** | `{min_incomp}` | `{max_incomp}` |")
    md.append(f"| **Excluded Unavailable References** | `{min_unavail}` | `{max_unavail}` |")
    md.append("")

    # 4. Multi-Label Canonical Skills Evaluation
    if metrics.skill_metrics and metrics.skill_metrics.ads_with_verified_skills > 0:
        sk = metrics.skill_metrics
        md.append("## 4. Canonical Skill Extraction Evaluation (Multi-Label)")
        md.append("")
        md.append(f"- **Evaluated Advertisements with Verified Skills:** {sk.ads_with_verified_skills}")
        md.append(f"- **Micro-Averaged Precision:** {sk.micro_precision * 100:.2f}% | **Recall:** {sk.micro_recall * 100:.2f}% | **F1:** {sk.micro_f1 * 100:.2f}%")
        md.append(f"- **Macro-Averaged Precision:** {sk.macro_precision * 100:.2f}% | **Recall:** {sk.macro_recall * 100:.2f}% | **F1:** {sk.macro_f1 * 100:.2f}%")
        md.append("")
        if sk.per_label_metrics:
            md.append("### Top Per-Label Skill Performance")
            md.append("")
            md.append("| Canonical Skill Label | Support (N) | Precision | Recall | F1-Score |")
            md.append("| :--- | :---: | :---: | :---: | :---: |")
            top_skills = sorted(sk.per_label_metrics.items(), key=lambda x: x[1]["support"], reverse=True)[:8]
            for lbl, data in top_skills:
                md.append(f"| `{lbl}` | {data['support']} | {data['precision'] * 100:.1f}% | {data['recall'] * 100:.1f}% | {data['f1'] * 100:.1f}% |")
            md.append("")

    # 5. Regional Stratification Analysis
    md.append("## 5. Regional Stratification Analysis")
    md.append("")
    md.append("| Country | Sample (N) | Exact Match Ads | Exact Match % | 95% Wilson CI | Title Agreement | Employer Agreement | Work Mode Agreement | Statistical Caveat |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |")

    for country_name, grp in metrics.by_country.items():
        title_norm = grp.field_metrics.get("job_title")
        comp_norm = grp.field_metrics.get("employer")
        wm_norm = grp.field_metrics.get("work_mode")

        t_str = f"{title_norm.normalized_agreement_rate * 100:.1f}%" if title_norm and title_norm.eligible_references > 0 else "N/A"
        c_str = f"{comp_norm.normalized_agreement_rate * 100:.1f}%" if comp_norm and comp_norm.eligible_references > 0 else "N/A"
        w_str = f"{wm_norm.normalized_agreement_rate * 100:.1f}%" if wm_norm and wm_norm.eligible_references > 0 else "N/A"
        ci_str = f"[{grp.wilson_ci_lower * 100:.1f}%, {grp.wilson_ci_upper * 100:.1f}%]"
        caveat = "⚠️ Small sample ($N < 10$)" if grp.is_small_sample else "Adequate pilot sample"

        md.append(
            f"| **{country_name}** | {grp.total_records} | {grp.fully_correct_records} | "
            f"{grp.exact_match_rate * 100:.1f}% | {ci_str} | {t_str} | {c_str} | {w_str} | {caveat} |"
        )
    md.append("")

    # 6. Extraction Architecture Breakdown
    md.append("## 6. Extraction Architecture and Platform Analysis")
    md.append("")
    md.append("| Extraction Method | Evaluated (N) | Exact Match Ads | Exact Match % | 95% Wilson CI | Method Description |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :--- |")
    for method_name, grp in metrics.by_method.items():
        desc = {
            "jsonld": "Schema.org structured metadata",
            "site_adapter": "Tailored REST API / portal adapter",
            "generic_html": "Heuristic fallback across HTML selectors",
            "browser_rendered": "Headless browser DOM hydration for SPAs",
            "none": "Negative controls (error / search pages)"
        }.get(method_name, "Custom adapter")
        ci_str = f"[{grp.wilson_ci_lower * 100:.1f}%, {grp.wilson_ci_upper * 100:.1f}%]"
        md.append(f"| `{method_name}` | {grp.total_records} | {grp.fully_correct_records} | {grp.exact_match_rate * 100:.1f}% | {ci_str} | {desc} |")
    md.append("")

    # 7. Error Taxonomy and Source Distribution
    md.append("## 7. Error Taxonomy & Qualitative Diagnostics")
    md.append("")
    error_cat_counts: Dict[str, int] = {}
    error_by_field: Dict[str, int] = {}
    error_samples: List[Dict[str, Any]] = []

    for r in results:
        for fname, fres in r.field_results.items():
            if fres.status in ("incorrect", "missing_prediction", "over_extracted", "incompatible_currency", "incompatible_pay_period"):
                cat = fres.error_category
                error_cat_counts[cat] = error_cat_counts.get(cat, 0) + 1
                error_by_field[fname] = error_by_field.get(fname, 0) + 1
                if len(error_samples) < 8 and fres.details:
                    error_samples.append({
                        "id": r.benchmark_id,
                        "field": fname,
                        "expected": str(fres.expected_raw)[:35],
                        "predicted": str(fres.predicted_raw)[:35],
                        "category": cat,
                        "details": fres.details
                    })

    md.append("### Most Frequent Error Categories")
    md.append("")
    md.append("| Error Category | Frequency (N) | Description |")
    md.append("| :--- | :---: | :--- |")
    for cat, cnt in sorted(error_cat_counts.items(), key=lambda x: x[1], reverse=True)[:6]:
        md.append(f"| `{cat}` | {cnt} | Primary classification of extraction discrepancy |")
    md.append("")

    if error_samples:
        md.append("### Diagnostic Sample of Extraction Failures")
        md.append("")
        md.append("| Benchmark ID | Field | Expected Ground Truth | Predicted Value | Error Details |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")
        for s in error_samples:
            md.append(f"| `{s['id']}` | `{s['field']}` | `{s['expected']}` | `{s['predicted']}` | {s['details']} |")
        md.append("")

    # 8. Methodological Limitations
    md.append("## 8. Methodological Scope & Statistical Caveats")
    md.append("")
    md.append("1. **Unit of Analysis:** The unit of analysis is the individual job vacancy advertisement. Attribute evaluations within an advertisement are correlated and must not be treated as independent Bernoulli trials.")
    md.append("2. **Convenience Sample Limitations:** This benchmark evaluates extraction engine correctness against authentic web sources. It does not establish the true macroeconomic distribution of job openings or wages across South and Southeast Asia.")
    md.append("3. **Source Drift & Ephemerality:** In the event of source web page expiration, the locally preserved evidence snapshot serves as the definitive reference standard.")
    md.append("")

    return "\n".join(md)


def export_metrics_json(metrics: GlobalEvaluationMetrics, output_file: Path):
    """Exports machine-readable JSON metrics."""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(metrics.to_dict(), f, indent=2)


def export_field_errors_csv(results: List[RecordEvaluationResult], output_file: Path):
    """Exports field-level error CSV identifying all extraction errors, missing values, ambiguous labels, and over-extractions."""
    fieldnames = [
        "benchmark_id",
        "source_url",
        "country",
        "source_platform",
        "extraction_method",
        "field_name",
        "expected_value",
        "predicted_value",
        "expected_raw",
        "expected_normalized",
        "predicted_raw",
        "predicted_normalized",
        "error_category",
        "error_type",
        "error_status",
        "numeric_error",
        "discrepancy_details",
    ]

    rows = []
    for rec in results:
        for fname, fres in rec.field_results.items():
            if fres.status in ("incorrect", "missing_prediction", "over_extracted", "incompatible_currency", "incompatible_pay_period", "ambiguous_excluded"):
                # Sanitize text
                exp_r = str(fres.expected_raw if fres.expected_raw is not None else "")[:120].replace("\n", " ")
                exp_n = str(fres.expected_normalized if fres.expected_normalized is not None else "")[:120].replace("\n", " ")
                pred_r = str(fres.predicted_raw if fres.predicted_raw is not None else "")[:120].replace("\n", " ")
                pred_n = str(fres.predicted_normalized if fres.predicted_normalized is not None else "")[:120].replace("\n", " ")
                num_err = f"{fres.numeric_error:.2f}" if fres.numeric_error is not None else ""

                exp_val = exp_n if exp_n else exp_r
                pred_val = pred_n if pred_n else pred_r
                err_status = fres.error_type if fres.error_type else ("missing" if fres.status == "missing_prediction" else "incorrect")

                rows.append({
                    "benchmark_id": rec.benchmark_id,
                    "source_url": rec.source_url,
                    "country": rec.country,
                    "source_platform": rec.source_platform,
                    "extraction_method": rec.extraction_method,
                    "field_name": fname,
                    "expected_value": exp_val,
                    "predicted_value": pred_val,
                    "expected_raw": exp_r,
                    "expected_normalized": exp_n,
                    "predicted_raw": pred_r,
                    "predicted_normalized": pred_n,
                    "error_category": fres.error_category,
                    "error_type": fres.error_type,
                    "error_status": err_status,
                    "numeric_error": num_err,
                    "discrepancy_details": fres.details.replace("\n", " "),
                })

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def export_stratified_summary_csv(metrics: GlobalEvaluationMetrics, output_file: Path):
    """Exports summary table across Country, Platform, and Method dimensions."""
    fieldnames = [
        "dimension",
        "subgroup_name",
        "total_records",
        "fully_correct_records",
        "exact_match_rate",
        "ci_lower_95",
        "ci_upper_95",
        "is_small_sample",
        "title_agreement_rate",
        "employer_agreement_rate",
        "salary_disclosed_rate",
        "work_mode_agreement_rate"
    ]

    rows = []
    # By Country
    for name, grp in metrics.by_country.items():
        t = grp.field_metrics.get("job_title")
        e = grp.field_metrics.get("employer")
        s = grp.field_metrics.get("salary_disclosed")
        w = grp.field_metrics.get("work_mode")
        rows.append({
            "dimension": "country",
            "subgroup_name": name,
            "total_records": grp.total_records,
            "fully_correct_records": grp.fully_correct_records,
            "exact_match_rate": grp.exact_match_rate,
            "ci_lower_95": grp.wilson_ci_lower,
            "ci_upper_95": grp.wilson_ci_upper,
            "is_small_sample": grp.is_small_sample,
            "title_agreement_rate": t.normalized_agreement_rate if t else 0.0,
            "employer_agreement_rate": e.normalized_agreement_rate if e else 0.0,
            "salary_disclosed_rate": s.normalized_agreement_rate if s else 0.0,
            "work_mode_agreement_rate": w.normalized_agreement_rate if w else 0.0,
        })

    # By Platform
    for name, grp in metrics.by_platform.items():
        t = grp.field_metrics.get("job_title")
        e = grp.field_metrics.get("employer")
        s = grp.field_metrics.get("salary_disclosed")
        w = grp.field_metrics.get("work_mode")
        rows.append({
            "dimension": "platform",
            "subgroup_name": name,
            "total_records": grp.total_records,
            "fully_correct_records": grp.fully_correct_records,
            "exact_match_rate": grp.exact_match_rate,
            "ci_lower_95": grp.wilson_ci_lower,
            "ci_upper_95": grp.wilson_ci_upper,
            "is_small_sample": grp.is_small_sample,
            "title_agreement_rate": t.normalized_agreement_rate if t else 0.0,
            "employer_agreement_rate": e.normalized_agreement_rate if e else 0.0,
            "salary_disclosed_rate": s.normalized_agreement_rate if s else 0.0,
            "work_mode_agreement_rate": w.normalized_agreement_rate if w else 0.0,
        })

    # By Extraction Method
    for name, grp in metrics.by_method.items():
        t = grp.field_metrics.get("job_title")
        e = grp.field_metrics.get("employer")
        s = grp.field_metrics.get("salary_disclosed")
        w = grp.field_metrics.get("work_mode")
        rows.append({
            "dimension": "extraction_method",
            "subgroup_name": name,
            "total_records": grp.total_records,
            "fully_correct_records": grp.fully_correct_records,
            "exact_match_rate": grp.exact_match_rate,
            "ci_lower_95": grp.wilson_ci_lower,
            "ci_upper_95": grp.wilson_ci_upper,
            "is_small_sample": grp.is_small_sample,
            "title_agreement_rate": t.normalized_agreement_rate if t else 0.0,
            "employer_agreement_rate": e.normalized_agreement_rate if e else 0.0,
            "salary_disclosed_rate": s.normalized_agreement_rate if s else 0.0,
            "work_mode_agreement_rate": w.normalized_agreement_rate if w else 0.0,
        })

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def export_reproducibility_record(
    benchmark_path: Path,
    predictions_path: Path,
    output_dir: Path,
    match_key: str,
    metrics: GlobalEvaluationMetrics,
    output_file: Path,
):
    def _file_hash(p: Path) -> str:
        if not p.exists():
            return "not_found"
        with open(p, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def _git_commit() -> str:
        try:
            import subprocess
            r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=2)
            if r.returncode == 0:
                return r.stdout.strip()
        except Exception:
            pass
        return "unknown"

    rec = {
        "evaluation_timestamp_utc": metrics.timestamp,
        "benchmark_version": "1.0.0",
        "code_version": _git_commit(),
        "model_versions": {
            "it_classifier": "2.0.0",
            "shine_adapter": "1.2.0",
            "timesjobs_adapter": "1.0.0",
            "mycareersfuture_adapter": "1.0.0",
        },
        "taxonomy_versions": {
            "role_taxonomy": "0.1.0",
            "skill_taxonomy": "0.1.0",
        },
        "normalization_parameters": {
            "salary_numerical_tolerance": 1.0,
            "text_token_jaccard_threshold": 0.80,
            "description_containment_threshold": 0.60,
            "hours_per_month": 160.0,
            "annual_to_monthly_divisor": 12.0,
        },
        "random_seed": None,  # Deterministic execution
        "configuration": {
            "match_key": match_key,
            "confidence_level": 0.95,
            "confidence_interval_method": "Wilson score interval",
            "salary_numerical_tolerance": 1.0,
            "text_token_jaccard_threshold": 0.80,
            "description_containment_threshold": 0.60,
        },
        "input_artifacts": {
            "benchmark_dataset_path": str(benchmark_path),
            "benchmark_dataset_sha256": _file_hash(benchmark_path),
            "total_benchmark_records": metrics.total_benchmark_records,
            "predictions_path": str(predictions_path),
            "predictions_sha256": _file_hash(predictions_path),
            "total_predictions_loaded": metrics.total_predictions_loaded,
        },
        "alignment_summary": {
            "matched_records_count": metrics.matched_records_count,
            "unmatched_benchmark_count": metrics.unmatched_benchmark_count,
            "extra_predictions_count": metrics.extra_predictions_count,
        },
        "headline_results": {
            "exact_match_rate": metrics.exact_match_rate,
            "exact_match_95_ci": [metrics.exact_match_ci_lower, metrics.exact_match_ci_upper],
            "macro_coverage": metrics.macro_coverage,
            "macro_correctness": metrics.macro_correctness,
            "macro_f1": metrics.macro_f1,
        }
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2)
