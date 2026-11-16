import React, { useState, useEffect } from 'react';
import {
  FileText,
  Search,
  Download,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Database,
  ArrowRight,
  RefreshCw,
  Eye,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  X,
} from 'lucide-react';
import { SecurityNotice } from './SecurityNotice';

interface RawDataProps {
  onNavigateToCollect: () => void;
}

interface RawRecord {
  job_id: string;
  source_job_id?: string;
  job_title_raw?: string;
  company_raw?: string;
  country_raw?: string;
  location_raw?: string;
  job_description_raw?: string;
  posted_date_raw?: string;
  closing_date_raw?: string;
  employment_type_raw?: string;
  source_platform?: string;
  source_hostname?: string;
  source_url?: string;
  extractor_name?: string;
  extraction_method?: string;
  extraction_status?: string;
  extraction_confidence?: string | number;
  description_type?: string;
  scraped_at?: string;
  fetch_method?: string;
  rendering_used?: string | boolean;
  failure_reason?: string;
  error_message?: string;
  [key: string]: any;
}

interface RawDataResponse {
  status: string;
  has_data: boolean;
  total_records: number;
  filtered_records: number;
  batch_id: string;
  page: number;
  page_size: number;
  total_pages: number;
  records: RawRecord[];
  available_batches: Array<{
    batch_id: string;
    filename: string;
    size_kb: number;
    mtime: string;
  }>;
  filter_options: {
    companies: string[];
    sources: string[];
    extractors: string[];
  };
  overview: {
    total: number;
    by_source: Record<string, number>;
    by_status: Record<string, number>;
    by_extractor: Record<string, number>;
  };
}

