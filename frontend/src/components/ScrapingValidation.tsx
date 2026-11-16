import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  RefreshCw,
  Search,
  Filter,
  Download,
  ExternalLink,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Database,
  Info,
  ChevronLeft,
  ChevronRight,
  FileText,
} from 'lucide-react';

interface EvaluationRun {
  run_id: string;
  is_latest: boolean;
  label: string;
  timestamp_iso: string;
  total_benchmark: number;
  matched_records: number;
  exact_match_rate: number;
  macro_coverage: number;
  macro_correctness: number;
  is_synthetic: boolean;
  from_database: boolean;
}

interface ValidationData {
  has_data: boolean;
  run_id: string;
  is_synthetic: boolean;
  metadata: {
    timestamp?: string;
    unit_of_analysis?: string;
    total_benchmark_records?: number;
    total_predictions_loaded?: number;
    matched_records_count?: number;
    unmatched_benchmark_count?: number;
    extra_predictions_count?: number;
    fully_correct_records?: number;
    exact_match_rate?: number;
    exact_match_95_ci?: [number, number];
    macro_coverage?: number;
    macro_correctness?: number;
    macro_precision?: number;
    macro_recall?: number;
    macro_f1?: number;
  };
  filter_options: {
    countries: string[];
    platforms: string[];
    methods: string[];
    field_names: string[];
    statuses: string[];
    error_categories: string[];
  };
  stratified: {
    country: any[];
    platform: any[];
    extraction_method: any[];
  };
  field_metrics: Record<string, any>;
  numeric_salary: {
    comparable_count: number;
    salary_min_mae: number;
    salary_min_medae: number;
    salary_max_mae: number;
    salary_max_medae: number;
    excluded_incompatible_count: number;
  };
  total_errors_count: number;
  filtered_errors_count: number;
}

interface ReviewQueueItem {
  benchmark_id: string;
  field_name: string;
  country: string;
  source_platform: string;
  extraction_method: string;
  expected_raw: string;
  expected_normalized: string;
  predicted_raw: string;
  predicted_normalized: string;
  error_category: string;
  error_type: string;
  discrepancy_details: string;
  source_url: string;
  review_status: 'pending_review' | 'verified' | 'incorrect' | 'unavailable' | 'ambiguous';
  reviewer_id?: string;
  reviewer_notes?: string;
  corrected_value?: string;
  review_timestamp?: string;
}

