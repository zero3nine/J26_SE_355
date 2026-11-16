import React, { useState, useEffect } from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Download,
  ExternalLink,
  Search,
  RefreshCw,
  Trash2,
  Globe,
  Clock,
  Copy,
  Check,
  Eye,
  FileText,
  X,
  Layers,
} from 'lucide-react';
import { SecurityNotice } from './SecurityNotice';

interface FailureRecord {
  id: string;
  url: string;
  source_hostname: string;
  extractor_name: string;
  error_type: string;
  error_message: string;
  timestamp: string;
  retryable: 'Yes' | 'No' | string;
  kind?: 'failure' | 'exclusion' | string;
  stage?: string;
}

interface FailureLogsResponse {
  status: string;
  scope: string;
  batch_id: string;
  run_info: {
    collection_batch_id: string;
    started_at: string;
    completed_at: string;
    elapsed_seconds?: number;
    requests_attempted?: number;
    requests_completed?: number;
    valid_jobs_accepted?: number;
    failed_urls?: number;
    access_restricted_count?: number;
    permission_status?: string;
    configurations?: Record<string, any>;
  } | null;
  available_batches: string[];
  stats: {
    total_records: number;
    failures_count: number;
    exclusions_count: number;
    retryable_count: number;
    categories: Record<string, number>;
    sources: Record<string, number>;
    stages: Record<string, number>;
  };
  records: FailureRecord[];
}

