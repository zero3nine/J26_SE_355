# Implementation roadmap

The pipeline can reopen saved batches, replay imports with recorded membership, and save both extraction methods as one matched run. Regional Analysis reads the master database without importing records. The research views offer explicit extraction-run selection. See the [issue register](suggestions.md#current-issues) for the remaining limitations.

| Order | Work | Done when |
| --- | --- | --- |
| 1 | **Verify the supported collection environment.** Check browser sandbox and egress in the intended deployment, then pilot permitted portals individually. Verify Windows setup and the admin container. | Approved offline and live checks have dated results for listing and detail coverage, required OCR/browser setup, and field completeness. Restricted sources stay excluded. |
| 2 | **Review posting identity and sample eligibility.** Inspect repeated URLs, portal aliases, possible reposts, and benchmark labels. Define which advertisements qualify for each shared measure. | Reviewed identity rules distinguish repeat observations from distinct postings. A hand-calculated sample gives the expected counts, and documented exclusions explain differences between measures. |
| 3 | **Preserve extraction and temporal evidence.** Record the exact model revision and verified spans. Evaluate trend thresholds and forecast horizons across calendar gaps. | Reviewers can trace published results to model, taxonomy, inputs, and defensible horizon-specific checks. Unsupported projections are suppressed. |
| 4 | **Publish one reviewed empirical sample.** Prepare the cohort and verify the public runtime with only the sanitized snapshot. | Another teammate can reproduce the publication. The hosted dashboard and exports identify the cohort, methods, and limitations, and the snapshot is served read-only. |