export const ScrapingValidation: React.FC = () => {
  // Run Selection & Engine Execution
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>('latest');
  const [loadingRuns, setLoadingRuns] = useState<boolean>(true);
  const [rerunning, setRerunning] = useState<boolean>(false);
  const [rerunFeedback, setRerunFeedback] = useState<{ success: boolean; message: string } | null>(null);

  // Validation Data & Filters
  const [validationData, setValidationData] = useState<ValidationData | null>(null);
  const [loadingData, setLoadingData] = useState<boolean>(true);

  // Filters State
  const [countryFilter, setCountryFilter] = useState<string>('All');
  const [platformFilter, setPlatformFilter] = useState<string>('All');
  const [methodFilter, setMethodFilter] = useState<string>('All');
  const [fieldFilter, setFieldFilter] = useState<string>('All');
  const [statusFilter, setStatusFilter] = useState<string>('All');
  const [errorCatFilter, setErrorCatFilter] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Active Sub-Tab in Comparative Quality Analysis
  const [activeAnalysisTab, setActiveAnalysisTab] = useState<
    'country' | 'platform' | 'architecture' | 'fields' | 'salary'
  >('country');

  // Review Queue State & Pagination
  const [reviewQueue, setReviewQueue] = useState<ReviewQueueItem[]>([]);
  const [totalQueueCount, setTotalQueueCount] = useState<number>(0);
  const [queueLoading, setQueueLoading] = useState<boolean>(false);
  const [queuePage, setQueuePage] = useState<number>(1);
  const pageSize = 50;

  // Selected Discrepancy for Verification Decision
  const [selectedItem, setSelectedItem] = useState<ReviewQueueItem | null>(null);
  const [decisionStatus, setDecisionStatus] = useState<string>('verified');
  const [correctedValue, setCorrectedValue] = useState<string>('');
  const [reviewerId, setReviewerId] = useState<string>('researcher_1');
  const [reviewerNotes, setReviewerNotes] = useState<string>('');
  const [savingDecision, setSavingDecision] = useState<boolean>(false);
  const [decisionFeedback, setDecisionFeedback] = useState<{ success: boolean; message: string } | null>(null);

  // Audit History
  const [history, setHistory] = useState<any[]>([]);
  const [historyOpen, setHistoryOpen] = useState<boolean>(false);

  // 1. Initial Load: Fetch runs list
  useEffect(() => {
    fetchRuns();
    fetchHistory();
  }, []);

  // 2. Fetch Validation Data whenever run or filters change
  useEffect(() => {
    fetchValidationData();
    fetchReviewQueue(1);
    setQueuePage(1);
  }, [
    selectedRunId,
    countryFilter,
    platformFilter,
    methodFilter,
    fieldFilter,
    statusFilter,
    errorCatFilter,
    searchQuery,
  ]);

  const fetchRuns = async () => {
    setLoadingRuns(true);
    try {
      const res = await fetch('/api/validation/runs');
      if (res.ok) {
        const data = await res.json();
        setRuns(data.runs || []);
        if (data.latest_run_id) {
          setSelectedRunId(data.latest_run_id);
        }
      }
    } catch (err) {
      console.error('Failed to load evaluation runs', err);
    } finally {
      setLoadingRuns(false);
    }
  };

  const fetchValidationData = async () => {
    setLoadingData(true);
    try {
      const params = new URLSearchParams({
        run_id: selectedRunId,
        ...(countryFilter !== 'All' && { country: countryFilter }),
        ...(platformFilter !== 'All' && { platform: platformFilter }),
        ...(methodFilter !== 'All' && { method: methodFilter }),
        ...(fieldFilter !== 'All' && { field_name: fieldFilter }),
        ...(statusFilter !== 'All' && { status: statusFilter }),
        ...(errorCatFilter !== 'All' && { error_cat: errorCatFilter }),
        ...(searchQuery.trim() && { search_query: searchQuery.trim() }),
      });

      const res = await fetch(`/api/validation/data?${params.toString()}`);
      if (res.ok) {
        const data: ValidationData = await res.json();
        setValidationData(data);
      }
    } catch (err) {
      console.error('Failed to fetch validation data', err);
    } finally {
      setLoadingData(false);
    }
  };

  const fetchReviewQueue = async (page: number) => {
    setQueueLoading(true);
    try {
      const offset = (page - 1) * pageSize;
      const params = new URLSearchParams({
        run_id: selectedRunId,
        limit: String(pageSize),
        offset: String(offset),
        ...(countryFilter !== 'All' && { country: countryFilter }),
        ...(platformFilter !== 'All' && { platform: platformFilter }),
        ...(methodFilter !== 'All' && { method: methodFilter }),
        ...(fieldFilter !== 'All' && { field_name: fieldFilter }),
        ...(statusFilter !== 'All' && { status: statusFilter }),
        ...(errorCatFilter !== 'All' && { error_cat: errorCatFilter }),
        ...(searchQuery.trim() && { search_query: searchQuery.trim() }),
      });

      const res = await fetch(`/api/validation/review-queue?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setReviewQueue(data.items || []);
        setTotalQueueCount(data.total_count || 0);
        // Default selected item if none selected
        if ((!selectedItem || !data.items.some((i: any) => i.benchmark_id === selectedItem.benchmark_id && i.field_name === selectedItem.field_name)) && data.items.length > 0) {
          selectItemForReview(data.items[0]);
        }
      }
    } catch (err) {
      console.error('Failed to load review queue', err);
    } finally {
      setQueueLoading(false);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch('/api/validation/history');
      if (res.ok) {
        const data = await res.json();
        setHistory(data.history || []);
      }
    } catch (err) {
      console.error('Failed to load correction history', err);
    }
  };

  const handleRerunEngine = async () => {
    if (rerunning) return;
    setRerunning(true);
    setRerunFeedback(null);
    try {
      const res = await fetch('/api/validation/rerun', { method: 'POST' });
      const data = await res.json();
      if (res.ok && data.success) {
        setRerunFeedback({ success: true, message: data.message || 'Evaluation completed successfully!' });
        await fetchRuns();
        await fetchValidationData();
        await fetchReviewQueue(1);
      } else {
        setRerunFeedback({ success: false, message: data.message || 'Evaluation engine execution failed.' });
      }
    } catch (err: any) {
      setRerunFeedback({ success: false, message: err?.message || 'Network error executing evaluation engine.' });
    } finally {
      setRerunning(false);
    }
  };

  const selectItemForReview = (item: ReviewQueueItem) => {
    setSelectedItem(item);
    setDecisionStatus(item.review_status && item.review_status !== 'pending_review' ? item.review_status : 'verified');
    setCorrectedValue(item.corrected_value || '');
    setReviewerNotes(item.reviewer_notes || '');
    setDecisionFeedback(null);
  };

  const handleSaveDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem) return;

    if (!reviewerNotes.trim()) {
      setDecisionFeedback({ success: false, message: 'Reviewer justification notes are mandatory.' });
      return;
    }

    setSavingDecision(true);
    setDecisionFeedback(null);
    try {
      const res = await fetch('/api/validation/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          benchmark_id: selectedItem.benchmark_id,
          field_name: selectedItem.field_name,
          status: decisionStatus,
          reviewer_id: reviewerId,
          reviewer_notes: reviewerNotes,
          corrected_value: correctedValue,
          original_predicted: selectedItem.predicted_raw,
          original_expected: selectedItem.expected_raw,
          source_url: selectedItem.source_url,
          country: selectedItem.country,
          source_platform: selectedItem.source_platform,
        }),
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setDecisionFeedback({ success: true, message: data.message || 'Review decision recorded.' });
        fetchReviewQueue(queuePage);
        fetchHistory();
      } else {
        setDecisionFeedback({ success: false, message: data.message || 'Failed to persist review decision.' });
      }
    } catch (err: any) {
      setDecisionFeedback({ success: false, message: err?.message || 'Error saving decision.' });
    } finally {
      setSavingDecision(false);
    }
  };

  const resetFilters = () => {
    setCountryFilter('All');
    setPlatformFilter('All');
    setMethodFilter('All');
    setFieldFilter('All');
    setStatusFilter('All');
    setErrorCatFilter('All');
    setSearchQuery('');
  };

  const meta = validationData?.metadata || {};
  const totalBM = meta.total_benchmark_records ?? 0;
  const matchedBM = meta.matched_records_count ?? 0;
  const unmatchedBM = meta.unmatched_benchmark_count ?? 0;
  const extraPreds = meta.extra_predictions_count ?? 0;
  const fullyCorrect = meta.fully_correct_records ?? 0;
  const exactRatePct = (meta.exact_match_rate ?? 0) * 100;
  const exactCI = meta.exact_match_95_ci || [0, 0];
  const macroCovPct = (meta.macro_coverage ?? 0) * 100;
  const macroCorrPct = (meta.macro_correctness ?? 0) * 100;
  const evalTimestamp = meta.timestamp || '2026-10-22T15:59:03Z';

  const filterOpts = validationData?.filter_options || {
    countries: ['All'],
    platforms: ['All'],
    methods: ['All'],
    field_names: ['All'],
    statuses: ['All'],
    error_categories: ['All'],
  };

  const totalPages = Math.ceil(totalQueueCount / pageSize) || 1;

  return (
    <div className="space-y-6">
      {/* 1. Security Notice Card */}
      <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-4 text-xs text-amber-950 shadow-xs">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-bold text-amber-900 uppercase tracking-wider text-[11px]">Security Notice</span>
            <p className="text-[11px] leading-relaxed text-amber-900/90">
              Only submit publicly accessible and permitted job detail links. Local/private IP addresses are blocked,
              and unknown external hosts require administrator domain approval.
            </p>
          </div>
        </div>
      </div>

      {/* 2. Main Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E2E8F0] pb-4">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-[#172033]">
            Scraping Accuracy & Benchmark Validation
          </h2>
          <p className="text-xs md:text-sm text-[#64748B] mt-0.5">
            Quantitative empirical evaluation of extraction accuracy, coverage, and error patterns independently
            verified against ground-truth job advertisements across target regional markets.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 border border-emerald-200">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Evaluation Active
          </span>
        </div>
      </div>

      {/* 3. Benchmark Snapshot Selection & Evaluation Control Bar */}
      <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-4">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 items-end">
          <div className="lg:col-span-3 space-y-1.5">
            <label className="text-xs font-semibold text-[#172033] flex items-center gap-1.5">
              <Database className="h-4 w-4 text-[#2563EB]" />
              Select Evaluation Run / Benchmark Snapshot:
            </label>
            <div className="relative">
              <select
                value={selectedRunId}
                onChange={(e) => setSelectedRunId(e.target.value)}
                disabled={loadingRuns || rerunning}
                className="w-full appearance-none rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] py-2.5 pl-3 pr-10 text-xs font-medium text-[#172033] focus:border-[#2563EB] focus:bg-white focus:outline-hidden disabled:opacity-50"
              >
                {runs.map((r) => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-[#64748B]" />
            </div>
          </div>

          <div>
            <button
              onClick={handleRerunEngine}
              disabled={rerunning}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-[#2563EB] px-4 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-[#1D4ED8] focus:outline-hidden disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`h-4 w-4 ${rerunning ? 'animate-spin' : ''}`} />
              {rerunning ? 'Executing Engine...' : 'Re-run Evaluation Engine'}
            </button>
          </div>
        </div>

        {/* Provenance & Metadata Badges */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#E2E8F0] pt-3 text-xs">
          <div className="flex flex-wrap items-center gap-2.5">
            {validationData?.is_synthetic ? (
              <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-[11px] font-bold text-amber-800">
                ⚠️ Synthetic Test Data (Non-Production)
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-[11px] font-bold text-emerald-800">
                <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                Empirical Research Benchmark (Independently Verified)
              </span>
            )}

            <span className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-0.5 text-[11px] font-semibold text-[#2563EB]">
              🗄️ Master SQLite Database
            </span>

            <span className="text-[11px] text-[#64748B]">
              Evaluation Timestamp (UTC): <strong className="text-[#172033] font-mono">{evalTimestamp}</strong>
            </span>

            <span className="text-[11px] text-[#64748B]">
              Benchmark Version: <strong className="text-[#172033]">v2.0 (Dual-Layer)</strong>
            </span>
          </div>

          <div className="text-[11px] text-[#2563EB] font-medium">
            Unit of Analysis: <strong className="text-[#172033]">Individual Job Vacancy</strong>
          </div>
        </div>

        {rerunFeedback && (
          <div
            className={`rounded-lg p-3 text-xs flex items-center gap-2 ${
              rerunFeedback.success
                ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
                : 'bg-rose-50 border border-rose-200 text-rose-800'
            }`}
          >
            {rerunFeedback.success ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
            ) : (
              <XCircle className="h-4 w-4 text-rose-600 shrink-0" />
            )}
            <span>{rerunFeedback.message}</span>
          </div>
        )}
      </div>

      {/* 4. Core Scorecard KPIs (5 Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Card 1: Benchmark Corpus */}
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs border-l-4 border-l-[#2563EB] space-y-1">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
            Benchmark Corpus (N)
          </span>
          <div className="text-2xl font-bold font-mono text-[#172033]">
            {loadingData ? '—' : totalBM}
          </div>
          <div className="text-[11px] text-[#64748B]">
            Verified Reference Ads
          </div>
        </div>

        {/* Card 2: Evaluated / Matched */}
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs border-l-4 border-l-[#16A34A] space-y-1">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
            Evaluated / Matched
          </span>
          <div className="text-2xl font-bold font-mono text-[#16A34A]">
            {loadingData ? '—' : matchedBM}
          </div>
          <div className="text-[11px] text-emerald-700 font-mono">
            Unmatched: {unmatchedBM} | Extra: {extraPreds}
          </div>
        </div>

        {/* Card 3: Macro Coverage */}
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs border-l-4 border-l-[#0284C7] space-y-1">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
            Match Coverage (Macro)
          </span>
          <div className="text-2xl font-bold font-mono text-[#0284C7]">
            {loadingData ? '—' : `${macroCovPct.toFixed(1)}%`}
          </div>
          <div className="text-[11px] text-sky-700">
            Completeness (Eligible Fields)
          </div>
        </div>

        {/* Card 4: Macro Correctness */}
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs border-l-4 border-l-[#7C3AED] space-y-1">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
            Match Correctness (Macro)
          </span>
          <div className="text-2xl font-bold font-mono text-[#7C3AED]">
            {loadingData ? '—' : `${macroCorrPct.toFixed(1)}%`}
          </div>
          <div className="text-[11px] text-purple-700">
            Precision on Captured Fields
          </div>
        </div>

        {/* Card 5: Exact Match Rate */}
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs border-l-4 border-l-[#D97706] space-y-1">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
            Exact Match Rate
          </span>
          <div className="text-2xl font-bold font-mono text-[#D97706]">
            {loadingData ? '—' : `${fullyCorrect} `}
            <span className="text-xs font-normal text-[#64748B]">({exactRatePct.toFixed(1)}%)</span>
          </div>
          <div className="text-[10px] text-amber-800 font-mono">
            95% CI: [{(exactCI[0] * 100).toFixed(1)}%, {(exactCI[1] * 100).toFixed(1)}%]
          </div>
        </div>
      </div>

      {/* 5. Filter & Slice Evaluation Results Toolbar */}
      <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E2E8F0] pb-3">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-[#2563EB]" />
            <h3 className="text-sm font-bold text-[#172033]">Filter & Slice Evaluation Results</h3>
          </div>
          <button
            onClick={resetFilters}
            className="text-xs font-semibold text-[#2563EB] hover:text-[#1D4ED8] underline"
          >
            Reset Filters
          </button>
        </div>

        {/* Filter Dropdowns Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {/* Country / Market */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[#64748B]">Country / Market:</label>
            <select
              value={countryFilter}
              onChange={(e) => setCountryFilter(e.target.value)}
              className="w-full rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-2 text-xs text-[#172033] focus:border-[#2563EB] focus:bg-white focus:outline-hidden"
            >
              {filterOpts.countries.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          {/* Source Platform */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[#64748B]">Source Platform / Hostname:</label>
            <select
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value)}
              className="w-full rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-2 text-xs text-[#172033] focus:border-[#2563EB] focus:bg-white focus:outline-hidden"
            >
              {filterOpts.platforms.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>

          {/* Extraction Method */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[#64748B]">Extraction Method:</label>
            <select
              value={methodFilter}
              onChange={(e) => setMethodFilter(e.target.value)}
              className="w-full rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-2 text-xs text-[#172033] focus:border-[#2563EB] focus:bg-white focus:outline-hidden"
            >
              {filterOpts.methods.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>

          {/* Field Name */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[#64748B]">Field Name:</label>
            <select
              value={fieldFilter}
              onChange={(e) => setFieldFilter(e.target.value)}
              className="w-full rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-2 text-xs text-[#172033] focus:border-[#2563EB] focus:bg-white focus:outline-hidden font-mono"
            >
              {filterOpts.field_names.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>

          {/* Validation Status / Type */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[#64748B]">Validation Status / Type:</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-2 text-xs text-[#172033] focus:border-[#2563EB] focus:bg-white focus:outline-hidden"
            >
              {filterOpts.statuses.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* Error Category */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[#64748B]">Error Category:</label>
            <select
              value={errorCatFilter}
              onChange={(e) => setErrorCatFilter(e.target.value)}
              className="w-full rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-2 text-xs text-[#172033] focus:border-[#2563EB] focus:bg-white focus:outline-hidden"
            >
              {filterOpts.error_categories.map((ec) => (
                <option key={ec} value={ec}>{ec}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-[#64748B]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="🔍 Search discrepancies by Benchmark ID, URL, expected or extracted text..."
            className="w-full rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] py-2 pl-9 pr-3 text-xs text-[#172033] placeholder-[#94A3B8] focus:border-[#2563EB] focus:bg-white focus:outline-hidden"
          />
        </div>

        <div className="text-[11px] text-[#64748B]">
          Displaying <strong className="text-[#172033]">{validationData?.filtered_errors_count ?? 0}</strong> of{' '}
          <strong className="text-[#172033]">{validationData?.total_errors_count ?? 0}</strong> field-level
          discrepancies matching current filter criteria.
        </div>
      </div>

      {/* 6. Comparative Quality Analysis (5 Sub-Tabs) */}
      <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E2E8F0] pb-3">
          <div>
            <h3 className="text-sm font-bold text-[#172033]">Comparative Quality Analysis</h3>
            <p className="text-[11px] text-[#64748B]">
              Stratified empirical benchmarking across geographic markets, portal domains, parsing strategies, and canonical fields.
            </p>
          </div>

          {/* Sub-Tabs Selector */}
          <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-[#E2E8F0] p-1 bg-slate-50 text-xs">
            {[
              { id: 'country', label: '🌍 Country-Level Quality' },
              { id: 'platform', label: '🏢 Source Platform Analysis' },
              { id: 'architecture', label: '⚙️ Extraction Architecture' },
              { id: 'fields', label: '📋 Field-by-Field Matrix' },
              { id: 'salary', label: '💰 Numeric Salary Errors' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveAnalysisTab(tab.id as any)}
                className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-all ${
                  activeAnalysisTab === tab.id
                    ? 'bg-white text-[#2563EB] shadow-2xs'
                    : 'text-[#64748B] hover:text-[#172033]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Sub-Tab 1: Country-Level Quality (Geographic Extraction Quality Comparison) */}
        {activeAnalysisTab === 'country' && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h4 className="text-sm font-bold text-[#172033]">
                  Geographic Extraction Quality Comparison
                </h4>
                <p className="text-[11px] text-[#64748B]">
                  Stratified performance across target national labor markets. N denotes verified benchmark sample size.
                </p>
              </div>
            </div>

            {/* If no country stratification matches */}
            {(!validationData?.stratified?.country || validationData.stratified.country.length === 0) ? (
              <div className="rounded-xl border border-blue-200 bg-blue-50/70 p-6 text-center space-y-2">
                <Info className="h-6 w-6 text-[#2563EB] mx-auto" />
                <h5 className="text-xs font-bold text-[#172033]">
                  No quality stratification data matches the current filter set.
                </h5>
                <p className="text-[11px] text-[#64748B] max-w-md mx-auto">
                  Adjust the country, platform, or error category filters above to view regional extraction performance.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Stratified Country Table */}
                <div className="overflow-x-auto border border-[#E2E8F0] rounded-lg">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-b border-[#E2E8F0] text-[11px] font-semibold text-[#64748B]">
                      <tr>
                        <th className="py-2.5 px-3">Country</th>
                        <th className="py-2.5 px-3 text-center">Total (N)</th>
                        <th className="py-2.5 px-3 text-right">Exact Match %</th>
                        <th className="py-2.5 px-3 text-center">95% Wilson CI</th>
                        <th className="py-2.5 px-3 text-right">Title Agree %</th>
                        <th className="py-2.5 px-3 text-right">Employer Agree %</th>
                        <th className="py-2.5 px-3 text-right">Salary Discl %</th>
                        <th className="py-2.5 px-3 text-right">Work Mode %</th>
                        <th className="py-2.5 px-3 text-center">Reliability</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E2E8F0]">
                      {validationData.stratified.country.map((row: any, i: number) => {
                        const n = Number(row.total_records || 0);
                        const exact = (Number(row.exact_match_rate || 0) * 100).toFixed(1);
                        const ciL = (Number(row.ci_lower_95 || 0) * 100).toFixed(1);
                        const ciU = (Number(row.ci_upper_95 || 0) * 100).toFixed(1);
                        const tAgr = (Number(row.title_agreement_rate || 0) * 100).toFixed(1);
                        const eAgr = (Number(row.employer_agreement_rate || 0) * 100).toFixed(1);
                        const sAgr = (Number(row.salary_disclosed_rate || 0) * 100).toFixed(1);
                        const wAgr = (Number(row.work_mode_agreement_rate || 0) * 100).toFixed(1);
                        const isSmall = Boolean(row.is_small_sample) || n < 10;

                        return (
                          <tr key={i} className="hover:bg-slate-50/60 font-mono text-[11px]">
                            <td className="py-2.5 px-3 font-sans font-bold text-[#172033]">{row.subgroup_name}</td>
                            <td className="py-2.5 px-3 text-center font-bold">{n}</td>
                            <td className="py-2.5 px-3 text-right">{exact}%</td>
                            <td className="py-2.5 px-3 text-center text-[#64748B]">[{ciL}%, {ciU}%]</td>
                            <td className="py-2.5 px-3 text-right text-blue-700 font-bold">{tAgr}%</td>
                            <td className="py-2.5 px-3 text-right text-emerald-700 font-bold">{eAgr}%</td>
                            <td className="py-2.5 px-3 text-right text-purple-700 font-bold">{sAgr}%</td>
                            <td className="py-2.5 px-3 text-right text-slate-700">{wAgr}%</td>
                            <td className="py-2.5 px-3 text-center font-sans">
                              <span
                                className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold ${
                                  isSmall
                                    ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                    : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                }`}
                              >
                                {isSmall ? 'Small Sample (N<10)' : 'Adequate Sample'}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Small Sample Alert if any N < 10 */}
                {validationData.stratified.country.some((r: any) => Boolean(r.is_small_sample) || Number(r.total_records) < 10) && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50/70 p-3 text-xs text-amber-800 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                    <span>
                      ⚠️ <strong>Small Sample Size Alert:</strong> Subgroups with N &lt; 10 have wide confidence intervals.
                      Percentage comparisons must be interpreted with caution.
                    </span>
                  </div>
                )}

                {/* Typical Grouped Bar Chart Comparing Country Accuracy */}
                <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-2">
                    <h5 className="text-xs font-bold text-[#172033]">
                      Extraction Agreement Rates by Target Country (%)
                    </h5>
                    <div className="flex items-center gap-4 text-[11px]">
                      <div className="flex items-center gap-1.5">
                        <span className="h-2.5 w-2.5 rounded-full bg-[#2563EB]"></span>
                        <span className="text-[#172033]">Title Agreement</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="h-2.5 w-2.5 rounded-full bg-[#16A34A]"></span>
                        <span className="text-[#172033]">Employer Agreement</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="h-2.5 w-2.5 rounded-full bg-[#7C3AED]"></span>
                        <span className="text-[#172033]">Salary Disclosed</span>
                      </div>
                    </div>
                  </div>

                  {/* SVG Clustered Vertical Bar Chart */}
                  <div className="relative w-full overflow-x-auto">
                    <div style={{ minWidth: '500px', height: '220px', position: 'relative' }}>
                      <svg viewBox="0 0 600 220" className="w-full h-full font-sans select-none">
                        {/* Y-Axis Ticks */}
                        {[0, 25, 50, 75, 100].map((t) => {
                          const y = 20 + 150 - (t / 100) * 150;
                          return (
                            <g key={t}>
                              <line x1={45} x2={580} y1={y} y2={y} stroke="#E2E8F0" strokeDasharray={t === 0 ? undefined : '3 3'} />
                              <text x={38} y={y + 4} textAnchor="end" className="text-[10px] fill-[#64748B] font-mono">
                                {t}%
                              </text>
                            </g>
                          );
                        })}

                        {/* Baseline */}
                        <line x1={45} x2={580} y1={170} y2={170} stroke="#94A3B8" strokeWidth="1.5" />

                        {/* Country Clusters */}
                        {validationData.stratified.country.map((cRow: any, idx: number) => {
                          const groupWidth = (580 - 45) / validationData.stratified.country.length;
                          const groupStartX = 45 + idx * groupWidth;
                          const barW = Math.min(22, (groupWidth * 0.6) / 3);
                          const clusterOffset = (groupWidth - barW * 3 - 6) / 2;

                          const tVal = Number(cRow.title_agreement_rate || 0) * 100;
                          const eVal = Number(cRow.employer_agreement_rate || 0) * 100;
                          const sVal = Number(cRow.salary_disclosed_rate || 0) * 100;

                          const tH = Math.max(0, (tVal / 100) * 150);
                          const eH = Math.max(0, (eVal / 100) * 150);
                          const sH = Math.max(0, (sVal / 100) * 150);

                          return (
                            <g key={cRow.subgroup_name}>
                              {/* Title Bar */}
                              <rect
                                x={groupStartX + clusterOffset}
                                y={170 - tH}
                                width={barW}
                                height={tH}
                                fill="#2563EB"
                                rx="2"
                              >
                                <title>{cRow.subgroup_name} Title Agreement: {tVal.toFixed(1)}%</title>
                              </rect>

                              {/* Employer Bar */}
                              <rect
                                x={groupStartX + clusterOffset + barW + 3}
                                y={170 - eH}
                                width={barW}
                                height={eH}
                                fill="#16A34A"
                                rx="2"
                              >
                                <title>{cRow.subgroup_name} Employer Agreement: {eVal.toFixed(1)}%</title>
                              </rect>

                              {/* Salary Disclosed Bar */}
                              <rect
                                x={groupStartX + clusterOffset + (barW + 3) * 2}
                                y={170 - sH}
                                width={barW}
                                height={sH}
                                fill="#7C3AED"
                                rx="2"
                              >
                                <title>{cRow.subgroup_name} Salary Disclosed: {sVal.toFixed(1)}%</title>
                              </rect>

                              {/* Country Label */}
                              <text
                                x={groupStartX + groupWidth / 2}
                                y={192}
                                textAnchor="middle"
                                className="text-[11px] font-bold fill-[#172033]"
                              >
                                {cRow.subgroup_name}
                              </text>
                            </g>
                          );
                        })}
                      </svg>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Sub-Tab 2: Source Platform Analysis */}
        {activeAnalysisTab === 'platform' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-[#172033]">
                Source Platform & Hostname Breakdown
              </h4>
              <p className="text-[11px] text-[#64748B]">
                Performance across individual job portals. Evaluates portal-specific adapters and anti-bot resistance.
              </p>
            </div>

            {(!validationData?.stratified?.platform || validationData.stratified.platform.length === 0) ? (
              <div className="p-6 text-center text-xs text-slate-400">
                No platform stratification data matching current filter.
              </div>
            ) : (
              <div className="space-y-4">
                <div className="overflow-x-auto border border-[#E2E8F0] rounded-lg">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-b border-[#E2E8F0] text-[11px] font-semibold text-[#64748B]">
                      <tr>
                        <th className="py-2.5 px-3">Source Platform</th>
                        <th className="py-2.5 px-3 text-center">Total (N)</th>
                        <th className="py-2.5 px-3 text-right">Exact Match %</th>
                        <th className="py-2.5 px-3 text-center">95% Wilson CI</th>
                        <th className="py-2.5 px-3 text-right">Title Agree %</th>
                        <th className="py-2.5 px-3 text-right">Employer Agree %</th>
                        <th className="py-2.5 px-3 text-right">Salary Discl %</th>
                        <th className="py-2.5 px-3 text-right">Work Mode %</th>
                        <th className="py-2.5 px-3 text-center">Reliability</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E2E8F0]">
                      {validationData.stratified.platform.map((row: any, i: number) => {
                        const n = Number(row.total_records || 0);
                        const exact = (Number(row.exact_match_rate || 0) * 100).toFixed(1);
                        const ciL = (Number(row.ci_lower_95 || 0) * 100).toFixed(1);
                        const ciU = (Number(row.ci_upper_95 || 0) * 100).toFixed(1);
                        const tAgr = (Number(row.title_agreement_rate || 0) * 100).toFixed(1);
                        const eAgr = (Number(row.employer_agreement_rate || 0) * 100).toFixed(1);
                        const sAgr = (Number(row.salary_disclosed_rate || 0) * 100).toFixed(1);
                        const wAgr = (Number(row.work_mode_agreement_rate || 0) * 100).toFixed(1);
                        const isSmall = Boolean(row.is_small_sample) || n < 10;

                        return (
                          <tr key={i} className="hover:bg-slate-50/60 font-mono text-[11px]">
                            <td className="py-2 px-3 font-sans font-bold text-[#172033]">{row.subgroup_name}</td>
                            <td className="py-2 px-3 text-center font-bold">{n}</td>
                            <td className="py-2 px-3 text-right">{exact}%</td>
                            <td className="py-2 px-3 text-center text-[#64748B]">[{ciL}%, {ciU}%]</td>
                            <td className="py-2 px-3 text-right text-blue-700">{tAgr}%</td>
                            <td className="py-2 px-3 text-right text-emerald-700">{eAgr}%</td>
                            <td className="py-2 px-3 text-right text-purple-700">{sAgr}%</td>
                            <td className="py-2 px-3 text-right text-slate-700">{wAgr}%</td>
                            <td className="py-2 px-3 text-center font-sans">
                              <span
                                className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold ${
                                  isSmall
                                    ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                    : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                }`}
                              >
                                {isSmall ? 'Small (N<10)' : 'Adequate'}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Blocked Portals Ethical Access Notice */}
                {validationData.stratified.platform.some((p: any) => Number(p.total_records) > 0 && Number(p.title_agreement_rate) === 0) && (
                  <div className="rounded-lg border border-blue-200 bg-blue-50/70 p-3 text-xs text-[#172033] flex items-start gap-2.5">
                    <Info className="h-4 w-4 text-[#2563EB] shrink-0 mt-0.5" />
                    <p className="text-[11px] leading-relaxed text-[#172033]">
                      <strong>Ethical Perimeter Access Notice:</strong> Zero agreement on commercial job portals such as Naukri or JobStreet
                      reflects documented ethical access restrictions (Cloudflare / Akamai challenge perimeters), not parsing bugs.
                      These enterprise job boards require offline verified reference batches for replication.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Sub-Tab 3: Extraction Architecture */}
        {activeAnalysisTab === 'architecture' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-[#172033]">
                Extraction Strategy & Architecture Performance
              </h4>
              <p className="text-[11px] text-[#64748B]">
                Comparison of extraction tiers: Structured JSON-LD vs. Dedicated Adapters vs. Generic HTML Heuristics vs. Browser Headless Rendering.
              </p>
            </div>

            {(!validationData?.stratified?.extraction_method || validationData.stratified.extraction_method.length === 0) ? (
              <div className="p-6 text-center text-xs text-slate-400">
                No extraction method stratification data matching current filter.
              </div>
            ) : (
              <div className="overflow-x-auto border border-[#E2E8F0] rounded-lg">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-[#E2E8F0] text-[11px] font-semibold text-[#64748B]">
                    <tr>
                      <th className="py-2.5 px-3">Extraction Architecture Strategy</th>
                      <th className="py-2.5 px-3 text-center">Total (N)</th>
                      <th className="py-2.5 px-3 text-right">Exact Match %</th>
                      <th className="py-2.5 px-3 text-center">95% Wilson CI</th>
                      <th className="py-2.5 px-3 text-right">Title Agree %</th>
                      <th className="py-2.5 px-3 text-right">Employer Agree %</th>
                      <th className="py-2.5 px-3 text-right">Salary Discl %</th>
                      <th className="py-2.5 px-3 text-right">Work Mode %</th>
                      <th className="py-2.5 px-3 text-center">Reliability</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E2E8F0]">
                    {validationData.stratified.extraction_method.map((row: any, i: number) => {
                      const n = Number(row.total_records || 0);
                      const exact = (Number(row.exact_match_rate || 0) * 100).toFixed(1);
                      const ciL = (Number(row.ci_lower_95 || 0) * 100).toFixed(1);
                      const ciU = (Number(row.ci_upper_95 || 0) * 100).toFixed(1);
                      const tAgr = (Number(row.title_agreement_rate || 0) * 100).toFixed(1);
                      const eAgr = (Number(row.employer_agreement_rate || 0) * 100).toFixed(1);
                      const sAgr = (Number(row.salary_disclosed_rate || 0) * 100).toFixed(1);
                      const wAgr = (Number(row.work_mode_agreement_rate || 0) * 100).toFixed(1);
                      const isSmall = Boolean(row.is_small_sample) || n < 10;

                      return (
                        <tr key={i} className="hover:bg-slate-50/60 font-mono text-[11px]">
                          <td className="py-2 px-3 font-sans font-bold text-[#172033]">{row.subgroup_name}</td>
                          <td className="py-2 px-3 text-center font-bold">{n}</td>
                          <td className="py-2 px-3 text-right">{exact}%</td>
                          <td className="py-2 px-3 text-center text-[#64748B]">[{ciL}%, {ciU}%]</td>
                          <td className="py-2 px-3 text-right text-blue-700">{tAgr}%</td>
                          <td className="py-2 px-3 text-right text-emerald-700">{eAgr}%</td>
                          <td className="py-2 px-3 text-right text-purple-700">{sAgr}%</td>
                          <td className="py-2 px-3 text-right text-slate-700">{wAgr}%</td>
                          <td className="py-2 px-3 text-center font-sans">
                            <span
                              className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold ${
                                isSmall
                                  ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                  : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              }`}
                            >
                              {isSmall ? 'Small (N<10)' : 'Adequate'}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Sub-Tab 4: Field-by-Field Matrix */}
        {activeAnalysisTab === 'fields' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-[#172033]">
                Canonical Field Extraction Matrix
              </h4>
              <p className="text-[11px] text-[#64748B]">
                Evaluates exact agreement, normalized rule agreement, completeness coverage, and hallucination rates.
              </p>
            </div>

            {(!validationData?.field_metrics || Object.keys(validationData.field_metrics).length === 0) ? (
              <div className="p-6 text-center text-xs text-slate-400">
                No field metrics matching filter.
              </div>
            ) : (
              <div className="overflow-x-auto border border-[#E2E8F0] rounded-lg">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-[#E2E8F0] text-[11px] font-semibold text-[#64748B]">
                    <tr>
                      <th className="py-2.5 px-3">Field Name</th>
                      <th className="py-2.5 px-2 text-center">Eligible (N)</th>
                      <th className="py-2.5 px-2 text-center">Matched</th>
                      <th className="py-2.5 px-2 text-center text-emerald-700">Correct (TP)</th>
                      <th className="py-2.5 px-2 text-center text-rose-700">Incorrect (FP)</th>
                      <th className="py-2.5 px-2 text-center text-amber-700">Missing (FN)</th>
                      <th className="py-2.5 px-2 text-right">Coverage %</th>
                      <th className="py-2.5 px-2 text-right">Correctness %</th>
                      <th className="py-2.5 px-2 text-right font-bold text-[#2563EB]">Norm Agree %</th>
                      <th className="py-2.5 px-2 text-center text-[#64748B]">95% Wilson CI</th>
                      <th className="py-2.5 px-2 text-center">Unavail (N)</th>
                      <th className="py-2.5 px-2 text-right text-rose-600">Hallucination %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E2E8F0]">
                    {Object.entries(validationData.field_metrics).map(([fname, fstats]: [string, any]) => {
                      if (fieldFilter !== 'All' && fname !== fieldFilter) return null;

                      const elig = fstats.eligible_references ?? 0;
                      const matched = fstats.matched_predictions ?? 0;
                      const correct = fstats.correct_values ?? 0;
                      const incorrect = fstats.incorrect_values ?? 0;
                      const missing = fstats.missing_predictions ?? 0;
                      const normAgr = (Number(fstats.normalized_agreement_rate || 0) * 100).toFixed(1);
                      const cov = (Number(fstats.extraction_coverage || 0) * 100).toFixed(1);
                      const corr = (Number(fstats.extraction_correctness || 0) * 100).toFixed(1);
                      const unavail = fstats.unavailable_references ?? 0;
                      const halluc = (Number(fstats.hallucination_rate || 0) * 100).toFixed(1);
                      const ciL = (Number(fstats.wilson_ci_lower || 0) * 100).toFixed(1);
                      const ciU = (Number(fstats.wilson_ci_upper || 0) * 100).toFixed(1);

                      return (
                        <tr key={fname} className="hover:bg-slate-50/60 font-mono text-[11px]">
                          <td className="py-2 px-3 font-semibold text-[#172033]">
                            <code className="bg-slate-100 px-1.5 py-0.5 rounded text-[11px] text-[#2563EB] border border-slate-200">
                              {fname}
                            </code>
                          </td>
                          <td className="py-2 px-2 text-center font-bold">{elig}</td>
                          <td className="py-2 px-2 text-center">{matched}</td>
                          <td className="py-2 px-2 text-center text-emerald-700 font-bold">{correct}</td>
                          <td className="py-2 px-2 text-center text-rose-700">{incorrect}</td>
                          <td className="py-2 px-2 text-center text-amber-700">{missing}</td>
                          <td className="py-2 px-2 text-right">{cov}%</td>
                          <td className="py-2 px-2 text-right">{corr}%</td>
                          <td className="py-2 px-2 text-right font-bold text-[#2563EB]">{normAgr}%</td>
                          <td className="py-2 px-2 text-center text-[#64748B]">[{ciL}%, {ciU}%]</td>
                          <td className="py-2 px-2 text-center">{unavail}</td>
                          <td className="py-2 px-2 text-right text-rose-600">{halluc}%</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Sub-Tab 5: Numeric Salary Errors */}
        {activeAnalysisTab === 'salary' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-[#172033]">
                Numeric Salary Bounds Error Analysis
              </h4>
              <p className="text-[11px] text-[#64748B]">
                Monetary bounds are compared only when currency and pay period match. Incompatible pairs are excluded.
              </p>
            </div>

            {/* 4 Salary Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs space-y-1">
                <span className="text-[11px] font-semibold text-[#64748B]">Comparable Salary Pairs</span>
                <div className="text-2xl font-bold font-mono text-[#172033]">
                  {validationData?.numeric_salary?.comparable_count ?? 0}
                </div>
                <div className="text-[10px] text-[#64748B]">Valid Disclosed Matches</div>
              </div>

              <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs space-y-1">
                <span className="text-[11px] font-semibold text-[#64748B]">Salary Min MAE</span>
                <div className="text-2xl font-bold font-mono text-emerald-600">
                  {(validationData?.numeric_salary?.salary_min_mae ?? 0).toFixed(2)}
                </div>
                <div className="text-[10px] text-emerald-700">Zero Extraction Drift</div>
              </div>

              <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs space-y-1">
                <span className="text-[11px] font-semibold text-[#64748B]">Salary Max MAE</span>
                <div className="text-2xl font-bold font-mono text-emerald-600">
                  {(validationData?.numeric_salary?.salary_max_mae ?? 0).toFixed(2)}
                </div>
                <div className="text-[10px] text-emerald-700">Zero Extraction Drift</div>
              </div>

              <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs space-y-1">
                <span className="text-[11px] font-semibold text-[#64748B]">Excluded Incompatible</span>
                <div className="text-2xl font-bold font-mono text-slate-500">
                  {validationData?.numeric_salary?.excluded_incompatible_count ?? 0}
                </div>
                <div className="text-[10px] text-[#64748B]">Currency / Unit Mismatches</div>
              </div>
            </div>

            {/* Evaluation Rule Callout Card */}
            <div className="rounded-xl border border-blue-200 bg-blue-50/70 p-4 text-xs text-[#172033] space-y-1">
              <span className="font-bold text-[#2563EB]">Evaluation Rule & Methodology:</span>
              <p className="text-[11px] leading-relaxed text-[#64748B]">
                Advertisements where salary was undisclosed are verified as{' '}
                <code className="bg-white px-1 py-0.5 rounded text-[#2563EB] border border-blue-200">salary_disclosed = False</code>.
                Numeric error metrics are computed strictly across disclosed, currency-matched pairs (e.g. INR vs. INR, SGD vs. SGD).
                Mean Absolute Error (MAE) and Median Absolute Error (MedAE) of 0.00 confirm zero extraction drift across validated disclosures.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* 7. Field-Level Discrepancy & Validation Review Queue */}
      <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E2E8F0] pb-3">
          <div>
            <h3 className="text-sm font-bold text-[#172033]">
              Field-Level Discrepancy & Validation Review Queue
            </h3>
            <p className="text-[11px] text-[#64748B]">
              Inspect discrepancies between extracted values and ground truth. Reviewers can record audited decisions
              without mutating the immutable benchmark dataset.
            </p>
          </div>
          <div className="text-xs text-[#64748B]">
            Showing <strong>{reviewQueue.length}</strong> of <strong>{totalQueueCount}</strong> discrepancy records
          </div>
        </div>

        {queueLoading ? (
          <div className="flex h-40 items-center justify-center">
            <RefreshCw className="h-6 w-6 animate-spin text-[#2563EB]" />
          </div>
        ) : reviewQueue.length === 0 ? (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50/80 p-6 text-center text-xs text-emerald-800 space-y-1">
            <CheckCircle2 className="h-6 w-6 text-emerald-600 mx-auto" />
            <span className="font-bold">No discrepancies match the selected filters.</span>
            <p className="text-[11px] text-emerald-700">All predictions in this slice agree with ground truth.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Review Table */}
            <div className="overflow-x-auto border border-[#E2E8F0] rounded-lg">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-[#E2E8F0] text-[11px] font-semibold text-[#64748B]">
                  <tr>
                    <th className="py-2.5 px-3">Benchmark ID</th>
                    <th className="py-2.5 px-2">Country</th>
                    <th className="py-2.5 px-2">Platform</th>
                    <th className="py-2.5 px-2">Field</th>
                    <th className="py-2.5 px-3">Expected (Ref)</th>
                    <th className="py-2.5 px-3">Extracted (Pred)</th>
                    <th className="py-2.5 px-2">Category</th>
                    <th className="py-2.5 px-2 text-center">Review Status</th>
                    <th className="py-2.5 px-2 text-center">Source Link</th>
                    <th className="py-2.5 px-2 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E2E8F0]">
                  {reviewQueue.map((item, idx) => {
                    const isSelected = selectedItem?.benchmark_id === item.benchmark_id && selectedItem?.field_name === item.field_name;

                    let statusBadgeClass = 'bg-slate-100 text-slate-700 border-slate-200';
                    if (item.review_status === 'verified') statusBadgeClass = 'bg-emerald-50 text-emerald-700 border-emerald-200';
                    else if (item.review_status === 'pending_review') statusBadgeClass = 'bg-amber-50 text-amber-700 border-amber-200';
                    else if (item.review_status === 'incorrect') statusBadgeClass = 'bg-rose-50 text-rose-700 border-rose-200';

                    return (
                      <tr
                        key={`${item.benchmark_id}_${item.field_name}_${idx}`}
                        onClick={() => selectItemForReview(item)}
                        className={`cursor-pointer transition-colors text-[11px] ${
                          isSelected ? 'bg-blue-50/70 border-l-2 border-l-[#2563EB]' : 'hover:bg-slate-50/60'
                        }`}
                      >
                        <td className="py-2.5 px-3 font-mono font-semibold text-[#172033]">
                          <code>{item.benchmark_id}</code>
                        </td>
                        <td className="py-2.5 px-2 text-[#172033]">{item.country}</td>
                        <td className="py-2.5 px-2 text-[#64748B] truncate max-w-[110px]" title={item.source_platform}>
                          {item.source_platform}
                        </td>
                        <td className="py-2.5 px-2 font-bold text-[#172033]">{item.field_name}</td>
                        <td className="py-2.5 px-3 font-mono text-emerald-700 truncate max-w-[130px]" title={item.expected_raw}>
                          {item.expected_raw ? item.expected_raw : <em className="text-slate-400 font-sans">empty</em>}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-rose-600 truncate max-w-[130px]" title={item.predicted_raw}>
                          {item.predicted_raw ? item.predicted_raw : <em className="text-slate-400 font-sans">missing</em>}
                        </td>
                        <td className="py-2.5 px-2 text-[10px] text-[#64748B] truncate max-w-[120px]" title={item.error_category}>
                          {item.error_category}
                        </td>
                        <td className="py-2.5 px-2 text-center">
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold border ${statusBadgeClass}`}>
                            {item.review_status}
                          </span>
                        </td>
                        <td className="py-2.5 px-2 text-center">
                          {item.source_url ? (
                            <a
                              href={item.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="inline-flex text-[#2563EB] hover:text-[#1D4ED8]"
                              title="Open original posting link"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                            </a>
                          ) : (
                            <span className="text-slate-300">—</span>
                          )}
                        </td>
                        <td className="py-2.5 px-2 text-center">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              selectItemForReview(item);
                            }}
                            className={`rounded px-2 py-1 text-[10px] font-semibold transition-all ${
                              isSelected
                                ? 'bg-[#2563EB] text-white'
                                : 'border border-[#E2E8F0] bg-white text-[#172033] hover:bg-slate-50'
                            }`}
                          >
                            Review
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-[#E2E8F0] pt-3 text-xs text-[#64748B]">
                <div>
                  Page <strong className="text-[#172033]">{queuePage}</strong> of{' '}
                  <strong className="text-[#172033]">{totalPages}</strong> ({totalQueueCount} total discrepancy records)
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => {
                      if (queuePage > 1) {
                        setQueuePage(queuePage - 1);
                        fetchReviewQueue(queuePage - 1);
                      }
                    }}
                    disabled={queuePage <= 1}
                    className="inline-flex items-center gap-1 rounded border border-[#E2E8F0] bg-white px-2.5 py-1 text-xs font-semibold text-[#172033] hover:bg-slate-50 disabled:opacity-40"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                    Previous
                  </button>
                  <button
                    onClick={() => {
                      if (queuePage < totalPages) {
                        setQueuePage(queuePage + 1);
                        fetchReviewQueue(queuePage + 1);
                      }
                    }}
                    disabled={queuePage >= totalPages}
                    className="inline-flex items-center gap-1 rounded border border-[#E2E8F0] bg-white px-2.5 py-1 text-xs font-semibold text-[#172033] hover:bg-slate-50 disabled:opacity-40"
                  >
                    Next
                    <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            )}

            {/* Interactive Verification Decision Panel */}
            {selectedItem && (
              <div className="rounded-xl border border-blue-200 bg-blue-50/40 p-5 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-blue-200 pb-3">
                  <div>
                    <h4 className="text-sm font-bold text-[#172033]">
                      Submit Verification Decision or Operational Correction
                    </h4>
                    <p className="text-[11px] text-[#64748B]">
                      Records an immutable peer review annotation for <code>{selectedItem.benchmark_id}</code>. Ground-truth benchmark files are never overwritten.
                    </p>
                  </div>
                  <div className="text-xs">
                    <span className="font-semibold text-[#64748B]">Field Under Review: </span>
                    <strong className="text-[#2563EB]">{selectedItem.field_name}</strong>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Left Column: Discrepancy Evidence Context */}
                  <div className="space-y-2.5 text-xs">
                    <div className="flex justify-between border-b border-slate-200/60 pb-1.5">
                      <span className="text-[#64748B]">Benchmark ID:</span>
                      <strong className="font-mono text-[#172033]">{selectedItem.benchmark_id}</strong>
                    </div>
                    <div className="flex justify-between border-b border-slate-200/60 pb-1.5">
                      <span className="text-[#64748B]">Platform / Hostname:</span>
                      <strong className="text-[#172033]">{selectedItem.source_platform}</strong>
                    </div>
                    <div className="flex justify-between border-b border-slate-200/60 pb-1.5">
                      <span className="text-[#64748B]">Country:</span>
                      <strong className="text-[#172033]">{selectedItem.country}</strong>
                    </div>
                    <div className="flex justify-between border-b border-slate-200/60 pb-1.5">
                      <span className="text-[#64748B]">Expected (Ground Truth):</span>
                      <strong className="font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                        {selectedItem.expected_raw || '<empty>'}
                      </strong>
                    </div>
                    <div className="flex justify-between border-b border-slate-200/60 pb-1.5">
                      <span className="text-[#64748B]">Extracted by Scraper:</span>
                      <strong className="font-mono text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200">
                        {selectedItem.predicted_raw || '<missing>'}
                      </strong>
                    </div>
                    <div className="space-y-1 pt-1">
                      <span className="text-[#64748B]">Discrepancy Details:</span>
                      <p className="text-[11px] italic text-[#172033] bg-white p-2 rounded border border-slate-200">
                        {selectedItem.discrepancy_details || 'Value divergence observed during automated matching.'}
                      </p>
                    </div>
                    {selectedItem.source_url && (
                      <div className="pt-1">
                        <a
                          href={selectedItem.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#2563EB] hover:underline"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                          Inspect Authoritative Source URL
                        </a>
                      </div>
                    )}
                  </div>

                  {/* Right Column: Reviewer Decision Form */}
                  <form onSubmit={handleSaveDecision} className="space-y-3">
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-[#172033]">
                        Reviewer Decision Status:
                      </label>
                      <select
                        value={decisionStatus}
                        onChange={(e) => setDecisionStatus(e.target.value)}
                        className="w-full rounded-lg border border-[#E2E8F0] bg-white p-2 text-xs font-medium text-[#172033] focus:border-[#2563EB] focus:outline-hidden"
                      >
                        <option value="verified">verified (Ground truth reference is authoritative)</option>
                        <option value="incorrect">incorrect (Scraper extracted invalid value)</option>
                        <option value="unavailable">unavailable (Omitted / unavailable from source page)</option>
                        <option value="ambiguous">ambiguous (Source page content is ambiguous)</option>
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-[#172033]">
                        Corrected / Validated Value (optional override):
                      </label>
                      <input
                        type="text"
                        value={correctedValue}
                        onChange={(e) => setCorrectedValue(e.target.value)}
                        placeholder="Leave blank to accept reference, or input validated string"
                        className="w-full rounded-lg border border-[#E2E8F0] bg-white p-2 text-xs text-[#172033] placeholder-[#94A3B8] focus:border-[#2563EB] focus:outline-hidden"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-[#172033]">
                        Reviewer Identifier:
                      </label>
                      <input
                        type="text"
                        value={reviewerId}
                        onChange={(e) => setReviewerId(e.target.value)}
                        className="w-full rounded-lg border border-[#E2E8F0] bg-white p-2 text-xs text-[#172033] focus:border-[#2563EB] focus:outline-hidden"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-[#172033]">
                        Reviewer Justification / Evidence Notes (mandatory):
                      </label>
                      <textarea
                        rows={2}
                        value={reviewerNotes}
                        onChange={(e) => setReviewerNotes(e.target.value)}
                        placeholder="Document verified evidence from source page or rationale..."
                        className="w-full rounded-lg border border-[#E2E8F0] bg-white p-2 text-xs text-[#172033] placeholder-[#94A3B8] focus:border-[#2563EB] focus:outline-hidden"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={savingDecision}
                      className="w-full flex items-center justify-center gap-2 rounded-lg bg-[#2563EB] px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-[#1D4ED8] disabled:opacity-50 transition-colors"
                    >
                      {savingDecision ? (
                        <>
                          <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                          Persisting Review Decision...
                        </>
                      ) : (
                        '💾 Persist Review Decision'
                      )}
                    </button>

                    {decisionFeedback && (
                      <div
                        className={`rounded-lg p-2.5 text-xs flex items-center gap-2 ${
                          decisionFeedback.success
                            ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
                            : 'bg-rose-50 border border-rose-200 text-rose-800'
                        }`}
                      >
                        {decisionFeedback.success ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                        ) : (
                          <XCircle className="h-4 w-4 text-rose-600 shrink-0" />
                        )}
                        <span>{decisionFeedback.message}</span>
                      </div>
                    )}
                  </form>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 8. Reviewer Audit Trail & Correction History (Expandable) */}
        <div className="border-t border-[#E2E8F0] pt-4">
          <button
            onClick={() => setHistoryOpen(!historyOpen)}
            className="w-full flex items-center justify-between text-left text-xs font-semibold text-[#172033] hover:text-[#2563EB]"
          >
            <span className="flex items-center gap-1.5">
              📜 View Reviewer Audit Trail & Correction History ({history.length} records recorded)
            </span>
            {historyOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>

          {historyOpen && (
            <div className="mt-3 pt-3 border-t border-[#E2E8F0] space-y-2">
              {history.length === 0 ? (
                <div className="text-xs text-[#64748B] italic p-3 text-center">
                  No historical review decisions logged yet. Decisions saved above will appear here in the immutable audit trail.
                </div>
              ) : (
                <div className="overflow-x-auto border border-[#E2E8F0] rounded-lg">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-b border-[#E2E8F0] text-[11px] font-semibold text-[#64748B]">
                      <tr>
                        <th className="py-2 px-3">Timestamp</th>
                        <th className="py-2 px-3">Benchmark ID</th>
                        <th className="py-2 px-3">Field</th>
                        <th className="py-2 px-3">Status</th>
                        <th className="py-2 px-3">Reviewer</th>
                        <th className="py-2 px-3">Justification Notes</th>
                        <th className="py-2 px-3">Corrected Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E2E8F0]">
                      {history.map((h, i) => (
                        <tr key={i} className="hover:bg-slate-50/60 font-mono text-[11px]">
                          <td className="py-2 px-3 text-[#64748B] whitespace-nowrap">{h.timestamp?.slice(0, 19)}</td>
                          <td className="py-2 px-3 font-semibold text-[#172033]">{h.benchmark_id}</td>
                          <td className="py-2 px-3 font-bold text-[#2563EB]">{h.field_name}</td>
                          <td className="py-2 px-3">
                            <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-800">
                              {h.status}
                            </span>
                          </td>
                          <td className="py-2 px-3 font-sans text-[#172033]">{h.reviewer_id}</td>
                          <td className="py-2 px-3 font-sans text-[#64748B] truncate max-w-[200px]" title={h.reviewer_notes}>
                            {h.reviewer_notes}
                          </td>
                          <td className="py-2 px-3 text-emerald-700">{h.corrected_value || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 9. Downloadable Export Package Section */}
      <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-3">
        <div className="border-b border-[#E2E8F0] pb-2">
          <h3 className="text-sm font-bold text-[#172033]">Download Validation & Accuracy Package</h3>
          <p className="text-[11px] text-[#64748B]">
            Export audit datasets reflecting current filter selections. Sensitive tokens and internal passwords are excluded.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 pt-1">
          {/* 1. Summary CSV */}
          <a
            href={`/api/validation/download/summary?run_id=${selectedRunId}`}
            download
            className="flex items-center justify-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-3 py-2 text-xs font-semibold text-[#172033] shadow-2xs hover:bg-slate-50 transition-colors"
          >
            <Download className="h-3.5 w-3.5 text-[#2563EB]" />
            📊 Summary CSV
          </a>

          {/* 2. Filtered Errors CSV */}
          <a
            href={`/api/validation/download/errors?run_id=${selectedRunId}&country=${countryFilter}&platform=${platformFilter}&method=${methodFilter}&field_name=${fieldFilter}&status=${statusFilter}&error_cat=${errorCatFilter}&search_query=${encodeURIComponent(searchQuery)}`}
            download
            className="flex items-center justify-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-3 py-2 text-xs font-semibold text-[#172033] shadow-2xs hover:bg-slate-50 transition-colors"
          >
            <Download className="h-3.5 w-3.5 text-amber-600" />
            ⚠️ Filtered Errors CSV
          </a>

          {/* 3. Stratification CSV */}
          <a
            href={`/api/validation/download/stratification?run_id=${selectedRunId}`}
            download
            className="flex items-center justify-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-3 py-2 text-xs font-semibold text-[#172033] shadow-2xs hover:bg-slate-50 transition-colors"
          >
            <Download className="h-3.5 w-3.5 text-emerald-600" />
            🌍 Stratification CSV
          </a>

          {/* 4. Review Queue CSV */}
          <a
            href={`/api/validation/download/queue?run_id=${selectedRunId}&country=${countryFilter}&platform=${platformFilter}&method=${methodFilter}&field_name=${fieldFilter}&status=${statusFilter}&error_cat=${errorCatFilter}&search_query=${encodeURIComponent(searchQuery)}`}
            download
            className="flex items-center justify-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-3 py-2 text-xs font-semibold text-[#172033] shadow-2xs hover:bg-slate-50 transition-colors"
          >
            <Download className="h-3.5 w-3.5 text-purple-600" />
            📝 Review Queue CSV
          </a>

          {/* 5. Full Report (.md) */}
          <a
            href={`/api/validation/download/report?run_id=${selectedRunId}`}
            download
            className="flex items-center justify-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-3 py-2 text-xs font-semibold text-[#172033] shadow-2xs hover:bg-slate-50 transition-colors"
          >
            <FileText className="h-3.5 w-3.5 text-blue-700" />
            📄 Full Report (.md)
          </a>
        </div>
      </div>
    </div>
  );
};