export const RawData: React.FC<RawDataProps> = ({ onNavigateToCollect }) => {
  const [data, setData] = useState<RawDataResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedRecord, setSelectedRecord] = useState<RawRecord | null>(null);

  // Filters
  const [search, setSearch] = useState<string>('');
  const [company, setCompany] = useState<string>('All');
  const [source, setSource] = useState<string>('All');
  const [extractor, setExtractor] = useState<string>('All');
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);

  // Batch loader selector
  const [selectedBatchToLoad, setSelectedBatchToLoad] = useState<string>('');
  const [isBatchLoading, setIsBatchLoading] = useState<boolean>(false);

  const fetchRawData = async (resetPage = false) => {
    try {
      setLoading(true);
      const currentPage = resetPage ? 1 : page;
      if (resetPage) setPage(1);

      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: pageSize.toString(),
      });
      if (search.trim()) params.append('search', search.trim());
      if (company !== 'All') params.append('company', company);
      if (source !== 'All') params.append('source', source);
      if (extractor !== 'All') params.append('extractor', extractor);

      const res = await fetch(`/api/raw-data?${params.toString()}`);
      if (res.ok) {
        const json = await res.json();
        setData(json);
        if (json.records && json.records.length > 0 && !selectedRecord) {
          setSelectedRecord(json.records[0]);
        }
      }
    } catch (err) {
      console.error('Failed to load raw data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRawData();
  }, [page, pageSize, company, source, extractor]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchRawData(true);
    }, 350);
    return () => clearTimeout(timer);
  }, [search]);

  const handleLoadBatch = async (batchId: string) => {
    if (!batchId) return;
    try {
      setIsBatchLoading(true);
      const res = await fetch('/api/raw-data/load-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch_id: batchId }),
      });
      if (res.ok) {
        setSelectedRecord(null);
        await fetchRawData(true);
      }
    } catch (err) {
      console.error('Failed to load batch:', err);
    } finally {
      setIsBatchLoading(false);
    }
  };

  const handleResetFilters = () => {
    setSearch('');
    setCompany('All');
    setSource('All');
    setExtractor('All');
    setPage(1);
  };

  const getStatusBadge = (status?: string) => {
    const s = (status || '').toLowerCase();
    if (s === 'success') {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-[#16A34A] border border-emerald-200">
          <CheckCircle2 className="h-3 w-3" />
          Success
        </span>
      );
    }
    if (s === 'partial') {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-[#2563EB] border border-blue-200">
          <Sparkles className="h-3 w-3" />
          Partial
        </span>
      );
    }
    if (s === 'manual_review') {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-[#D97706] border border-amber-200">
          <AlertTriangle className="h-3 w-3" />
          Review
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-[11px] font-semibold text-[#DC2626] border border-red-200">
        <XCircle className="h-3 w-3" />
        {status || 'Failed'}
      </span>
    );
  };

  const formatConfidence = (val?: string | number) => {
    if (val === undefined || val === null || val === '') return '—';
    const num = typeof val === 'number' ? val : parseFloat(val);
    if (isNaN(num)) return String(val);
    return `${Math.round(num * 100)}%`;
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-2 border-b border-[#E2E8F0] pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-100 text-[#2563EB]">
              <FileText className="h-4 w-4" />
            </span>
            <h2 className="text-2xl font-bold tracking-tight text-[#172033]">
              Raw Collected Data
            </h2>
          </div>
          <p className="mt-1 text-sm text-[#64748B]">
            Inspect, search, and verify raw job vacancy crawls, unstructured HTML text, and extraction provenance.
          </p>
        </div>

        {data?.has_data && (
          <div className="flex items-center gap-2">
            <a
              href="/api/raw-data/download"
              download
              className="inline-flex items-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-3.5 py-2 text-xs font-semibold text-[#172033] shadow-2xs hover:bg-slate-50 transition-colors"
            >
              <Download className="h-3.5 w-3.5 text-[#2563EB]" />
              Download Raw CSV
            </a>
            <button
              onClick={() => handleLoadBatch('clear')}
              title="Reset session raw data to empty"
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-[#64748B] hover:bg-slate-50 hover:text-red-600 transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset
            </button>
          </div>
        )}
      </div>

      {/* Security Warning Notice */}
      <SecurityNotice />

      {/* Main Content Area */}
      {loading && !data ? (
        <div className="flex h-64 items-center justify-center rounded-xl border border-[#E2E8F0] bg-white p-8">
          <div className="flex flex-col items-center gap-2 text-[#64748B]">
            <RefreshCw className="h-6 w-6 animate-spin text-[#2563EB]" />
            <span className="text-sm">Loading raw records from backend session...</span>
          </div>
        </div>
      ) : !data?.has_data ? (
        /* Empty State */
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-10 text-center shadow-xs space-y-6">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-50 text-[#64748B] border border-slate-200">
            <Database className="h-8 w-8 text-slate-400" />
          </div>

          <div className="space-y-1.5">
            <h3 className="text-xl font-bold text-[#172033]">No Raw Data Available</h3>
            <p className="mx-auto max-w-lg text-sm text-[#64748B] leading-relaxed">
              No raw data collected in session. Use Collect Data to scrape current vacancies or import a historical dataset.
            </p>
          </div>

          <div className="pt-2 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <button
              onClick={onNavigateToCollect}
              className="inline-flex items-center gap-2 rounded-xl bg-[#2563EB] px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#1D4ED8] transition-all"
            >
              Go to Collect Data
              <ArrowRight className="h-4 w-4" />
            </button>

            {data?.available_batches && data.available_batches.length > 0 && (
              <div className="flex items-center gap-2 text-xs text-[#64748B]">
                <span>or load past batch:</span>
                <select
                  value={selectedBatchToLoad}
                  onChange={(e) => setSelectedBatchToLoad(e.target.value)}
                  className="rounded-lg border border-[#E2E8F0] bg-slate-50 px-2.5 py-1.5 text-xs text-[#172033]"
                >
                  <option value="">Select a saved batch...</option>
                  {data.available_batches.map((b) => (
                    <option key={b.batch_id} value={b.batch_id}>
                      {b.filename} ({b.size_kb} KB)
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => handleLoadBatch(selectedBatchToLoad)}
                  disabled={!selectedBatchToLoad || isBatchLoading}
                  className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-[#2563EB] hover:bg-blue-100 disabled:opacity-50"
                >
                  {isBatchLoading ? 'Loading...' : 'Load Batch'}
                </button>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Available Data State */
        <div className="space-y-6">
          {/* Data Overview Cards */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-2xs border-l-4 border-l-[#2563EB]">
              <div className="text-xs font-semibold uppercase tracking-wider text-[#64748B]">
                Total Raw Records
              </div>
              <div className="mt-1 text-2xl font-bold text-[#172033]">
                {data.total_records.toLocaleString()}
              </div>
              <div className="mt-1 text-[11px] text-[#64748B]">
                {data.filtered_records !== data.total_records
                  ? `${data.filtered_records} match active filters`
                  : 'Active session dataset'}
              </div>
            </div>

            <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-2xs border-l-4 border-l-[#16A34A]">
              <div className="text-xs font-semibold uppercase tracking-wider text-[#64748B]">
                Successful Extractions
              </div>
              <div className="mt-1 text-2xl font-bold text-[#16A34A]">
                {(data.overview.by_status['success'] || 0) + (data.overview.by_status['partial'] || 0)}
              </div>
              <div className="mt-1 text-[11px] text-[#64748B]">
                {Math.round(
                  (((data.overview.by_status['success'] || 0) + (data.overview.by_status['partial'] || 0)) /
                    (data.total_records || 1)) *
                    100
                )}
                % extraction rate
              </div>
            </div>

            <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-2xs border-l-4 border-l-[#9333EA]">
              <div className="text-xs font-semibold uppercase tracking-wider text-[#64748B]">
                Unique Portals / Sources
              </div>
              <div className="mt-1 text-2xl font-bold text-[#9333EA]">
                {Object.keys(data.overview.by_source).length}
              </div>
              <div className="mt-1 text-[11px] text-[#64748B] truncate">
                {Object.keys(data.overview.by_source).slice(0, 3).join(', ') || 'N/A'}
              </div>
            </div>

            <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-2xs border-l-4 border-l-[#D97706]">
              <div className="text-xs font-semibold uppercase tracking-wider text-[#64748B]">
                Active Batch ID
              </div>
              <div className="mt-1 font-mono text-sm font-bold text-[#172033] truncate">
                {data.batch_id || 'Active Session'}
              </div>
              <div className="mt-1 text-[11px] text-[#64748B]">
                {Object.keys(data.overview.by_extractor).length} extractor methods
              </div>
            </div>
          </div>

          {/* Filters & Search Toolbar */}
          <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-[#64748B]" />
                <input
                  type="text"
                  placeholder="Search by title / company..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] pl-9 pr-3 py-2 text-xs text-[#172033] placeholder-slate-400 focus:border-[#2563EB] focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-100"
                />
              </div>

              {/* Company Filter */}
              <div>
                <select
                  value={company}
                  onChange={(e) => {
                    setCompany(e.target.value);
                    setPage(1);
                  }}
                  className="w-full rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-2 text-xs text-[#172033] focus:border-[#2563EB] focus:bg-white focus:outline-none"
                >
                  <option value="All">All Companies ({data.filter_options.companies.length})</option>
                  {data.filter_options.companies.map((c) => (
                    <option key={c} value={c}>
                      {c.length > 30 ? c.slice(0, 28) + '...' : c}
                    </option>
                  ))}
                </select>
              </div>

              {/* Source Filter */}
              <div>
                <select
                  value={source}
                  onChange={(e) => {
                    setSource(e.target.value);
                    setPage(1);
                  }}
                  className="w-full rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-2 text-xs text-[#172033] focus:border-[#2563EB] focus:bg-white focus:outline-none"
                >
                  <option value="All">All Sources / Portals ({data.filter_options.sources.length})</option>
                  {data.filter_options.sources.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>

              {/* Extractor Filter */}
              <div className="flex items-center gap-2">
                <select
                  value={extractor}
                  onChange={(e) => {
                    setExtractor(e.target.value);
                    setPage(1);
                  }}
                  className="w-full rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-2 text-xs text-[#172033] focus:border-[#2563EB] focus:bg-white focus:outline-none"
                >
                  <option value="All">All Methods ({data.filter_options.extractors.length})</option>
                  {data.filter_options.extractors.map((ext) => (
                    <option key={ext} value={ext}>
                      {ext}
                    </option>
                  ))}
                </select>

                {(search || company !== 'All' || source !== 'All' || extractor !== 'All') && (
                  <button
                    onClick={handleResetFilters}
                    title="Clear all filters"
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-slate-200 text-[#64748B] hover:bg-slate-100 hover:text-[#172033]"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Raw Records Table Card */}
          <div className="rounded-xl border border-[#E2E8F0] bg-white shadow-xs overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-[#E2E8F0] bg-[#F8FAFC] text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                    <th className="px-4 py-3">Job ID</th>
                    <th className="px-4 py-3">Job Title</th>
                    <th className="px-4 py-3">Company</th>
                    <th className="px-4 py-3">Source / Host</th>
                    <th className="px-4 py-3">Posted Date</th>
                    <th className="px-4 py-3">Extractor</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Conf</th>
                    <th className="px-4 py-3 text-center">Inspect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E2E8F0]">
                  {data.records.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-8 text-center text-xs text-[#64748B]">
                        No records match the current filter criteria.
                      </td>
                    </tr>
                  ) : (
                    data.records.map((r, idx) => {
                      const isSelected = selectedRecord?.job_id === r.job_id;
                      return (
                        <tr
                          key={r.job_id || idx}
                          onClick={() => setSelectedRecord(r)}
                          className={`cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-blue-50/70'
                              : 'hover:bg-slate-50'
                          }`}
                        >
                          <td className="px-4 py-3 font-mono text-[11px] text-[#2563EB] whitespace-nowrap">
                            {r.job_id}
                          </td>
                          <td className="px-4 py-3 font-medium text-[#172033] max-w-xs truncate" title={r.job_title_raw}>
                            {r.job_title_raw || '—'}
                          </td>
                          <td className="px-4 py-3 text-[#64748B] max-w-[150px] truncate" title={r.company_raw}>
                            {r.company_raw || '—'}
                          </td>
                          <td className="px-4 py-3 text-[#64748B] whitespace-nowrap">
                            <span className="font-medium text-[#172033]">{r.source_platform}</span>
                            {r.source_hostname && (
                              <span className="block text-[10px] text-slate-400">{r.source_hostname}</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-[#64748B] whitespace-nowrap">
                            {r.posted_date_raw || '—'}
                          </td>
                          <td className="px-4 py-3 text-[#64748B] whitespace-nowrap">
                            <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-700">
                              {r.extractor_name || r.description_type || 'generic'}
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            {getStatusBadge(r.extraction_status)}
                          </td>
                          <td className="px-4 py-3 text-[11px] font-mono text-[#64748B] whitespace-nowrap">
                            {formatConfidence(r.extraction_confidence)}
                          </td>
                          <td className="px-4 py-3 text-center whitespace-nowrap">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedRecord(r);
                              }}
                              className={`rounded p-1 transition-colors ${
                                isSelected
                                  ? 'bg-blue-100 text-[#2563EB]'
                                  : 'text-[#64748B] hover:bg-slate-100 hover:text-[#2563EB]'
                              }`}
                              title="Inspect full details"
                            >
                              <Eye className="h-4 w-4" />
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination bar */}
            <div className="flex items-center justify-between border-t border-[#E2E8F0] px-4 py-3 text-xs text-[#64748B]">
              <div className="flex items-center gap-2">
                <span>
                  Showing {Math.min((data.page - 1) * data.page_size + 1, data.filtered_records)} to{' '}
                  {Math.min(data.page * data.page_size, data.filtered_records)} of{' '}
                  <strong>{data.filtered_records}</strong> entries
                </span>
                <span className="text-slate-300">|</span>
                <div className="flex items-center gap-1">
                  <span>Page size:</span>
                  <select
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value));
                      setPage(1);
                    }}
                    className="rounded border border-[#E2E8F0] bg-white px-2 py-0.5 text-xs text-[#172033]"
                  >
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
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

          {/* Record Inspection Detail Panel */}
          {selectedRecord && (
            <div className="rounded-xl border border-[#E2E8F0] bg-white p-6 shadow-xs space-y-4">
              <div className="flex flex-col gap-2 border-b border-[#E2E8F0] pb-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-100 text-[#2563EB]">
                    <Eye className="h-4 w-4" />
                  </span>
                  <div>
                    <h3 className="text-base font-bold text-[#172033]">
                      {selectedRecord.job_title_raw || 'Untitled Job'}
                    </h3>
                    <p className="text-xs text-[#64748B]">
                      {selectedRecord.company_raw || 'Unknown Employer'} • ID: <code>{selectedRecord.job_id}</code>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {selectedRecord.source_url && (
                    <a
                      href={selectedRecord.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 rounded-lg border border-[#E2E8F0] bg-slate-50 px-2.5 py-1 text-xs font-medium text-[#2563EB] hover:bg-slate-100"
                    >
                      Original Source <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                  {getStatusBadge(selectedRecord.extraction_status)}
                </div>
              </div>

              {/* Provenance & Metadata Chips Grid */}
              <div className="space-y-1.5">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                  Record Provenance & Execution Metadata
                </span>
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="rounded-md bg-blue-50 px-2.5 py-1 font-medium text-[#2563EB] border border-blue-100">
                    Host: <strong>{selectedRecord.source_hostname || selectedRecord.source_platform || 'N/A'}</strong>
                  </span>
                  <span className="rounded-md bg-purple-50 px-2.5 py-1 font-medium text-[#7C3AED] border border-purple-100">
                    Country: <strong>{selectedRecord.country_raw || selectedRecord.country || 'N/A'}</strong>
                  </span>
                  <span className="rounded-md bg-slate-100 px-2.5 py-1 font-medium text-slate-700">
                    Extractor: <strong>{selectedRecord.extractor_name || 'N/A'}</strong> ({selectedRecord.extraction_method || 'none'})
                  </span>
                  <span className="rounded-md bg-slate-100 px-2.5 py-1 font-medium text-slate-700">
                    Posting Date: <strong>{selectedRecord.posted_date_raw || 'Unknown'}</strong>
                  </span>
                  <span className="rounded-md bg-slate-100 px-2.5 py-1 font-medium text-slate-700">
                    Collected: <strong>{selectedRecord.scraped_at || 'Unknown'}</strong>
                  </span>
                  <span className="rounded-md bg-slate-100 px-2.5 py-1 font-medium text-slate-700">
                    Fetch: <strong>{selectedRecord.fetch_method || 'http'}</strong> (Rendered: {String(selectedRecord.rendering_used || 'False')})
                  </span>
                  <span className="rounded-md bg-slate-100 px-2.5 py-1 font-medium text-slate-700">
                    Type: <strong>{selectedRecord.description_type || 'html_text'}</strong>
                  </span>
                  {selectedRecord.failure_reason && (
                    <span className="rounded-md bg-amber-50 px-2.5 py-1 font-medium text-[#D97706] border border-amber-200">
                      Diagnostic: {selectedRecord.failure_reason}
                    </span>
                  )}
                  {selectedRecord.error_message && (
                    <span className="rounded-md bg-red-50 px-2.5 py-1 font-medium text-[#DC2626] border border-red-200">
                      Error: {selectedRecord.error_message}
                    </span>
                  )}
                </div>
              </div>

              {/* Raw Description Content */}
              <div className="space-y-1.5 pt-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-[#172033]">Raw Description Content (Read-Only)</span>
                  <span className="font-mono text-[11px] text-[#64748B]">
                    {selectedRecord.job_description_raw?.length || 0} characters
                  </span>
                </div>
                <div className="h-64 overflow-y-auto rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-4 font-mono text-xs text-[#172033] leading-relaxed whitespace-pre-wrap select-text">
                  {selectedRecord.job_description_raw || (
                    <span className="text-slate-400 italic">No raw description available for this record.</span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
