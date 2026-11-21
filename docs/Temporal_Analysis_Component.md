# Temporal Analysis Component

## Purpose, ownership, and research basis

The Temporal Trend & Emerging Skill Analysis component belongs to **Munasinghe A T (IT23210042)** within J26-SE-355. It examines how employer-requested technical skills change over time, using the shared job dataset and lexical/semantic skill representations. It also asks whether changing extraction representation changes temporal conclusions.

The research basis is **IT23210042_Proposal_Report_261021_193752.pdf**, especially sections 2-5, together with the overall TAF. This guide describes code inspected on **2026-11-14**, separating existing behavior from proposal commitments. See [About.md](About.md) for the overall framework and [suggestions.md](suggestions.md) for recommended corrections.

The proposal specifies a quantitative, longitudinal, observational study: normalize demand by eligible advertisements, examine change and persistence, screen emerging skills, and forecast only when data supports it. Active collection is expected to cover approximately 6-12 months; historical supplementation targets **up to approximately ten years**, conditional on reliable dates, density, and comparable sources. Neither interval is a claim about the dataset currently available.

The component owns temporal integration, date/period checks, aggregation, trend measures, candidate classifications, conditional forecasts, forecast evaluation, temporal method sensitivity, and their visualizations. Extraction models and ground-truth skill annotation are upstream/shared responsibilities. Role, relationship, and regional analysis remain separate components.

## Implementation map

| File | Responsibility |
| --- | --- |
| `src/analytics/temporal_analysis.py` | Database readers, date parsing, demand series, zero expansion, trend rules, forecasting, back-testing, and representation comparison. |
| `pages/13_Temporal_Analysis.py` | Research controls, charts, tables, downloads, role slices, quality checks, and source-audit sample. |
| `src/analysis/build_temporal_dataset.py` | Separate CSV preparation utility; it does not populate the temporal page or persist results to SQLite. |
| `src/database/connection.py`, `schema.sql`, `repository.py` | Shared jobs, skill mentions, extraction/import runs, and persistence helpers. |
| `src/roles/role_skill_analysis.py` | Shared title-first role classifier used for role-specific temporal views. |
| `tests/test_temporal_analysis.py` | Existing small regression suite for denominators, period construction, forecasts, and evaluation. |

## Inputs and date handling

The normal workflow is **Master Dataset → Extract Skills → Save lexical and semantic results → Temporal Analysis**. Select a matched extraction run to use its recorded job cohort and both methods. Choose **Legacy data (unverified cohort)** to work with older pooled job and skill records.

Matched mode reads the selected run's completed jobs, including jobs with zero skill mentions. Legacy mode gets mentions from `load_temporal_input()` and uses dated master jobs from `load_eligible_jobs()` as its denominator. `normalize_dates()` parses posting dates as UTC, removes the timezone for aggregation, and drops unparseable dates.

Important current boundaries:

- A non-empty date counted in the page's headline is not necessarily parseable.
- Temporal measures use dated jobs in the selected scope. Review the cohort for IT classification, duplicates, and source coverage before interpreting it.
- Skill grouping uses stored `skill_name`, not a join to a canonical display-name/version contract.
- Future dates can be flagged by page checks but are not rejected by the analytics reader itself.

For defensible analysis, supply reliable advertisement posting dates, preserve their provenance, and establish an explicit eligible IT cohort before interpretation. Publication dates and observation timestamps answer different questions.

## Demand measurement and controls

For skill `s` and period `t`:

```text
demand_rate(s, t) = 100 * distinct jobs mentioning s in t
                          / distinct eligible jobs in t
```

For example, 20 Python advertisements among 100 eligible jobs give 20% demand. Forty among 200 also give 20%; increased collection volume alone is not demand growth. A job mentioning a skill repeatedly counts once per period/skill.

`build_demand_series()` applies country/source filters to numerator and denominator, creates monthly (`M`) or calendar-quarterly (`Q`) buckets, and returns:

- A skill-period table: `period`, `skill_name`, `jobs_mentioning_skill`, `eligible_jobs`, `demand_rate`.
- A denominator table with `period`, `eligible_jobs`, and `meets_min_jobs`.

