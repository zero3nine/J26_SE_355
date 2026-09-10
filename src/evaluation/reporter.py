"""
Evaluation Report Generator: Markdown and Machine-Readable JSON.
Academic Research Component for Information Extraction Quality Benchmark.
"""

from __future__ import annotations

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
    """Generates a comprehensive academic Markdown evaluation report."""
    md = []
    md.append("# Information Extraction Benchmark Evaluation Report")
    md.append(f"**Project:** IT Job Market Intelligence Tool (J26_SE_355)  ")
    md.append(f"**Evaluation Timestamp (UTC):** `{metrics.timestamp}`  ")
    md.append(f"**Benchmark Dataset:** `{benchmark_path}`  ")
    md.append(f"**Predictions Source:** `{predictions_path}`  ")
    md.append(f"**Record Alignment Strategy:** `{match_key}`  ")
    md.append("")
    md.append("---")
    md.append("")

    # 1. Executive Summary
    md.append("## 1. Executive Summary & Core Extraction Metrics")
    md.append("")
    md.append("| Metric | Value | Description |")
    md.append("| :--- | :--- | :--- |")
    md.append(f"| **Benchmark Records** | `{metrics.total_benchmark_records}` | Total independently verified ground truth advertisements |")
    md.append(f"| **Predictions Loaded** | `{metrics.total_predictions_loaded}` | Total raw or cleaned scraping output records |")
    md.append(f"| **Matched Evaluations** | `{metrics.matched_records_count}` | Records aligned for independent field-by-field evaluation |")
    md.append(f"| **Unmatched Benchmark Records** | `{metrics.unmatched_benchmark_count}` | Verified advertisements absent from prediction file |")
    md.append(f"| **Extra Predictions** | `{metrics.extra_predictions_count}` | Prediction records not present in the benchmark dataset |")
    md.append(f"| **Exact Match Advertisements** | `{metrics.fully_correct_records}` / `{metrics.matched_records_count}` (`{metrics.exact_match_rate * 100:.2f}%`) | Advertisements where all verified fields were extracted correctly |")
    md.append(f"| **Macro Precision** | `{metrics.macro_precision * 100:.2f}%` | Unweighted average precision across verified extraction fields |")
    md.append(f"| **Macro Recall** | `{metrics.macro_recall * 100:.2f}%` | Unweighted average extraction recall across verified fields |")
    md.append(f"| **Macro F1-Score** | `{metrics.macro_f1 * 100:.2f}%` | Harmonic mean of macro precision and recall |")
    md.append("")

    # 2. Field-by-Field Quality Matrix
    md.append("## 2. Field-by-Field Quality & Verification Matrix")
    md.append("")
    md.append("> [!NOTE]")
    md.append("> Reference statuses strictly distinguish verified, unavailable, and ambiguous source data.")
    md.append("> Missing source information is never interpreted as a confirmed value.")
    md.append("")
    md.append("| Field | Verified (N) | Correct (TP) | Incorrect | Missing (FN) | Precision | Recall | F1 | Unavail (N) | Correct Absent (TN) | Over-Extracted (FP) | Hallucination Rate |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

    sorted_fields = [
        "job_title", "company", "location_raw", "country_normalized",
        "city_normalized", "work_mode", "posted_date", "closing_date",
        "description", "salary", "skills"
    ]
    for fn in sorted_fields:
        fm = metrics.field_metrics.get(fn)
        if not fm:
            continue
        p_pct = f"{fm.precision * 100:.1f}%" if fm.verified_total > 0 else "N/A"
        r_pct = f"{fm.recall * 100:.1f}%" if fm.verified_total > 0 else "N/A"
        f1_pct = f"{fm.f1_score * 100:.1f}%" if fm.verified_total > 0 else "N/A"
        hr_pct = f"{fm.hallucination_rate * 100:.1f}%" if fm.unavailable_total > 0 else "0.0%"

        md.append(
            f"| `{fm.field_name}` | {fm.verified_total} | {fm.correct} | {fm.incorrect} | "
            f"{fm.missing_prediction} | {p_pct} | {r_pct} | {f1_pct} | "
            f"{fm.unavailable_total} | {fm.correct_absence} | {fm.over_extracted} | {hr_pct} |"
        )
    md.append("")

    # 3. Country Stratification
    md.append("## 3. Regional Stratification Analysis")
    md.append("")
    md.append("| Country | Sample (N) | Exact Match Ads | Exact Match % | Title F1 | Company F1 | Salary Disclosed F1 | Work Mode F1 |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

    for country_name, grp in metrics.by_country.items():
        title_f1 = grp.field_metrics.get("job_title")
        comp_f1 = grp.field_metrics.get("company")
        sal_f1 = grp.field_metrics.get("salary")
        wm_f1 = grp.field_metrics.get("work_mode")

        t_str = f"{title_f1.f1_score * 100:.1f}%" if title_f1 and title_f1.verified_total > 0 else "N/A"
        c_str = f"{comp_f1.f1_score * 100:.1f}%" if comp_f1 and comp_f1.verified_total > 0 else "N/A"
        s_str = f"{sal_f1.f1_score * 100:.1f}%" if sal_f1 and sal_f1.verified_total > 0 else "N/A"
        w_str = f"{wm_f1.f1_score * 100:.1f}%" if wm_f1 and wm_f1.verified_total > 0 else "N/A"

        md.append(
            f"| **{country_name}** | {grp.total_records} | {grp.fully_correct_records} | "
            f"{grp.exact_match_rate * 100:.1f}% | {t_str} | {c_str} | {s_str} | {w_str} |"
        )
    md.append("")

    # 4. Portal and Extraction Method Performance
    md.append("## 4. Extraction Method and Portal Breakdown")
    md.append("")
    md.append("### Extraction Architecture Comparison")
    md.append("")
    md.append("| Extraction Method | Evaluated Records (N) | Exact Match Records | Exact Match Rate | Method Description |")
    md.append("| :--- | :---: | :---: | :---: | :--- |")
    for method_name, grp in metrics.by_method.items():
        desc = {
            "jsonld": "Schema.org JobPosting structured metadata",
            "site_adapter": "Portal-tailored DOM / REST API extraction",
            "generic_html": "Heuristic fallback across unstructured HTML",
            "browser_rendered": "Headless browser DOM hydration for SPAs",
            "none": "Failed or unextracted pages"
        }.get(method_name, "Custom adapter")
        md.append(f"| `{method_name}` | {grp.total_records} | {grp.fully_correct_records} | {grp.exact_match_rate * 100:.1f}% | {desc} |")
    md.append("")

    md.append("### Source Platform Breakdown")
    md.append("")
    md.append("| Platform Hostname | Sample (N) | Exact Match Rate | Primary Country |")
    md.append("| :--- | :---: | :---: | :--- |")
    for plat_name, grp in metrics.by_platform.items():
        # find country
        plat_country = next((r.country for r in results if r.source_platform == plat_name), "Unknown")
        md.append(f"| `{plat_name}` | {grp.total_records} | {grp.exact_match_rate * 100:.1f}% | {plat_country} |")
    md.append("")

    # 5. Qualitative Error Taxonomy & Error Samples
    md.append("## 5. Qualitative Error Taxonomy & Failure Case Analysis")
    md.append("")
    errors_by_type: Dict[str, List[Dict[str, str]]] = {
        "mismatches": [],
        "missing_predictions": [],
        "over_extractions": [],
    }

    for r in results:
        for fname, fres in r.field_results.items():
            if fres.status == "incorrect":
                errors_by_type["mismatches"].append({
                    "id": r.benchmark_id, "field": fname,
                    "expected": str(fres.expected_value)[:40],
                    "predicted": str(fres.predicted_value)[:40],
                    "details": fres.details
                })
            elif fres.status == "missing_prediction":
                errors_by_type["missing_predictions"].append({
                    "id": r.benchmark_id, "field": fname,
                    "expected": str(fres.expected_value)[:40],
                    "details": fres.details
                })
            elif fres.status == "over_extracted":
                errors_by_type["over_extractions"].append({
                    "id": r.benchmark_id, "field": fname,
                    "predicted": str(fres.predicted_value)[:40],
                    "details": fres.details
                })

    md.append(f"- **Value Discrepancies (Incorrect extractions):** {len(errors_by_type['mismatches'])}")
    md.append(f"- **Omissions (Missing predictions for verified fields):** {len(errors_by_type['missing_predictions'])}")
    md.append(f"- **Over-extractions (Hallucinations on unavailable fields):** {len(errors_by_type['over_extractions'])}")
    md.append("")

    if errors_by_type["mismatches"]:
        md.append("#### Sample Value Discrepancies")
        md.append("")
        md.append("| Benchmark ID | Field | Expected Ground Truth | System Prediction | Discrepancy Reason |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")
        for err in errors_by_type["mismatches"][:6]:
            md.append(f"| `{err['id']}` | `{err['field']}` | `{err['expected']}` | `{err['predicted']}` | {err['details']} |")
        md.append("")

    # 6. Ambiguities & Scope Limitations
    md.append("## 6. Source Ambiguities & Methodological Limitations")
    md.append("")
    md.append("1. **Convenience Sample Scope:** This pilot benchmark of independently audited job advertisements provides rigorous point validation for extraction heuristics. It does not establish statistical representativeness of entire national labor markets.")
    md.append("2. **Separation from Operational Pipelines:** Reference benchmark labels are strictly stored in `data/evaluation/` and must never be fed into scraping queues or used for dynamic threshold calibration.")
    md.append("3. **Irreducible Ambiguity:** Source pages with indeterminate locations (e.g., 'Remote / APAC') or unanchored relative dates ('Recently added') are flagged as `ambiguous` and excluded from strict accuracy denominators.")
    md.append("")

    return "\n".join(md)


def export_metrics_json(metrics: GlobalEvaluationMetrics, output_file: Path):
    """Exports metrics to machine-readable JSON."""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(metrics.to_dict(), f, indent=2)
