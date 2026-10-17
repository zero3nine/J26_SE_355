# Information Extraction Evaluation Results Directory
**Project:** IT Job Market Intelligence Tool (J26_SE_355)  
**Location:** `data/evaluation/results/`  

---

## Output Artifacts

Running `python -m src.evaluation.evaluate_scraping` automatically produces timestamped artifacts:

1. **`evaluation_report_<YYYYMMDD_HHMMSS>.md`**: Comprehensive human-readable Markdown evaluation report containing:
   - Executive extraction summary (matched records, exact match rate, macro precision, recall, and F1).
   - Field-by-field quality matrix (TP, FP, FN, TN, precision, recall, hallucination rate).
   - Regional stratification analysis across Sri Lanka, India, Singapore, and Malaysia.
   - Extraction method comparison (JSON-LD vs. Site Adapter vs. Generic HTML vs. Browser-Rendered).
   - Qualitative error taxonomy and specific mismatch breakdowns.
2. **`evaluation_metrics_<YYYYMMDD_HHMMSS>.json`**: Machine-readable JSON output containing full statistical counters and nested group breakdowns.
3. **`evaluation_report_latest.md`** & **`evaluation_metrics_latest.json`**: Always updated to reflect the most recent evaluation run.
