# Extraction follow-ups

The shared vocabulary, lexical and semantic extractors, calibration and evaluation commands, Streamlit workflow, and CSV exports are in place. See [how to run extraction](README.md).

1. Persist per-job, per-method completion for a matched input cohort. Cover successful zero-skill results, failures, and retries during the save.
2. Preserve the actual model and taxonomy versions, threshold, input-text provenance, and available matching evidence. Document how title fallback labels relate to the text passed to the extractors.
3. Record how human annotators define technical skills. Use separate calibration and held-out samples and report precision, recall, and F1 at the selected threshold. Keep labels out of the extraction inputs.
4. Make research readers select one explicit run or matched cohort and explain exclusions so method comparisons can be reproduced.

See the [issue register](../../docs/suggestions.md#current-issues) for evidence and the [roadmap](../../docs/roadmap.md) for acceptance checks.
