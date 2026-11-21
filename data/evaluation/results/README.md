# Information Extraction Evaluation Results Directory
**Project:** IT Job Market Intelligence Tool (J26_SE_355)  
**Location:** `data/evaluation/results/`  

---

## Output Artifacts

Follow the [evaluation CLI guide](../BENCHMARK_DOCUMENTATION.md#6-how-to-run-the-evaluation-cli) to choose predictions and an output directory. A run with matching records writes these artifacts:

1. **`evaluation_report_<YYYYMMDD_HHMMSS>.md`**: Comprehensive human-readable Markdown evaluation report containing:
   - Executive extraction summary (matched records, exact match rate, macro precision, recall, and F1).
   - Field-by-field quality matrix (TP, FP, FN, TN, precision, recall, hallucination rate).
   - Regional stratification analysis across Sri Lanka, India, Singapore, and Malaysia.
   - Extraction method comparison (JSON-LD vs. Site Adapter vs. Generic HTML vs. Browser-Rendered).
   - Qualitative error taxonomy and specific mismatch breakdowns.
2. **`evaluation_metrics_<YYYYMMDD_HHMMSS>.json`**: Machine-readable JSON output containing full statistical counters and nested group breakdowns.
3. **`evaluation_errors_<YYYYMMDD_HHMMSS>.csv`** and **`evaluation_summary_<YYYYMMDD_HHMMSS>.csv`** record field errors and grouped metrics.
4. **`evaluation_reproducibility_<YYYYMMDD_HHMMSS>.json`** records the run inputs and settings.

Each artifact also has a `_latest` copy in the chosen output directory. The reports checked into this directory record past runs. Use a separate output directory when reproducing them.