export const FailureLogs: React.FC = () => {
  const [data, setData] = useState<FailureLogsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [scope, setScope] = useState<string>('session');
  const [activeTab, setActiveTab] = useState<'all' | 'failures' | 'exclusions' | 'retryable'>('all');

  // Search and filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [stageFilter, setStageFilter] = useState<string>('all');

  // Detailed modal inspection state
  const [inspectRecord, setInspectRecord] = useState<FailureRecord | null>(null);
  const [copiedUrl, setCopiedUrl] = useState<boolean>(false);

  // Actions state
  const [retrying, setRetrying] = useState<boolean>(false);
  const [actionFeedback, setActionFeedback] = useState<{
    type: 'success' | 'error' | 'info';
    message: string;
  } | null>(null);

  const fetchFailureLogs = async (targetScope: string = scope) => {
    try {
      setLoading(true);
      const res = await fetch(`/api/failure-logs?scope=${encodeURIComponent(targetScope)}`);
      if (res.ok) {
        const json: FailureLogsResponse = await res.json();
        setData(json);
      } else {
        throw new Error('Failed to load failure logs');
      }
    } catch (err: any) {
      console.error('Error loading failure logs:', err);
      setActionFeedback({
        type: 'error',
        message: err.message || 'Unable to retrieve failure logs from server.',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFailureLogs(scope);
  }, [scope]);

  // Clear feedback after 5 seconds
  useEffect(() => {
    if (actionFeedback) {
      const timer = setTimeout(() => setActionFeedback(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [actionFeedback]);

  // Handle Clear Session
  const handleClearSession = async () => {
    if (!window.confirm('Clear all rejection and failure logs for the current session?')) return;
    try {
      const res = await fetch('/api/failure-logs/clear-session', { method: 'POST' });
      if (res.ok) {
        setActionFeedback({
          type: 'success',
          message: 'Current session failure logs have been reset.',
        });
        await fetchFailureLogs('session');
      }
    } catch (err) {
      console.error('Failed to clear session logs:', err);
    }
  };

  // Handle Retry Failed URLs
  const handleRetryUrls = async (urlsToRetry: string[]) => {
    if (urlsToRetry.length === 0) return;
    setRetrying(true);
    setActionFeedback(null);
    try {
      const res = await fetch('/api/collect/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          urls: urlsToRetry,
          target_valid: Math.max(urlsToRetry.length, 10),
          max_requests: Math.max(urlsToRetry.length * 2, 20),
          max_time: 300,
          polite_delay: 2.0,
          fallback: true,
          ocr: true,
          crawl_all_pages: false,
          dataset_behavior: 'Append to current raw data',
          save_to_file: false,
        }),
      });

      if (res.ok) {
        const resData = await res.json();
        setActionFeedback({
          type: 'success',
          message: `Retry crawl job launched for ${urlsToRetry.length} URL(s) (Batch ID: ${resData.batch_id}). Monitor progress in Collect Data.`,
        });
      } else {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Failed to trigger retry job.');
      }
    } catch (err: any) {
      setActionFeedback({
        type: 'error',
        message: err.message || 'Retry job launch failed.',
      });
    } finally {
      setRetrying(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 2000);
  };

  // Filter records
  const allRecords = data?.records || [];
  const filteredRecords = allRecords.filter((rec) => {
    // Tab filter
    if (activeTab === 'failures' && rec.kind === 'exclusion') return false;
    if (activeTab === 'exclusions' && rec.kind !== 'exclusion') return false;
    if (activeTab === 'retryable' && rec.retryable !== 'Yes') return false;

    // Category filter
    if (categoryFilter !== 'all' && rec.error_type !== categoryFilter) return false;

    // Source filter
    if (sourceFilter !== 'all' && rec.source_hostname !== sourceFilter) return false;

    // Stage filter
    if (stageFilter !== 'all' && rec.stage !== stageFilter) return false;

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchUrl = rec.url.toLowerCase().includes(q);
      const matchHost = rec.source_hostname.toLowerCase().includes(q);
      const matchErr = rec.error_message.toLowerCase().includes(q);
      const matchType = rec.error_type.toLowerCase().includes(q);
      const matchExt = (rec.extractor_name || '').toLowerCase().includes(q);
      if (!matchUrl && !matchHost && !matchErr && !matchType && !matchExt) {
        return false;
      }
    }

    return true;
  });

  const retryableUrls = filteredRecords
    .filter((r) => r.retryable === 'Yes' && r.url)
    .map((r) => r.url);

  // Status badge styling helper
  const renderErrorTypeBadge = (errType: string) => {
    const isError = /fail|error|invalid|timeout|refused/i.test(errType);
    const isExclusion = /restrict|block|unsupported|non-job|ssrf|review|ocr/i.test(errType);

    if (isError) {
      return (
        <span className="inline-flex items-center gap-1 rounded-md border border-red-200 bg-red-50 px-2 py-0.5 text-[11px] font-semibold text-[#DC2626]">
          <XCircle className="h-3 w-3 shrink-0" />
          <span className="truncate max-w-[200px]" title={errType}>
            {errType}
          </span>
        </span>
      );
    }
    if (isExclusion) {
      return (
        <span className="inline-flex items-center gap-1 rounded-md border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-[#D97706]">
          <AlertTriangle className="h-3 w-3 shrink-0" />
          <span className="truncate max-w-[200px]" title={errType}>
            {errType}
          </span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-[#64748B]">
        {errType}
      </span>
    );
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-12">
      {/* 1. Shared Security Notice Banner */}
      <SecurityNotice />

      {/* 2. Page Header */}
      <div className="flex flex-col gap-3 border-b border-[#E2E8F0] pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-red-100 text-[#DC2626]">
              <AlertOctagon className="h-4 w-4" />
            </span>
            <h2 className="text-2xl font-bold tracking-tight text-[#172033]">
              Collection failures & exclusions log
            </h2>
          </div>
          <p className="mt-1 text-sm text-[#64748B]">
            Diagnostic inspection of collection exceptions, perimeter bot-wall blocks, format exclusions, and validation failures encountered during academic scraping operations.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Scope Selector */}
          <div className="flex items-center gap-1.5 text-xs text-[#64748B]">
            <span className="font-medium hidden sm:inline">Run Scope:</span>
            <select
              value={scope}
              onChange={(e) => setScope(e.target.value)}
              className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-1.5 text-xs font-semibold text-[#172033] shadow-2xs focus:border-[#2563EB] focus:outline-none"
            >
              <option value="session">Active Session Run</option>
              <option value="historical">Historical Log (failed_urls.csv)</option>
              <option value="all">All Aggregated Events</option>
              {data?.available_batches && data.available_batches.length > 0 && (
                <optgroup label="Saved Batch Records">
                  {data.available_batches.slice(0, 15).map((bId) => (
                    <option key={bId} value={bId}>
                      {bId}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
          </div>

          {/* Download CSV Button */}
          <a
            href={`/api/failure-logs/export-csv?scope=${encodeURIComponent(scope)}`}
            download={`jobs_failures_${data?.batch_id || 'log'}.csv`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-3 py-1.5 text-xs font-semibold text-[#172033] shadow-2xs hover:bg-slate-50 transition-colors"
            title="Download failure log CSV matching original format"
          >
            <Download className="h-3.5 w-3.5 text-[#2563EB]" />
            <span>Download CSV</span>
          </a>

          {/* Clear Session Logs */}
          {scope === 'session' && allRecords.length > 0 && (
            <button
              onClick={handleClearSession}
              className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold text-[#DC2626] hover:bg-red-100 transition-colors"
              title="Clear session failure log"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>Clear Session</span>
            </button>
          )}

          {/* Refresh Button */}
          <button
            onClick={() => fetchFailureLogs()}
            disabled={loading}
            className="rounded-lg border border-[#E2E8F0] bg-white p-1.5 text-[#64748B] hover:bg-slate-50 hover:text-[#172033] shadow-2xs disabled:opacity-50 transition-colors"
            title="Reload log records"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Action Toast Feedback */}
      {actionFeedback && (
        <div
          className={`flex items-center justify-between rounded-xl border p-4 text-xs font-medium shadow-xs transition-all ${
            actionFeedback.type === 'success'
              ? 'border-emerald-200 bg-emerald-50/90 text-emerald-950'
              : actionFeedback.type === 'info'
              ? 'border-blue-200 bg-blue-50/90 text-blue-950'
              : 'border-red-200 bg-red-50/90 text-red-950'
          }`}
        >
          <div className="flex items-center gap-2">
            {actionFeedback.type === 'success' ? (
              <CheckCircle2 className="h-4 w-4 text-[#16A34A] shrink-0" />
            ) : actionFeedback.type === 'info' ? (
              <CheckCircle2 className="h-4 w-4 text-[#2563EB] shrink-0" />
            ) : (
              <XCircle className="h-4 w-4 text-[#DC2626] shrink-0" />
            )}
            <span>{actionFeedback.message}</span>
          </div>
          <button
            onClick={() => setActionFeedback(null)}
            className="text-slate-400 hover:text-slate-600 font-bold ml-4"
          >
            ✕
          </button>
        </div>
      )}

      {/* 3. Failure & Exclusion Overview KPI Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {/* Total Failures */}
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-2xs border-l-4 border-l-[#DC2626]">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-[#64748B]">
            <span>Critical Failures</span>
            <XCircle className="h-4 w-4 text-[#DC2626]" />
          </div>
          <div className="mt-2 text-2xl font-bold text-[#DC2626]">
            {data?.stats?.failures_count ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-[#64748B]">
            Network, timeout & parser errors
          </div>
        </div>

        {/* Exclusions */}
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-2xs border-l-4 border-l-[#D97706]">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-[#64748B]">
            <span>Policy Exclusions</span>
            <AlertTriangle className="h-4 w-4 text-[#D97706]" />
          </div>
          <div className="mt-2 text-2xl font-bold text-[#D97706]">
            {data?.stats?.exclusions_count ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-[#64748B]">
            SSRF, bot-wall & format filters
          </div>
        </div>

        {/* Retryable Errors */}
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-2xs border-l-4 border-l-[#2563EB]">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-[#64748B]">
            <span>Retryable Records</span>
            <RotateCcw className="h-4 w-4 text-[#2563EB]" />
          </div>
          <div className="mt-2 text-2xl font-bold text-[#2563EB]">
            {data?.stats?.retryable_count ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-[#64748B]">
            Transient network or rate-limits
          </div>
        </div>

        {/* Affected Portals */}
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-2xs border-l-4 border-l-[#9333EA]">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-[#64748B]">
            <span>Affected Portals</span>
            <Globe className="h-4 w-4 text-[#9333EA]" />
          </div>
          <div className="mt-2 text-2xl font-bold text-[#9333EA]">
            {Object.keys(data?.stats?.sources || {}).length}
          </div>
          <div className="mt-1 text-[11px] text-[#64748B] truncate">
            {Object.keys(data?.stats?.sources || {}).slice(0, 3).join(', ') || 'None'}
          </div>
        </div>
      </div>

      {/* 4. Collection Run Metadata Card (if present) */}
      {data?.run_info && (
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-2xs space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-[#2563EB]" />
              <span className="text-xs font-bold text-[#172033]">
                Collection Run Context:
              </span>
              <code className="font-mono text-xs bg-slate-100 text-[#172033] px-2 py-0.5 rounded">
                {data.run_info.collection_batch_id}
              </code>
            </div>

            <div className="flex items-center gap-3 text-[11px] text-[#64748B]">
              {data.run_info.started_at && (
                <span>Started: {new Date(data.run_info.started_at).toLocaleTimeString()}</span>
              )}
              {data.run_info.elapsed_seconds !== undefined && (
                <span>Duration: {data.run_info.elapsed_seconds}s</span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-xs pt-1">
            <div>
              <span className="text-[#64748B]">Requests Attempted:</span>{' '}
              <strong className="text-[#172033]">{data.run_info.requests_attempted ?? 0}</strong>
            </div>
            <div>
              <span className="text-[#64748B]">Jobs Accepted:</span>{' '}
              <strong className="text-[#16A34A]">{data.run_info.valid_jobs_accepted ?? 0}</strong>
            </div>
            <div>
              <span className="text-[#64748B]">Failed URLs:</span>{' '}
              <strong className="text-[#DC2626]">{data.run_info.failed_urls ?? 0}</strong>
            </div>
            <div>
              <span className="text-[#64748B]">Access Restricted:</span>{' '}
              <strong className="text-[#D97706]">{data.run_info.access_restricted_count ?? 0}</strong>
            </div>
          </div>
        </div>
      )}

      {/* 5. Navigation View Tabs */}
      <div className="flex border-b border-[#E2E8F0]">
        <button
          onClick={() => setActiveTab('all')}
          className={`flex items-center gap-2 border-b-2 px-5 py-3 text-xs font-semibold transition-colors ${
            activeTab === 'all'
              ? 'border-[#2563EB] text-[#2563EB]'
              : 'border-transparent text-[#64748B] hover:text-[#172033]'
          }`}
        >
          <Layers className="h-4 w-4" />
          All Events
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] ${
              activeTab === 'all' ? 'bg-blue-100 text-[#2563EB]' : 'bg-slate-100 text-[#64748B]'
            }`}
          >
            {allRecords.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('failures')}
          className={`flex items-center gap-2 border-b-2 px-5 py-3 text-xs font-semibold transition-colors ${
            activeTab === 'failures'
              ? 'border-[#2563EB] text-[#2563EB]'
              : 'border-transparent text-[#64748B] hover:text-[#172033]'
          }`}
        >
          <XCircle className="h-4 w-4" />
          Collection Failures
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] ${
              activeTab === 'failures' ? 'bg-red-100 text-[#DC2626]' : 'bg-slate-100 text-[#64748B]'
            }`}
          >
            {data?.stats?.failures_count ?? 0}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('exclusions')}
          className={`flex items-center gap-2 border-b-2 px-5 py-3 text-xs font-semibold transition-colors ${
            activeTab === 'exclusions'
              ? 'border-[#2563EB] text-[#2563EB]'
              : 'border-transparent text-[#64748B] hover:text-[#172033]'
          }`}
        >
          <AlertTriangle className="h-4 w-4" />
          Excluded Records
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] ${
              activeTab === 'exclusions' ? 'bg-amber-100 text-[#D97706]' : 'bg-slate-100 text-[#64748B]'
            }`}
          >
            {data?.stats?.exclusions_count ?? 0}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('retryable')}
          className={`flex items-center gap-2 border-b-2 px-5 py-3 text-xs font-semibold transition-colors ${
            activeTab === 'retryable'
              ? 'border-[#2563EB] text-[#2563EB]'
              : 'border-transparent text-[#64748B] hover:text-[#172033]'
          }`}
        >
          <RotateCcw className="h-4 w-4" />
          Retryable Queue
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] ${
              activeTab === 'retryable' ? 'bg-blue-100 text-[#2563EB]' : 'bg-slate-100 text-[#64748B]'
            }`}
          >
            {data?.stats?.retryable_count ?? 0}
          </span>
        </button>
      </div>

      {/* 6. Search and Filtering Toolbar */}
      <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs space-y-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {/* Search Input */}
          <div className="relative lg:col-span-2">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-[#64748B]" />
            <input
              type="text"
              placeholder="Search by URL, error text, hostname..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] pl-9 pr-3 py-2 text-xs text-[#172033] placeholder-slate-400 focus:border-[#2563EB] focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-100"
            />
          </div>

          {/* Category Filter */}
          <div>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full rounded-lg border border-[#E2E8F0] bg-slate-50 px-2.5 py-2 text-xs text-[#172033]"
            >
              <option value="all">All Categories</option>
              {Object.keys(data?.stats?.categories || {}).map((cat) => (
                <option key={cat} value={cat}>
                  {cat} ({data?.stats?.categories[cat]})
                </option>
              ))}
            </select>
          </div>

          {/* Source Platform Filter */}
          <div>
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="w-full rounded-lg border border-[#E2E8F0] bg-slate-50 px-2.5 py-2 text-xs text-[#172033]"
            >
              <option value="all">All Portals</option>
              {Object.keys(data?.stats?.sources || {}).map((src) => (
                <option key={src} value={src}>
                  {src} ({data?.stats?.sources[src]})
                </option>
              ))}
            </select>
          </div>

          {/* Processing Stage Filter */}
          <div>
            <select
              value={stageFilter}
              onChange={(e) => setStageFilter(e.target.value)}
              className="w-full rounded-lg border border-[#E2E8F0] bg-slate-50 px-2.5 py-2 text-xs text-[#172033]"
            >
              <option value="all">All Stages</option>
              {Object.keys(data?.stats?.stages || {}).map((stg) => (
                <option key={stg} value={stg}>
                  {stg} ({data?.stats?.stages[stg]})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Active Filter Strip & Quick Retry Button */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-100 text-xs">
          <div className="text-[#64748B]">
            Showing <strong>{filteredRecords.length}</strong> of{' '}
            <strong>{allRecords.length}</strong> recorded event(s)
            {(categoryFilter !== 'all' || sourceFilter !== 'all' || stageFilter !== 'all' || searchQuery) && (
              <button
                onClick={() => {
                  setCategoryFilter('all');
                  setSourceFilter('all');
                  setStageFilter('all');
                  setSearchQuery('');
                }}
                className="ml-2 font-medium text-[#2563EB] hover:underline"
              >
                Reset filters
              </button>
            )}
          </div>

          {retryableUrls.length > 0 && (
            <button
              onClick={() => handleRetryUrls(retryableUrls)}
              disabled={retrying}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[#2563EB] px-3 py-1.5 text-xs font-semibold text-white shadow-2xs hover:bg-[#1D4ED8] disabled:opacity-50 transition-colors"
            >
              <RotateCcw className={`h-3.5 w-3.5 ${retrying ? 'animate-spin' : ''}`} />
              Retry {retryableUrls.length} Retryable URL(s)
            </button>
          )}
        </div>
      </div>

      {/* 7. Failure Logs Table / Empty State */}
      {allRecords.length === 0 ? (
        /* Empty State: Preserves exact requirement from original Streamlit page */
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-12 text-center shadow-xs space-y-4">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-[#16A34A] border border-emerald-100">
            <CheckCircle2 className="h-7 w-7" />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-[#172033]">No Collection Issues Found</h3>
            <p className="mx-auto max-w-md text-sm text-[#64748B]">
              No logs, failures, or exclusions recorded in this run.
            </p>
          </div>
          <div className="pt-2 flex justify-center gap-3">
            <button
              onClick={() => setScope('historical')}
              className="inline-flex items-center gap-1.5 rounded-xl border border-[#E2E8F0] bg-white px-4 py-2 text-xs font-semibold text-[#172033] shadow-2xs hover:bg-slate-50 transition-colors"
            >
              <Clock className="h-3.5 w-3.5 text-[#64748B]" />
              View Historical Failure Logs (failed_urls.csv)
            </button>
          </div>
        </div>
      ) : filteredRecords.length === 0 ? (
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-8 text-center text-xs text-[#64748B]">
          No failure records match the current filter criteria. Try resetting the search or category filters.
        </div>
      ) : (
        /* Table of Failure Records */
        <div className="overflow-hidden rounded-xl border border-[#E2E8F0] bg-white shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#E2E8F0] bg-slate-50 text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                <tr>
                  <th className="px-4 py-3">URL</th>
                  <th className="px-4 py-3">Source Host</th>
                  <th className="px-4 py-3">Error Classification</th>
                  <th className="px-4 py-3">Failure Reason / Message</th>
                  <th className="px-4 py-3">Stage</th>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3 text-center">Retryable</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E2E8F0]">
                {filteredRecords.map((rec) => {
                  const isRetryable = rec.retryable === 'Yes';
                  return (
                    <tr
                      key={rec.id}
                      className="hover:bg-slate-50/80 transition-colors"
                    >
                      {/* URL */}
                      <td className="px-4 py-3 font-mono text-[11px] max-w-xs truncate">
                        <a
                          href={rec.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[#2563EB] hover:underline"
                          title={rec.url}
                        >
                          <span className="truncate max-w-[220px]">{rec.url}</span>
                          <ExternalLink className="h-3 w-3 shrink-0" />
                        </a>
                      </td>

                      {/* Source Host */}
                      <td className="px-4 py-3 font-mono text-[11px] text-[#172033] whitespace-nowrap">
                        {rec.source_hostname || '—'}
                      </td>

                      {/* Error Classification */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        {renderErrorTypeBadge(rec.error_type)}
                      </td>

                      {/* Failure Reason */}
                      <td className="px-4 py-3 text-[#172033] max-w-sm truncate" title={rec.error_message}>
                        {rec.error_message.length > 55
                          ? `${rec.error_message.substring(0, 55)}...`
                          : rec.error_message}
                      </td>

                      {/* Processing Stage */}
                      <td className="px-4 py-3 text-[#64748B] whitespace-nowrap text-[11px]">
                        {rec.stage || 'Scraping'}
                      </td>

                      {/* Timestamp */}
                      <td className="px-4 py-3 text-[#64748B] whitespace-nowrap font-mono text-[11px]">
                        {rec.timestamp
                          ? new Date(rec.timestamp).toLocaleString(undefined, {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : '—'}
                      </td>

                      {/* Retryable Pill */}
                      <td className="px-4 py-3 text-center whitespace-nowrap">
                        {isRetryable ? (
                          <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-[#16A34A] border border-emerald-200">
                            Yes
                          </span>
                        ) : (
                          <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-[#64748B]">
                            No
                          </span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        <button
                          onClick={() => setInspectRecord(rec)}
                          className="inline-flex items-center gap-1 rounded-lg border border-[#E2E8F0] bg-white px-2.5 py-1 text-xs font-semibold text-[#172033] shadow-2xs hover:bg-slate-50 transition-colors"
                        >
                          <Eye className="h-3 w-3 text-[#64748B]" />
                          Inspect
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 8. Detailed Failure Inspection Modal */}
      {inspectRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-2xl rounded-2xl border border-[#E2E8F0] bg-white shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-[#E2E8F0] px-6 py-4 bg-slate-50/50">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-[#DC2626] border border-red-100">
                  <AlertOctagon className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-[#172033]">
                    Failure Record Diagnostics
                  </h3>
                  <p className="text-[11px] text-[#64748B]">
                    Detailed error analysis and technical extraction context
                  </p>
                </div>
              </div>
              <button
                onClick={() => setInspectRecord(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto text-xs">
              {/* URL with Copy */}
              <div className="space-y-1">
                <span className="font-semibold text-[#172033] block">Target Vacancy URL:</span>
                <div className="flex items-center gap-2 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-2.5 font-mono text-[11px] text-[#172033] break-all">
                  <span className="flex-1">{inspectRecord.url}</span>
                  <button
                    onClick={() => copyToClipboard(inspectRecord.url)}
                    className="p-1 text-[#64748B] hover:text-[#2563EB] transition-colors"
                    title="Copy URL"
                  >
                    {copiedUrl ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
                  </button>
                  <a
                    href={inspectRecord.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1 text-[#64748B] hover:text-[#2563EB] transition-colors"
                    title="Open URL in new tab"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                </div>
              </div>

              {/* Grid of Attributes */}
              <div className="grid grid-cols-2 gap-4 rounded-xl border border-[#E2E8F0] bg-slate-50/50 p-4">
                <div>
                  <span className="text-[#64748B] text-[11px] block">Error Classification</span>
                  <div className="mt-1">{renderErrorTypeBadge(inspectRecord.error_type)}</div>
                </div>

                <div>
                  <span className="text-[#64748B] text-[11px] block">Source Hostname</span>
                  <span className="font-mono font-semibold text-[#172033]">
                    {inspectRecord.source_hostname || '—'}
                  </span>
                </div>

                <div>
                  <span className="text-[#64748B] text-[11px] block">Processing Stage</span>
                  <span className="font-semibold text-[#172033]">{inspectRecord.stage || 'Scraping'}</span>
                </div>

                <div>
                  <span className="text-[#64748B] text-[11px] block">Retryable Status</span>
                  <span
                    className={`font-semibold ${
                      inspectRecord.retryable === 'Yes' ? 'text-[#16A34A]' : 'text-[#64748B]'
                    }`}
                  >
                    {inspectRecord.retryable === 'Yes' ? 'Yes (Transient Network)' : 'No (Deterministic / Policy)'}
                  </span>
                </div>

                <div>
                  <span className="text-[#64748B] text-[11px] block">Extractor Module</span>
                  <span className="font-mono text-[#172033]">{inspectRecord.extractor_name || 'Generic'}</span>
                </div>

                <div>
                  <span className="text-[#64748B] text-[11px] block">Timestamp</span>
                  <span className="font-mono text-[#172033]">
                    {inspectRecord.timestamp ? new Date(inspectRecord.timestamp).toISOString() : '—'}
                  </span>
                </div>
              </div>

              {/* Complete Error Message Box */}
              <div className="space-y-1.5">
                <span className="font-semibold text-[#172033]">Full Error Message / Failure Reason:</span>
                <div className="rounded-xl border border-red-200 bg-red-50/40 p-3.5 font-mono text-[11px] text-red-950 leading-relaxed whitespace-pre-wrap">
                  {inspectRecord.error_message}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between border-t border-[#E2E8F0] px-6 py-3.5 bg-slate-50/60">
              <span className="text-[11px] text-[#64748B]">
                Logged in accordance with academic reproducibility standards
              </span>
              <div className="flex items-center gap-2">
                {inspectRecord.retryable === 'Yes' && (
                  <button
                    onClick={() => {
                      handleRetryUrls([inspectRecord.url]);
                      setInspectRecord(null);
                    }}
                    disabled={retrying}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-[#2563EB] px-3.5 py-1.5 text-xs font-semibold text-white shadow-2xs hover:bg-[#1D4ED8] transition-colors"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    Retry URL Now
                  </button>
                )}
                <button
                  onClick={() => setInspectRecord(null)}
                  className="rounded-lg border border-[#E2E8F0] bg-white px-3.5 py-1.5 text-xs font-medium text-[#172033] hover:bg-slate-50 shadow-2xs transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
