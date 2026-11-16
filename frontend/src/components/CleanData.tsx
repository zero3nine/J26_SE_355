import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  ArrowRight,
  Database,
  DownloadCloud,
  FileText,
  CheckCircle2,
  RefreshCw,
  Search,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Download,
  MapPin,
} from 'lucide-react';
import { SecurityNotice } from './SecurityNotice';

interface CleanDataProps {
  onNavigateToCollect: () => void;
  onNavigateToRaw: () => void;
  onNavigateToExtract?: () => void;
}

interface CleanDataResponse {
  status: string;
  has_raw_data: boolean;
  raw_record_count: number;
  cleaning_completed: boolean;
  batch_id: string;
  stats: {
    total_raw_records?: number;
    filtered_short_title?: number;
    filtered_short_desc?: number;
    filtered_future_date?: number;
    filtered_non_it?: number;
    dedup_step1_removed?: number;
    dedup_step2_removed?: number;
    final_internal_records?: number;
    final_team_records?: number;
  };
  work_mode_distribution: Record<string, number>;
  country_distribution: Record<string, number>;
  published_run_id?: string;
  columns: string[];
  total_clean_records: number;
  records: Array<Record<string, any>>;
  page: number;
  page_size: number;
  total_pages: number;
}

export const CleanData: React.FC<CleanDataProps> = ({
  onNavigateToCollect,
  onNavigateToRaw,
  onNavigateToExtract,
}) => {
  const [data, setData] = useState<CleanDataResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [cleaning, setCleaning] = useState<boolean>(false);
  const [publishing, setPublishing] = useState<boolean>(false);
  const [publishResult, setPublishResult] = useState<{
    import_run_id: string;
    inserted_jobs: number;
    skipped_duplicates: number;
  } | null>(null);

  // Search & Pagination in cleaned records
  const [search, setSearch] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);

  // Expandable diagnostics
  const [showDiagnostics, setShowDiagnostics] = useState<boolean>(false);
  const [expandedDescId, setExpandedDescId] = useState<string | null>(null);

  // Available batches for quick load
  const [availableBatches, setAvailableBatches] = useState<any[]>([]);
  const [selectedBatch, setSelectedBatch] = useState<string>('');
  const [batchLoading, setBatchLoading] = useState<boolean>(false);

  const fetchCleanData = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      if (search.trim()) params.append('search', search.trim());

      const res = await fetch(`/api/clean-data?${params.toString()}`);
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }

      // If no raw data, fetch available batches so user can test-load
      const rawRes = await fetch('/api/raw-data');
      if (rawRes.ok) {
        const rawJson = await rawRes.json();
        setAvailableBatches(rawJson.available_batches || []);
      }
    } catch (err) {
      console.error('Failed to load clean data state:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCleanData();
  }, [page, pageSize]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchCleanData();
    }, 350);
    return () => clearTimeout(timer);
  }, [search]);

  const handleExecuteClean = async () => {
    try {
      setCleaning(true);
      setPublishResult(null);
      const res = await fetch('/api/clean-data/execute', { method: 'POST' });
      if (res.ok) {
        await fetchCleanData();
      }
    } catch (err) {
      console.error('Failed to execute clean pipeline:', err);
    } finally {
      setCleaning(false);
    }
  };

  const handlePublishMaster = async () => {
    try {
      setPublishing(true);
      const res = await fetch('/api/clean-data/publish-master', { method: 'POST' });
      if (res.ok) {
        const json = await res.json();
        setPublishResult(json);
        await fetchCleanData();
      }
    } catch (err) {
      console.error('Failed to publish clean data to master:', err);
    } finally {
      setPublishing(false);
    }
  };

  const handleLoadBatchForTest = async () => {
    if (!selectedBatch) return;
    try {
      setBatchLoading(true);
      await fetch('/api/raw-data/load-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch_id: selectedBatch }),
      });
      await fetchCleanData();
    } catch (err) {
      console.error('Failed to load batch:', err);
    } finally {
      setBatchLoading(false);
    }
  };

  // Funnel calculation metrics
  const totalRaw = data?.stats.total_raw_records || data?.raw_record_count || 0;
  const nonItExcl = data?.stats.filtered_non_it || 0;
  const shortTitleExcl = data?.stats.filtered_short_title || 0;
  const shortDescExcl = data?.stats.filtered_short_desc || 0;
  const futureDateExcl = data?.stats.filtered_future_date || 0;
  const totalExcl = nonItExcl + shortTitleExcl + shortDescExcl + futureDateExcl;

  const dedup1 = data?.stats.dedup_step1_removed || 0;
  const dedup2 = data?.stats.dedup_step2_removed || 0;
  const totalDedup = dedup1 + dedup2;

  const finalClean = data?.stats.final_team_records || data?.total_clean_records || 0;
  const yieldPct = totalRaw > 0 ? Math.round((finalClean / totalRaw) * 100) : 0;

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-2 border-b border-[#E2E8F0] pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-100 text-[#2563EB]">
              <Sparkles className="h-4 w-4" />
            </span>
            <h2 className="text-2xl font-bold tracking-tight text-[#172033]">
              Data Cleaning & Standardization Pipeline
            </h2>
          </div>
          <p className="mt-1 text-sm text-[#64748B]">
            Execute multi-tier data cleaning, HTML entity decoding, non-IT heuristic filtering, multi-currency salary normalization, and two-stage deduplication.
          </p>
        </div>

        {data?.cleaning_completed && (
          <div className="flex items-center gap-2">
            <a
              href="/api/clean-data/download"
              download
              className="inline-flex items-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-3.5 py-2 text-xs font-semibold text-[#172033] shadow-2xs hover:bg-slate-50 transition-colors"
            >
              <Download className="h-3.5 w-3.5 text-[#2563EB]" />
              Download Clean CSV
            </a>
          </div>
        )}
      </div>

      {/* Security Warning Notice */}
      <SecurityNotice />

      {/* Main Condition: Empty State vs Available Data State */}
      {loading && !data ? (
        <div className="flex h-64 items-center justify-center rounded-xl border border-[#E2E8F0] bg-white p-8">
          <div className="flex flex-col items-center gap-2 text-[#64748B]">
            <RefreshCw className="h-6 w-6 animate-spin text-[#2563EB]" />
            <span className="text-sm">Connecting to data-cleaning pipeline backend...</span>
          </div>
        </div>
      ) : !data?.has_raw_data ? (
        /* Empty State */
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-10 text-center shadow-xs space-y-6">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-50 text-[#64748B] border border-slate-200">
            <Sparkles className="h-8 w-8 text-slate-400" />
          </div>

          <div className="space-y-1.5">
            <h3 className="text-xl font-bold text-[#172033]">No Raw Data Available for Cleaning</h3>
            <p className="mx-auto max-w-lg text-sm text-[#64748B] leading-relaxed">
              No raw data to clean. Please collect raw records first.
            </p>
          </div>

          <div className="pt-2 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <button
              onClick={onNavigateToCollect}
              className="inline-flex items-center gap-2 rounded-xl bg-[#2563EB] px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#1D4ED8] transition-all"
            >
              <DownloadCloud className="h-4 w-4" />
              Go to Collect Data
            </button>

            <button
              onClick={onNavigateToRaw}
              className="inline-flex items-center gap-2 rounded-xl border border-[#E2E8F0] bg-white px-4 py-2.5 text-sm font-semibold text-[#172033] hover:bg-slate-50 transition-colors"
            >
              <FileText className="h-4 w-4 text-[#64748B]" />
              View Raw Data
            </button>
          </div>

          {availableBatches.length > 0 && (
            <div className="pt-4 border-t border-[#E2E8F0] max-w-md mx-auto flex items-center justify-center gap-2 text-xs text-[#64748B]">
              <span>Or load past raw crawl:</span>
              <select
                value={selectedBatch}
                onChange={(e) => setSelectedBatch(e.target.value)}
                className="rounded-lg border border-[#E2E8F0] bg-slate-50 px-2.5 py-1.5 text-xs text-[#172033]"
              >
                <option value="">Select batch...</option>
                {availableBatches.map((b) => (
                  <option key={b.batch_id} value={b.batch_id}>
                    {b.filename} ({b.size_kb} KB)
                  </option>
                ))}
              </select>
              <button
                onClick={handleLoadBatchForTest}
                disabled={!selectedBatch || batchLoading}
                className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-[#2563EB] hover:bg-blue-100 disabled:opacity-50"
              >
                {batchLoading ? 'Loading...' : 'Load'}
              </button>
            </div>
          )}
        </div>
      ) : (
        /* Populated Raw Records State */
        <div className="space-y-6">
          {/* Cleaning Trigger & Pipeline Launch Card */}
          <div className="rounded-xl border border-[#E2E8F0] bg-white p-6 shadow-xs">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-[#2563EB]">
                  Batch Processing Ready
                </span>
                <h3 className="text-lg font-bold text-[#172033]">
                  Ready to Clean {data.raw_record_count} Raw Job Advertisements
                </h3>
                <p className="mt-1 text-xs text-[#64748B]">
                  Executes HTML entity parsing, IT role classification heuristic, location/salary standardization, and deduplication.
                </p>
              </div>

              <button
                onClick={handleExecuteClean}
                disabled={cleaning}
                className="inline-flex items-center gap-2 rounded-xl bg-[#2563EB] px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-[#1D4ED8] disabled:opacity-50 transition-all shrink-0"
              >
                {cleaning ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Executing Cleaning Pipeline...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    ✨ Clean and Standardize Data
                  </>
                )}
              </button>
            </div>

            {/* Standard Config Checkboxes (Preserving existing defaults) */}
            <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 border-t border-[#E2E8F0] pt-4 text-xs text-[#172033]">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-[#16A34A]" />
                <span>HTML Entity Decoding & Tag Stripping</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-[#16A34A]" />
                <span>IT Role Heuristic Scoring & Exclusion</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-[#16A34A]" />
                <span>Two-Tier Deduplication (URL & Hash)</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-[#16A34A]" />
                <span>Multi-Currency Salary Normalization</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-[#16A34A]" />
                <span>Geographic & Work-Mode Standardizer</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-[#16A34A]" />
                <span>Team 10-Column Schema Standardization</span>
              </div>
            </div>
          </div>

          {/* Pipeline Statistics Funnel (When completed) */}
          {data.cleaning_completed && (
            <div className="rounded-xl border border-[#E2E8F0] bg-white p-6 shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3">
                <div>
                  <h3 className="text-base font-bold text-[#172033]">
                    Cleaning Pipeline Funnel & Yield Summary
                  </h3>
                  <p className="text-xs text-[#64748B]">
                    Sequential record attrition across filtering, deduplication, and standardization stages.
                  </p>
                </div>
                <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-[#16A34A] border border-emerald-200">
                  {yieldPct}% Acceptance Yield
                </span>
              </div>

              {/* Funnel Steps */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 pt-2">
                {/* Step 1: Raw Input */}
                <div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-4 relative">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                    1. Raw Input
                  </div>
                  <div className="mt-1 text-2xl font-bold text-[#172033]">
                    {totalRaw}
                  </div>
                  <div className="mt-1 text-[11px] text-[#16A34A] font-medium">
                    Initial crawl batch
                  </div>
                  <div className="mt-3 h-1.5 w-full rounded-full bg-slate-200 overflow-hidden">
                    <div className="h-full bg-[#2563EB]" style={{ width: '100%' }} />
                  </div>
                </div>

                {/* Step 2: Non-IT Exclusions */}
                <div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-4 relative">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                    2. Filtering
                  </div>
                  <div className="mt-1 text-2xl font-bold text-[#172033]">
                    {Math.max(0, totalRaw - totalExcl)}
                  </div>
                  <div className="mt-1 text-[11px] text-[#DC2626] font-medium">
                    -{totalExcl} non-IT / invalid exclusions
                  </div>
                  <div className="mt-3 h-1.5 w-full rounded-full bg-slate-200 overflow-hidden">
                    <div
                      className="h-full bg-amber-500"
                      style={{
                        width: `${totalRaw > 0 ? Math.round(((totalRaw - totalExcl) / totalRaw) * 100) : 0}%`,
                      }}
                    />
                  </div>
                </div>

                {/* Step 3: Deduplication */}
                <div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-4 relative">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                    3. Deduplication
                  </div>
                  <div className="mt-1 text-2xl font-bold text-[#172033]">
                    {data.stats.final_internal_records || Math.max(0, totalRaw - totalExcl - totalDedup)}
                  </div>
                  <div className="mt-1 text-[11px] text-[#7C3AED] font-medium">
                    -{totalDedup} duplicates eliminated
                  </div>
                  <div className="mt-3 h-1.5 w-full rounded-full bg-slate-200 overflow-hidden">
                    <div
                      className="h-full bg-purple-500"
                      style={{
                        width: `${totalRaw > 0 ? Math.round((finalClean / totalRaw) * 100) : 0}%`,
                      }}
                    />
                  </div>
                </div>

                {/* Step 4: Final Clean Yield */}
                <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-4 relative">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-[#16A34A]">
                    4. Final Clean Jobs
                  </div>
                  <div className="mt-1 text-2xl font-bold text-[#16A34A]">
                    {finalClean}
                  </div>
                  <div className="mt-1 text-[11px] text-emerald-800 font-medium">
                    Standardized team records
                  </div>
                  <div className="mt-3 h-1.5 w-full rounded-full bg-emerald-200 overflow-hidden">
                    <div className="h-full bg-[#16A34A]" style={{ width: `${yieldPct}%` }} />
                  </div>
                </div>
              </div>

              {/* Geographic Normalization & Work-Mode Diagnostics Accordion */}
              <div className="border-t border-[#E2E8F0] pt-4">
                <button
                  type="button"
                  onClick={() => setShowDiagnostics(!showDiagnostics)}
                  className="flex w-full items-center justify-between text-xs font-semibold text-[#172033] hover:text-[#2563EB]"
                >
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-[#2563EB]" />
                    <span>📍 Geographic Normalization & Work-Mode Diagnostics</span>
                  </div>
                  {showDiagnostics ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </button>

                {showDiagnostics && (
                  <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2 pt-2">
                    {/* Work-Mode Breakdown */}
                    <div className="rounded-xl border border-[#E2E8F0] bg-slate-50/60 p-4">
                      <div className="text-xs font-bold text-[#172033] mb-2">
                        Work-Mode Distribution (Analytically Distinct)
                      </div>
                      <div className="space-y-1.5">
                        {Object.entries(data.work_mode_distribution).length === 0 ? (
                          <div className="text-xs text-[#64748B] italic">No work-mode data recorded.</div>
                        ) : (
                          Object.entries(data.work_mode_distribution).map(([mode, cnt]) => (
                            <div key={mode} className="flex justify-between text-xs py-1 border-b border-slate-200 last:border-b-0">
                              <span className="font-medium text-[#172033] capitalize">{mode}</span>
                              <span className="font-mono text-[#2563EB] font-semibold">{cnt}</span>
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    {/* Country Breakdown */}
                    <div className="rounded-xl border border-[#E2E8F0] bg-slate-50/60 p-4">
                      <div className="text-xs font-bold text-[#172033] mb-2">
                        Country Normalization Breakdown
                      </div>
                      <div className="space-y-1.5">
                        {Object.entries(data.country_distribution).length === 0 ? (
                          <div className="text-xs text-[#64748B] italic">No country data recorded.</div>
                        ) : (
                          Object.entries(data.country_distribution).map(([c, cnt]) => (
                            <div key={c} className="flex justify-between text-xs py-1 border-b border-slate-200 last:border-b-0">
                              <span className="font-medium text-[#172033]">{c}</span>
                              <span className="font-mono text-[#16A34A] font-semibold">{cnt}</span>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Cleaned Dataset Preview Table */}
          {data.cleaning_completed && (
            <div className="rounded-xl border border-[#E2E8F0] bg-white shadow-xs overflow-hidden space-y-4 p-6">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-[#E2E8F0] pb-4">
                <div>
                  <h3 className="text-base font-bold text-[#172033]">
                    Cleaned Dataset (Team Schema Format — 10 Columns)
                  </h3>
                  <p className="text-xs text-[#64748B]">
                    Inspected and standardized job postings ready for skill extraction and SQLite master publishing.
                  </p>
                </div>

                <div className="relative w-64">
                  <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-[#64748B]" />
                  <input
                    type="text"
                    placeholder="Search cleaned jobs..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] pl-8 pr-3 py-1.5 text-xs text-[#172033] focus:border-[#2563EB] focus:bg-white focus:outline-none"
                  />
                </div>
              </div>

              {/* Table */}
              <div className="overflow-x-auto rounded-lg border border-[#E2E8F0]">
                <table className="w-full border-collapse text-left text-xs">
                  <thead>
                    <tr className="border-b border-[#E2E8F0] bg-[#F8FAFC] text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                      <th className="px-4 py-3">Job ID</th>
                      <th className="px-4 py-3">Job Title</th>
                      <th className="px-4 py-3">Company</th>
                      <th className="px-4 py-3">Country</th>
                      <th className="px-4 py-3">Location</th>
                      <th className="px-4 py-3">Description</th>
                      <th className="px-4 py-3">Posted</th>
                      <th className="px-4 py-3">Source</th>
                      <th className="px-4 py-3 text-center">URL</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E2E8F0]">
                    {data.records.length === 0 ? (
                      <tr>
                        <td colSpan={9} className="py-8 text-center text-xs text-[#64748B]">
                          No records match search criteria.
                        </td>
                      </tr>
                    ) : (
                      data.records.map((r, idx) => {
                        const isExpanded = expandedDescId === r.job_id;
                        return (
                          <tr key={r.job_id || idx} className="hover:bg-slate-50 transition-colors">
                            <td className="px-4 py-3 font-mono text-[11px] text-[#2563EB] whitespace-nowrap">
                              {r.job_id}
                            </td>
                            <td className="px-4 py-3 font-medium text-[#172033] max-w-xs truncate" title={r.job_title || r.job_title_raw}>
                              {r.job_title || r.job_title_raw || '—'}
                            </td>
                            <td className="px-4 py-3 text-[#64748B] max-w-[140px] truncate" title={r.company}>
                              {r.company || '—'}
                            </td>
                            <td className="px-4 py-3 text-[#64748B] whitespace-nowrap">
                              {r.country || r.country_normalized || '—'}
                            </td>
                            <td className="px-4 py-3 text-[#64748B] max-w-[140px] truncate">
                              {r.location || r.location_raw || '—'}
                            </td>
                            <td className="px-4 py-3 text-[#64748B] max-w-xs">
                              <div>
                                <button
                                  type="button"
                                  onClick={() => setExpandedDescId(isExpanded ? null : r.job_id)}
                                  className="text-left font-medium text-[#2563EB] hover:underline truncate block max-w-[220px]"
                                >
                                  {r.job_description ? r.job_description.slice(0, 35) + '...' : '—'}
                                </button>
                                {isExpanded && (
                                  <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 p-3 font-mono text-[11px] text-[#172033] whitespace-pre-wrap max-h-40 overflow-y-auto leading-relaxed">
                                    {r.job_description}
                                  </div>
                                )}
                              </div>
                            </td>
                            <td className="px-4 py-3 text-[#64748B] whitespace-nowrap">
                              {r.posted_date || '—'}
                            </td>
                            <td className="px-4 py-3 text-[#64748B] whitespace-nowrap">
                              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-700">
                                {r.source_platform || 'N/A'}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-center whitespace-nowrap">
                              {r.source_url ? (
                                <a
                                  href={r.source_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center justify-center rounded p-1 text-[#2563EB] hover:bg-blue-50"
                                >
                                  <ExternalLink className="h-3.5 w-3.5" />
                                </a>
                              ) : (
                                <span className="text-slate-300">—</span>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-[#64748B] pt-2">
                <div className="flex items-center gap-3">
                  <span>
                    Showing {Math.min((data.page - 1) * data.page_size + 1, data.total_clean_records)} to{' '}
                    {Math.min(data.page * data.page_size, data.total_clean_records)} of{' '}
                    <strong>{data.total_clean_records}</strong> clean jobs
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span>Per page:</span>
                    <select
                      value={pageSize}
                      onChange={(e) => {
                        setPageSize(Number(e.target.value));
                        setPage(1);
                      }}
                      className="rounded border border-[#E2E8F0] bg-white px-2 py-0.5 text-xs text-[#172033] focus:border-[#2563EB] focus:outline-none"
                    >
                      <option value={10}>10</option>
                      <option value={20}>20</option>
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                    </select>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={data.page <= 1}
                    className="inline-flex h-7 w-7 items-center justify-center rounded border border-[#E2E8F0] bg-white text-[#64748B] hover:bg-slate-50 disabled:opacity-40"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <span className="px-2 font-medium text-[#172033]">
                    {data.page} / {data.total_pages}
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                    disabled={data.page >= data.total_pages}
                    className="inline-flex h-7 w-7 items-center justify-center rounded border border-[#E2E8F0] bg-white text-[#64748B] hover:bg-slate-50 disabled:opacity-40"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Publish to Master Database Section */}
          {data.cleaning_completed && (
            <div className="rounded-xl border border-[#E2E8F0] bg-white p-6 shadow-xs space-y-4">
              <div className="border-b border-[#E2E8F0] pb-3">
                <h3 className="text-base font-bold text-[#172033]">Publish to Master Database</h3>
                <p className="text-xs text-[#64748B]">
                  To extract skills and run relationship/regional analysis across research batches, jobs must be published to the persistent SQLite master database.
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <button
                  onClick={handlePublishMaster}
                  disabled={publishing}
                  className="inline-flex items-center gap-2 rounded-xl bg-purple-600 px-5 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-purple-700 disabled:opacity-50 transition-all"
                >
                  {publishing ? (
                    <>
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      Publishing to SQLite...
                    </>
                  ) : (
                    <>
                      <Database className="h-3.5 w-3.5" />
                      🚀 Publish this batch to Master Database now
                    </>
                  )}
                </button>

                {(publishResult || data.published_run_id) && (
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3.5 py-2 text-xs text-emerald-950">
                      <CheckCircle2 className="h-4 w-4 text-[#16A34A] shrink-0" />
                      <div>
                        Published in Master Database (Run ID:{' '}
                        <code className="font-mono font-bold">
                          {publishResult?.import_run_id || data.published_run_id}
                        </code>
                        )
                      </div>
                    </div>

                    {onNavigateToExtract && (
                      <button
                        onClick={onNavigateToExtract}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-purple-200 bg-purple-50 px-3 py-2 text-xs font-medium text-purple-700 hover:bg-purple-100 transition-colors"
                      >
                        Navigate to Extract Skills
                        <ArrowRight className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