Callers must pass `jobs_df` containing the whole eligible population to preserve zero-skill jobs. The Streamlit page does so. The library fallback uses the supplied skill frame, which can inflate percentages if zero-skill jobs are absent.

The page defaults to monthly aggregation, five eligible jobs per period, six periods for trend classification, and three-period recent and baseline windows. Country and source are selectable. The role selector applies to the role-specific chart. The `all` representation takes the union of the saved methods within the selected scope.

### Zero demand, missing periods, and sample thresholds

`expand_zero_demand_periods()` adds zero mentions between each skill's first and last retained mention periods only for observations that meet the sample threshold. Missing and below-threshold periods stay out of the demand series. The denominator table keeps the observed sample counts for inspection.

## Trend indicators and current screening rules

`trend_table()` orders each skill's observations, constructs a calendar index, then drops missing rates before fitting. It reports:

| Indicator | Current calculation |
| --- | --- |
| Baseline/recent rate | Unweighted means of the preceding and latest configured observation windows. Short histories shrink the windows and can cause overlap. |
| Absolute change | Recent mean minus baseline mean, in percentage points. |
| Relative growth | Absolute change divided by baseline, times 100; undefined when baseline is zero. |
| Trend slope | NumPy linear fit against sequential observation indices. |
| Persistence | Fraction of the latest available consecutive differences that are positive. |
| Volatility | Population standard deviation of observed rates, in percentage points. |

The current ordered rules are:

1. Fewer than the required observations: **Volatile / uncertain**.
2. Baseline at most `max(1.0, series 35th percentile)`, positive recent change, positive slope, and persistence at least `0.5`: **Emerging candidate**.
3. Slope above `0.05` and positive recent change: **Growing**.
4. Slope below `-0.05` and negative recent change: **Declining**.
5. Standard deviation above `max(1.0, 0.75 * mean rate)`: **Volatile / uncertain**.
6. Otherwise: **Stable**.

These are heuristics, not validated emergence labels. Volatility is checked after directional rules, so a volatile series can receive a directional label. Missing calendar periods are compressed when fitting the slope and forming windows; the reported slope therefore need not represent equal elapsed calendar intervals. Source-composition stability does not enter the rule automatically.

The proposal calls for data-informed thresholds and sensitivity analysis. The current page exposes some aggregation/window controls, but it does not automatically evaluate threshold robustness, detect formal change points, or report period-by-period rank movement.

## Conditional forecasting and evaluation

`forecast_skill()` predicts normalized demand rates **one to three periods ahead**. It requires at least eight usable observations by default. It returns last-value, trailing-three-observation average, and linear-trend candidates. At 24 observations, with scikit-learn available, it also fits a Random Forest using three lagged rates and their mean, recursively generating future predictions. Outputs are clipped to 0-100%.

Random Forest forecasting uses 150 trees, `random_state=42`, and `min_samples_leaf=2`. It is fitted on the available historical lag examples; the function does not select it only when it beats baselines. Eight observations are a software gate, not a research justification that the series is forecastable.

`evaluate_forecast_baselines()` performs expanding-window, one-step rolling-origin evaluation: each target uses earlier observations only. Baseline evaluation requires at least ten observations by default. Random Forest evaluation becomes available at 15 observations; when enabled, all models use the same targets from index 12 onward. The evaluation forest uses 100 trees, so it is not identical to the final 150-tree forecast candidate.

Reported metrics are MAE and RMSE in percentage points, plus directional accuracy against movement from the last observation. Lower error is preferable; small target counts make rankings uncertain. The three-period forecast is not validated by a one-step score alone. There are no prediction intervals, seasonal baselines, sMAPE, Gradient Boosting, or sequence models in the current temporal implementation. The latter models are proposal candidates/extensions, not requirements to add regardless of data adequacy.

Calendar continuity is not enforced before training. Missing observations can make a lag mean 'previous observed period' rather than 'previous month/quarter'. Source coverage and statistical uncertainty require additional gates before public forecasts are credible.

## Lexical versus semantic sensitivity

