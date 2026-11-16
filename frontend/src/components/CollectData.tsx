import React, { useState, useEffect, useRef } from 'react';
import {
  DownloadCloud,
  Globe,
  Sliders,
  Play,
  Square,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ArrowRight,
  RefreshCw,
  Upload,
} from 'lucide-react';

export interface ScrapingStatusInfo {
  active: boolean;
  batchId?: string;
  progress?: {
    current: number;
    total: number;
    message: string;
    ratio: number;
  };
  result?: {
    batch_id: string;
    records_collected: number;
    completed_at?: string;
  } | null;
}

interface CollectDataProps {
  onNavigateToRawData?: () => void;
  onStatusChange?: (status: ScrapingStatusInfo) => void;
}

export const CollectData: React.FC<CollectDataProps> = ({ onNavigateToRawData, onStatusChange }) => {
  const [mode, setMode] = useState<'live' | 'historical'>('live');

  // URL Input State
  const [urlsInput, setUrlsInput] = useState<string>('');
  const [saveToFile, setSaveToFile] = useState<boolean>(false);
  const [validating, setValidating] = useState<boolean>(false);
  const [validationResult, setValidationResult] = useState<{
    valid: string[];
    rejected: Record<string, string>;
    approvedHostnames: string[];
    unapprovedHostnames: string[];
  } | null>(null);

  // Configuration State
  const [targetValid, setTargetValid] = useState<number>(50);
  const [maxRequests, setMaxRequests] = useState<number>(120);
  const [maxTime, setMaxTime] = useState<number>(300);
  const [politeDelay, setPoliteDelay] = useState<number>(2.0);
  const [useFallback, setUseFallback] = useState<boolean>(false);
  const [useOcr, setUseOcr] = useState<boolean>(true);
  const [crawlAllPages, setCrawlAllPages] = useState<boolean>(false);
  const [datasetBehavior, setDatasetBehavior] = useState<'Append' | 'Replace'>('Append');

  // Scraping Progress & Execution State
  const [isScraping, setIsScraping] = useState<boolean>(false);
  const [progress, setProgress] = useState<{
    current: number;
    total: number;
    message: string;
    ratio: number;
  }>({ current: 0, total: 0, message: 'Idle', ratio: 0.0 });
  const [logs, setLogs] = useState<string[]>([]);
  const [currentBatchId, setCurrentBatchId] = useState<string>('');
  const [completedResult, setCompletedResult] = useState<{
    batch_id: string;
    records_collected: number;
    completed_at: string;
  } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Historical Import State
  const [histSource, setHistSource] = useState<string>('Moratuwa research dataset');
  const [histCountry, setHistCountry] = useState<string>('Sri Lanka');

  const terminalRef = useRef<HTMLDivElement>(null);

  // Load sample URLs from urls.txt on initial load (without overwriting existing input)
  useEffect(() => {
    const loadSampleUrls = async () => {
      try {
        const res = await fetch('/api/collect/urls-txt');
        if (res.ok) {
          const data = await res.json();
          if (data.urls_text) {
            setUrlsInput((prev) => (prev && prev.trim().length > 0 ? prev : data.urls_text.trim()));
          }
        }
      } catch (err) {
        console.error('Failed to load sample URLs:', err);
      }
    };
    loadSampleUrls();
  }, []);

  // Sync scraping status with backend on component mount (handles direct visits, tab switching, and page reloads)
  useEffect(() => {
    const checkInitialStatus = async () => {
      try {
        const res = await fetch('/api/collect/status');
        if (res.ok) {
          const data = await res.json();
          if (data.active) {
            setIsScraping(true);
            if (data.progress) setProgress(data.progress);
            if (data.logs) setLogs(data.logs);
            if (data.batch_id) setCurrentBatchId(data.batch_id);
            onStatusChange?.({
              active: true,
              batchId: data.batch_id,
              progress: data.progress,
              result: null,
            });
          } else if (data.result) {
            setCompletedResult(data.result);
            if (data.progress) setProgress(data.progress);
            if (data.logs) setLogs(data.logs);
            if (data.batch_id) setCurrentBatchId(data.batch_id);
            onStatusChange?.({
              active: false,
              batchId: data.batch_id,
              progress: data.progress,
              result: data.result,
            });
          } else if (data.logs && data.logs.length > 0) {
            setLogs(data.logs);
            if (data.progress) setProgress(data.progress);
            if (data.batch_id) setCurrentBatchId(data.batch_id);
          }
        }
      } catch (err) {
        console.error('Failed to check initial scrape status:', err);
      }
    };
    checkInitialStatus();
  }, []);

  // Auto-validate whenever URLs change (debounced)
  useEffect(() => {
    const lines = urlsInput
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => l && !l.startsWith('#'));

    if (lines.length === 0) {
      setValidationResult(null);
      return;
    }

    const timer = setTimeout(async () => {
      setValidating(true);
      try {
        const res = await fetch('/api/collect/validate-urls', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ urls: lines }),
        });
        if (res.ok) {
          const data = await res.json();
          setValidationResult({
            valid: data.valid_urls,
            rejected: data.rejected_urls,
            approvedHostnames: data.approved_hostnames,
            unapprovedHostnames: data.unapproved_hostnames,
          });
        }
      } catch (err) {
        console.error('URL validation error:', err);
      } finally {
        setValidating(false);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [urlsInput]);

  // Polling for scraping job status
  useEffect(() => {
    let pollInterval: any = null;

    if (isScraping) {
      pollInterval = setInterval(async () => {
        try {
          const res = await fetch('/api/collect/status');
          if (res.ok) {
            const data = await res.json();
            setIsScraping(data.active);
            if (data.progress) setProgress(data.progress);
            if (data.logs) setLogs(data.logs);
            if (data.batch_id) setCurrentBatchId(data.batch_id);

            if (data.result) {
              setCompletedResult(data.result);
            }
            if (data.error) {
              setErrorMessage(data.error);
            }

            onStatusChange?.({
              active: data.active,
              batchId: data.batch_id,
              progress: data.progress,
              result: data.result,
            });
          }
        } catch (err) {
          console.error('Failed to poll scraping status:', err);
        }
      }, 800);
    }

    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [isScraping, onStatusChange]);

  // Scroll terminal to bottom when new logs arrive
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  const handleStartScrape = async () => {
    const lines = urlsInput
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => l && !l.startsWith('#'));

    if (lines.length === 0) return;

    setErrorMessage(null);
    setCompletedResult(null);
    setIsScraping(true);
    onStatusChange?.({
      active: true,
      batchId: '',
      progress: { current: 0, total: lines.length, message: 'Initiating crawler pipeline...', ratio: 0.0 },
      result: null,
    });

    try {
      const res = await fetch('/api/collect/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          urls: lines,
          target_valid: targetValid,
          max_requests: maxRequests,
          max_time: maxTime,
          polite_delay: politeDelay,
          fallback: useFallback,
          ocr: useOcr,
          crawl_all_pages: crawlAllPages,
          dataset_behavior: datasetBehavior === 'Append' ? 'Append to current raw data' : 'Replace current raw data',
          save_to_file: saveToFile,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to start scraping pipeline');
      }

      const data = await res.json();
      setCurrentBatchId(data.batch_id);
      onStatusChange?.({
        active: true,
        batchId: data.batch_id,
        progress: { current: 0, total: lines.length, message: 'Crawler launched', ratio: 0.0 },
        result: null,
      });
    } catch (err: any) {
      setErrorMessage(err.message || 'An error occurred while launching the crawler');
      setIsScraping(false);
      onStatusChange?.({
        active: false,
        result: null,
      });
    }
  };

  const handleCancelScrape = async () => {
    try {
      await fetch('/api/collect/cancel', { method: 'POST' });
    } catch (err) {
      console.error('Failed to request cancellation:', err);
    }
  };

  const loadSampleURLs = () => {
    setUrlsInput(
      'https://itpro.lk/jobs/software-engineering/\n' +
      'https://www.itpro.lk/jobs/quality-assurance/\n' +
      'https://www.topjobs.lk/employer/JobAdvertismentServlet?rid=0&ac=0000000375&jc=0001540527'
    );
  };

  const detectedCount = urlsInput
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith('#')).length;

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col gap-3 border-b border-[#E2E8F0] pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-100 text-[#2563EB]">
              <DownloadCloud className="h-4 w-4" />
            </span>
            <h2 className="text-2xl font-bold tracking-tight text-[#172033]">
              Collect Job Advertisements
            </h2>
          </div>
          <p className="mt-1 text-sm text-[#64748B]">
            Execute multi-site web scraping with polite crawling, SSRF validation, and DOM extraction, or import historical data.
          </p>
        </div>

        {/* Mode Selector */}
        <div className="inline-flex rounded-xl border border-[#E2E8F0] bg-white p-1 shadow-2xs">
          <button
            onClick={() => setMode('live')}
            className={`flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
              mode === 'live'
                ? 'bg-blue-50 text-[#2563EB] shadow-xs'
                : 'text-[#64748B] hover:text-[#172033]'
            }`}
          >
            <Globe className="h-3.5 w-3.5" />
            Live Scraping
          </button>
          <button
            onClick={() => setMode('historical')}
            className={`flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
              mode === 'historical'
                ? 'bg-blue-50 text-[#2563EB] shadow-xs'
                : 'text-[#64748B] hover:text-[#172033]'
            }`}
          >
            <Upload className="h-3.5 w-3.5" />
            Historical Data Import
          </button>
        </div>
      </div>

      {mode === 'live' ? (
        <div className="space-y-6">
          {/* Main URL Submission Card */}
          <div className="rounded-xl border border-[#E2E8F0] bg-white p-6 shadow-xs">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="text-base font-bold text-[#172033]">Submit Target Vacancy URLs</h3>
                <p className="text-xs text-[#64748B]">
                  Enter individual job posting URLs or listing search queries (one URL per line).
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={loadSampleURLs}
                  className="rounded-lg border border-[#E2E8F0] bg-slate-50 px-2.5 py-1 text-xs font-medium text-[#172033] hover:bg-slate-100 transition-colors"
                >
                  Load Sample URLs
                </button>
                {urlsInput && (
                  <button
                    type="button"
                    onClick={() => setUrlsInput('')}
                    className="rounded-lg px-2.5 py-1 text-xs font-medium text-[#64748B] hover:text-red-600 transition-colors"
                  >
                    Clear
                  </button>
                )}
                <span className="inline-flex items-center rounded-md bg-blue-50 px-2.5 py-1 text-xs font-semibold text-[#2563EB]">
                  {detectedCount} URL{detectedCount !== 1 ? 's' : ''} detected
                </span>
              </div>
            </div>

            {/* Textarea */}
            <div className="mt-4">
              <textarea
                value={urlsInput}
                onChange={(e) => setUrlsInput(e.target.value)}
                placeholder={
                  "https://www.itpro.lk/jobs/quality-assurance/\n" +
                  "https://www.topjobs.lk/employer/JobAdvertismentServlet?rid=0&ac=0000000375&jc=0001540527\n" +
                  "https://www.timesjobs.com/candidate/job-detail.html?jobId=12345"
                }
                rows={6}
                className="w-full rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-3.5 font-mono text-xs text-[#172033] placeholder-slate-400 focus:border-[#2563EB] focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 transition-all"
              />
            </div>

            {/* Validation Feedback Strip */}
            {validationResult && (
              <div className="mt-3 space-y-2">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2.5 py-1 font-semibold text-[#16A34A] border border-emerald-100">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    {validationResult.valid.length} Validated for Crawl
                  </span>
                  {Object.keys(validationResult.rejected).length > 0 && (
                    <span className="inline-flex items-center gap-1 rounded-md bg-red-50 px-2.5 py-1 font-semibold text-[#DC2626] border border-red-100">
                      <XCircle className="h-3.5 w-3.5" />
                      {Object.keys(validationResult.rejected).length} Rejected (Security / DNS)
                    </span>
                  )}
                  {validationResult.approvedHostnames.length > 0 && (
                    <span className="text-[11px] text-[#64748B]">
                      Approved Portals: <strong>{validationResult.approvedHostnames.join(', ')}</strong>
                    </span>
                  )}
                </div>

                {/* Show Rejected Reasons */}
                {Object.keys(validationResult.rejected).length > 0 && (
                  <div className="rounded-lg border border-red-200 bg-red-50/60 p-3 text-xs text-[#DC2626] space-y-1">
                    <div className="font-semibold flex items-center gap-1.5">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      Rejected URLs (will be omitted from crawl):
                    </div>
                    {Object.entries(validationResult.rejected).map(([u, reason]) => (
                      <div key={u} className="font-mono text-[11px] truncate">
                        • {u} — <span className="text-red-700">{reason}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="mt-3 flex items-center gap-2">
              <input
                type="checkbox"
                id="save_to_file"
                checked={saveToFile}
                onChange={(e) => setSaveToFile(e.target.checked)}
                className="h-4 w-4 rounded border-[#E2E8F0] text-[#2563EB] focus:ring-blue-200"
              />
              <label htmlFor="save_to_file" className="text-xs text-[#64748B] cursor-pointer">
                Save submitted URLs to <code className="text-slate-700 font-semibold">urls.txt</code>
              </label>
            </div>
          </div>

          {/* Crawl Run Configuration Accordion/Card */}
          <div className="rounded-xl border border-[#E2E8F0] bg-white p-6 shadow-xs">
            <div className="flex items-center gap-2 border-b border-[#E2E8F0] pb-3">
              <Sliders className="h-4 w-4 text-[#2563EB]" />
              <h3 className="text-base font-bold text-[#172033]">Crawler Run Configuration</h3>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2">
              {/* Target Valid IT Jobs */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs font-semibold text-[#172033]">
                  <span>Target Valid IT Jobs</span>
                  <span className="text-[#2563EB] font-bold">{targetValid}</span>
                </div>
                <input
                  type="range"
                  min={5}
                  max={200}
                  step={5}
                  value={targetValid}
                  onChange={(e) => setTargetValid(Number(e.target.value))}
                  className="w-full accent-[#2563EB]"
                />
                <span className="text-[11px] text-[#64748B]">Stop traversal when this many valid IT jobs are collected.</span>
              </div>

              {/* Maximum Requests Budget */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs font-semibold text-[#172033]">
                  <span>Maximum Requests Budget</span>
                  <span className="text-[#2563EB] font-bold">{maxRequests}</span>
                </div>
                <input
                  type="range"
                  min={10}
                  max={500}
                  step={10}
                  value={maxRequests}
                  onChange={(e) => setMaxRequests(Number(e.target.value))}
                  className="w-full accent-[#2563EB]"
                />
                <span className="text-[11px] text-[#64748B]">Safety ceiling preventing runaway HTTP traversal.</span>
              </div>

              {/* Maximum Duration */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs font-semibold text-[#172033]">
                  <span>Maximum Duration</span>
                  <span className="text-[#2563EB] font-bold">{maxTime}s</span>
                </div>
                <input
                  type="range"
                  min={30}
                  max={1800}
                  step={30}
                  value={maxTime}
                  onChange={(e) => setMaxTime(Number(e.target.value))}
                  className="w-full accent-[#2563EB]"
                />
                <span className="text-[11px] text-[#64748B]">Absolute execution timeout in seconds.</span>
              </div>

              {/* Polite Delay */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs font-semibold text-[#172033]">
                  <span>Polite Crawl Delay</span>
                  <span className="text-[#2563EB] font-bold">{politeDelay.toFixed(1)}s</span>
                </div>
                <input
                  type="range"
                  min={0.5}
                  max={10.0}
                  step={0.5}
                  value={politeDelay}
                  onChange={(e) => setPoliteDelay(Number(e.target.value))}
                  className="w-full accent-[#2563EB]"
                />
                <span className="text-[11px] text-[#64748B]">Inter-request pause to respect academic web etiquette.</span>
              </div>
            </div>

            {/* Toggles */}
            <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 border-t border-[#E2E8F0] pt-4">
              <label className="flex items-center gap-2.5 text-xs text-[#172033] cursor-pointer">
                <input
                  type="checkbox"
                  checked={useOcr}
                  onChange={(e) => setUseOcr(e.target.checked)}
                  className="h-4 w-4 rounded border-[#E2E8F0] text-[#2563EB]"
                />
                <span>Run Advertisement Image OCR</span>
              </label>

              <label className="flex items-center gap-2.5 text-xs text-[#172033] cursor-pointer">
                <input
                  type="checkbox"
                  checked={useFallback}
                  onChange={(e) => setUseFallback(e.target.checked)}
                  className="h-4 w-4 rounded border-[#E2E8F0] text-[#2563EB]"
                />
                <span>Playwright Browser Fallback</span>
              </label>

              <label className="flex items-center gap-2.5 text-xs text-[#172033] cursor-pointer">
                <input
                  type="checkbox"
                  checked={crawlAllPages}
                  onChange={(e) => setCrawlAllPages(e.target.checked)}
                  className="h-4 w-4 rounded border-[#E2E8F0] text-[#2563EB]"
                />
                <span>Temporal: keep paging past target</span>
              </label>
            </div>

            {/* Dataset Behavior */}
            <div className="mt-4 flex items-center gap-4 text-xs">
              <span className="font-semibold text-[#172033]">Dataset Behavior:</span>
              <label className="inline-flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="behavior"
                  value="Append"
                  checked={datasetBehavior === 'Append'}
                  onChange={() => setDatasetBehavior('Append')}
                  className="text-[#2563EB]"
                />
                <span className="text-[#64748B]">Append to current raw data</span>
              </label>
              <label className="inline-flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="behavior"
                  value="Replace"
                  checked={datasetBehavior === 'Replace'}
                  onChange={() => setDatasetBehavior('Replace')}
                  className="text-[#2563EB]"
                />
                <span className="text-[#64748B]">Replace current raw data</span>
              </label>
            </div>
          </div>

          {/* Trigger Scraping Action Area */}
          <div className="flex items-center gap-4">
            <button
              onClick={handleStartScrape}
              disabled={isScraping || detectedCount === 0 || validating}
              className="inline-flex items-center gap-2 rounded-xl bg-[#2563EB] px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-[#1D4ED8] focus:outline-none disabled:opacity-50 transition-all"
            >
              {isScraping ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Crawler Executing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-white" />
                  ⚡ Scrape Submitted URLs
                </>
              )}
            </button>

            {isScraping && (
              <button
                onClick={handleCancelScrape}
                className="inline-flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-[#DC2626] hover:bg-red-100 transition-colors"
              >
                <Square className="h-3.5 w-3.5 fill-[#DC2626]" />
                Cancel Crawl Run
              </button>
            )}
          </div>

          {/* Live Progress Bar & Status */}
          {(isScraping || logs.length > 0) && (
            <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="relative flex h-2.5 w-2.5">
                    {isScraping && (
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75"></span>
                    )}
                    <span
                      className={`relative inline-flex h-2.5 w-2.5 rounded-full ${
                        isScraping ? 'bg-[#2563EB]' : 'bg-emerald-500'
                      }`}
                    ></span>
                  </span>
                  <span className="text-xs font-bold text-[#172033]">
                    {isScraping ? 'Data-Ops Collection Pipeline In Progress' : 'Pipeline Execution Finished'}
                  </span>
                  {currentBatchId && (
                    <span className="font-mono text-[11px] text-[#64748B]">
                      ({currentBatchId})
                    </span>
                  )}
                </div>

                <span className="font-mono text-xs font-semibold text-[#2563EB]">
                  {Math.round(progress.ratio * 100)}%
                </span>
              </div>

              {/* Progress bar */}
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full bg-[#2563EB] transition-all duration-300"
                  style={{ width: `${Math.round(progress.ratio * 100)}%` }}
                />
              </div>

              {/* Terminal Logs View */}
              <div
                ref={terminalRef}
                className="h-48 overflow-y-auto rounded-lg border border-slate-800 bg-[#020617] p-3.5 font-mono text-xs text-slate-300 space-y-1"
              >
                {logs.length === 0 ? (
                  <div className="text-slate-500 italic">No output received yet...</div>
                ) : (
                  logs.map((line, idx) => (
                    <div key={idx} className="leading-relaxed">
                      {line}
                    </div>
                  ))
                )}
              </div>

              {/* Completion Banner */}
              {completedResult && (
                <div className="flex flex-col gap-2 rounded-lg border border-emerald-200 bg-emerald-50/80 p-3.5 text-xs text-emerald-950 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <strong className="font-semibold text-[#16A34A]">✓ Crawl Complete:</strong>{' '}
                    Collected <strong>{completedResult.records_collected}</strong> raw job records.
                    Batch ID: <code className="font-mono text-[11px]">{completedResult.batch_id}</code>
                  </div>
                  {onNavigateToRawData && (
                    <button
                      onClick={onNavigateToRawData}
                      className="inline-flex items-center gap-1 font-semibold text-[#2563EB] hover:underline"
                    >
                      Inspect in Raw Data <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              )}

              {errorMessage && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-[#DC2626]">
                  <strong>Error:</strong> {errorMessage}
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        /* Historical Data Import View */
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-6 shadow-xs space-y-5">
          <div>
            <h3 className="text-base font-bold text-[#172033]">Import Historical Job Advertisements</h3>
            <p className="text-xs text-[#64748B]">
              Import an existing dataset from a research repository or past collection run. Imported records enter the exact same cleaning and skill-extraction workflow.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-[#172033]">Dataset Source</label>
              <select
                value={histSource}
                onChange={(e) => setHistSource(e.target.value)}
                className="w-full rounded-lg border border-[#E2E8F0] bg-slate-50 p-2 text-xs text-[#172033]"
              >
                <option value="Moratuwa research dataset">Moratuwa research dataset</option>
                <option value="Techmap export">Techmap export</option>
                <option value="Other dataset">Other dataset</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-[#172033]">Default Country for Missing Values</label>
              <input
                type="text"
                value={histCountry}
                onChange={(e) => setHistCountry(e.target.value)}
                className="w-full rounded-lg border border-[#E2E8F0] bg-slate-50 p-2 text-xs text-[#172033]"
              />
            </div>
          </div>

          <div className="rounded-xl border-2 border-dashed border-[#E2E8F0] p-8 text-center bg-slate-50/50">
            <Upload className="mx-auto h-8 w-8 text-[#64748B]" />
            <div className="mt-2 text-xs font-medium text-[#172033]">
              Upload CSV or Excel dataset (.csv, .xlsx)
            </div>
            <div className="mt-1 text-[11px] text-[#64748B]">
              Standardized mapping of Job Title, Company, Description, and Source URL will be applied.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