Matched mode compares both methods on the same saved jobs and qualifying periods. It adds genuine zeros for skills that a method did not mention in an eligible period, including skills found only by the other method. Legacy mode retains its positive-mention mean. The page reports mean demand, rank correlation, top-10 overlap, and agreement among skills with trend labels.

These are sensitivity diagnostics, not precision/recall/F1 scores or proof that semantic extraction is correct. The proposal's controlled comparison requires the same advertisements, period grid, canonical taxonomy, eligibility rules, and recorded configuration for both methods.

## Outputs, quality checks, and separate CSV preparation

The page offers historical and role-specific charts, trend classifications, forecast/evaluation tables, method comparison, denominators, automated quality checks, and a deterministic source/year audit sample. Downloads include `temporal_skill_period_series.csv`, `temporal_trend_classifications.csv`, `temporal_forecast.csv`, `temporal_forecast_evaluation.csv`, and `lexical_semantic_temporal_comparison.csv`. These are exports, not persisted published results.

The headline missing-date diagnostic operates on `load_eligible_jobs()`, which already excludes blank dates; the later full-master automated checks provide a broader missingness report. Exported audit samples require human source checking; preparing a sample is not completed verification.

The independent CSV utility can prepare existing extracted files:

```bash
python -m src.analysis.build_temporal_dataset --input data/processed/jobs_extracted.csv --output data/analysis/temporal --frequency M
```

It writes `temporal_jobs_with_quality_flags.csv`, `temporal_skill_demand.csv`, and `temporal_data_quality_report.csv`. It chooses the first existing date/skill column from hard-coded candidate lists, rather than selecting a non-empty field per row. Skill preference starts with canonical, then semantic fields, then raw/lexical fields. Verify the reported selected columns; this command is not a lexical/semantic comparison.

Unlike the database reader, the utility can interpret relative posting labels against `scraped_at`/`collected_at`, recording `relative_to_collected_at`. Inspect that provenance: an import timestamp is not necessarily the observation time needed to resolve an old 'two months ago' label. The utility cannot retrieve expired advertisements, and raw batches without a recognized skills column are insufficient. Its eligibility/duplicate flags and CSV column names differ from the database path.

## Verification and remaining work

Run the existing component suite from the repository root:

```bash
python -m unittest discover -s tests -p "test_temporal_analysis.py"
```

On 2026-11-14, all five tests passed in the existing environment. They check denominator inclusion, a regular monthly series, bounded forecast horizons, metric availability, and matching evaluation target counts. They do not establish date/source validity, threshold correctness, method-cohort equivalence, or emergence accuracy. The run emitted NumPy timedelta deprecation warnings.

Before treating outputs as publishable findings, review the matched sample, validate trend thresholds and forecast behavior across gaps, and record the analysis configuration with the results. More sophisticated models should follow evidence from the data and simple baselines.

## Public dashboard integration

The independent SkillScope dashboard consumes a sanitized publication. `tools/publish_dashboard.py` requires an explicit reviewed cohort CSV for empirical publication. Its monthly aggregation preserves a full calendar grid, with below-threshold and unobserved months marked as missing.

The public summary is intentionally separate from `trend_table()`: it compares two complete adjacent three-month windows and labels changes above +2 pp or below -2 pp, with an additional low-baseline persistence rule for emerging candidates. The Data & methods view explains the formula. These are screening summaries, not imported/validated research classifications.

Simple baseline outlooks are computed offline and persisted in the public snapshot, requiring 18 consecutive months with at least five jobs each. They use last-value or three-month-average candidates selected by the latest six one-step rolling-origin errors. Filtering outside the published date/source scope hides the forecast instead of reusing an incompatible result. These are exploratory consumer baselines; they do not expose the research page's Random Forest predictions or claim three-step validated accuracy. Integrating reviewed component-specific model outputs remains future work.

The existing five research-component tests remain relevant to that code; dedicated `test_public_dashboard.py` regressions and `browser_public_dashboard.py` checks cover the new public boundary and its calendar, filtering, export, and forecast behavior.

The [implementation roadmap](roadmap.md) schedules the research calendar and cohort fixes before further forecasting work.
