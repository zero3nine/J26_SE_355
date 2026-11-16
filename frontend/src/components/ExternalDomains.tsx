import React, { useState, useEffect } from 'react';
import {
  Globe,
  ShieldCheck,
  ShieldAlert,
  Clock,
  CheckCircle2,
  XCircle,
  ExternalLink,
  Search,
  RefreshCw,
  Trash2,
  Plus,
  Filter,
  Check,
  Layers,
  Info,
} from 'lucide-react';
import { SecurityNotice } from './SecurityNotice';

interface QueueItem {
  source_url: string;
  external_url: string;
  source_hostname?: string;
  destination_hostname: string;
  anchor_text?: string;
  discovery_reason?: string;
  review_status: 'pending' | 'approved' | 'rejected' | string;
}

interface ExternalDomainsData {
  status: string;
  queue: QueueItem[];
  pending_hostnames: string[];
  approved_domains: string[];
  blocked_domains: string[];
  stats: {
    total_queue: number;
    pending_count: number;
    approved_count: number;
    rejected_count: number;
    whitelist_total: number;
    blacklist_total: number;
  };
}

export const ExternalDomains: React.FC = () => {
  const [data, setData] = useState<ExternalDomainsData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [selectedHost, setSelectedHost] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'queue' | 'approved' | 'blocked'>('queue');

  // Search & filter state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [whitelistSearch, setWhitelistSearch] = useState<string>('');

  // Add domain manually
  const [manualDomain, setManualDomain] = useState<string>('');
  const [isAddingManual, setIsAddingManual] = useState<boolean>(false);

  // Notifications
  const [feedback, setFeedback] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);

  const fetchDomainsData = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/external-domains');
      if (res.ok) {
        const json: ExternalDomainsData = await res.json();
        setData(json);
        if (json.pending_hostnames && json.pending_hostnames.length > 0) {
          if (!selectedHost || !json.pending_hostnames.includes(selectedHost)) {
            setSelectedHost(json.pending_hostnames[0]);
          }
        } else {
          setSelectedHost('');
        }
      } else {
        throw new Error('Failed to load external domains data');
      }
    } catch (err: any) {
      console.error('Error fetching external domains:', err);
      setFeedback({
        type: 'error',
        message: err.message || 'Unable to connect to domain governance service.',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDomainsData();
  }, []);

  // Clear feedback after 5 seconds
  useEffect(() => {
    if (feedback) {
      const timer = setTimeout(() => setFeedback(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [feedback]);

  // Handle Domain Approval
  const handleApprove = async (hostnameToApprove?: string) => {
    const host = (hostnameToApprove || selectedHost).trim();
    if (!host) return;

    setActionLoading(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/external-domains/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hostname: host }),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Failed to approve domain.');
      }

      const resJson = await res.json();
      setFeedback({
        type: 'success',
        message: resJson.message || `Domain '${host}' is approved!`,
      });
      await fetchDomainsData();
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.message || 'Domain approval failed.',
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Domain Rejection
  const handleReject = async (hostToReject: string, blockDomain: boolean = false) => {
    const host = hostToReject.trim();
    if (!host) return;

    setActionLoading(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/external-domains/reject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hostname: host, block_domain: blockDomain }),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Failed to reject domain.');
      }

      const resJson = await res.json();
      setFeedback({
        type: 'success',
        message: resJson.message || `Domain '${host}' marked as rejected.`,
      });
      await fetchDomainsData();
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.message || 'Domain rejection failed.',
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Domain Removal from Queue
  const handleRemove = async (hostname: string, targetUrl: string) => {
    setActionLoading(true);
    try {
      const res = await fetch('/api/external-domains/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hostname, external_url: targetUrl }),
      });

      if (res.ok) {
        setFeedback({
          type: 'success',
          message: `Record for '${hostname}' removed from review queue.`,
        });
        await fetchDomainsData();
      }
    } catch (err) {
      console.error('Failed to remove queue item:', err);
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Adding Whitelist Domain Manually
  const handleAddManualDomain = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanHost = manualDomain.trim().toLowerCase().replace(/^https?:\/\//, '').replace(/\/.*$/, '');
    if (!cleanHost) return;

    setIsAddingManual(true);
    try {
      const res = await fetch('/api/external-domains/add-approved', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hostname: cleanHost }),
      });

      if (res.ok) {
        setFeedback({
          type: 'success',
          message: `Domain '${cleanHost}' successfully added to approved whitelist.`,
        });
        setManualDomain('');
        await fetchDomainsData();
      } else {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Failed to add domain to whitelist.');
      }
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to add domain.',
      });
    } finally {
      setIsAddingManual(false);
    }
  };

  // Filtered queue items
  const filteredQueue = (data?.queue || []).filter((item) => {
    const matchesSearch =
      searchQuery === '' ||
      item.destination_hostname.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.source_url.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.anchor_text && item.anchor_text.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesStatus =
      statusFilter === 'all' ||
      item.review_status.toLowerCase() === statusFilter.toLowerCase();

    return matchesSearch && matchesStatus;
  });

  // Filtered whitelist domains
  const filteredWhitelist = (data?.approved_domains || []).filter((dom) =>
    whitelistSearch === '' || dom.toLowerCase().includes(whitelistSearch.toLowerCase())
  );

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-12">
      {/* 1. Shared Security Notice Banner */}
      <SecurityNotice />

      {/* 2. Page Header */}
      <div className="flex flex-col gap-3 border-b border-[#E2E8F0] pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-100 text-[#2563EB]">
              <Globe className="h-4 w-4" />
            </span>
            <h2 className="text-2xl font-bold tracking-tight text-[#172033]">
              External vacancy detail links review queue
            </h2>
          </div>
          <p className="mt-1 text-sm text-[#64748B]">
            Governance portal for third-party vacancy hostnames discovered during automated link traversal. Approved domains are authorized for cross-site detail extraction.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchDomainsData()}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-3.5 py-2 text-xs font-semibold text-[#172033] shadow-2xs hover:bg-slate-50 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 text-[#64748B] ${loading ? 'animate-spin' : ''}`} />
            Refresh Queue
          </button>
        </div>
      </div>

      {/* Feedback Toast Banner */}
      {feedback && (
        <div
          className={`flex items-center justify-between rounded-xl border p-4 text-xs font-medium shadow-xs transition-all ${
            feedback.type === 'success'
              ? 'border-emerald-200 bg-emerald-50/90 text-emerald-900'
              : 'border-red-200 bg-red-50/90 text-red-900'
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.type === 'success' ? (
              <CheckCircle2 className="h-4 w-4 text-[#16A34A] shrink-0" />
            ) : (
              <XCircle className="h-4 w-4 text-[#DC2626] shrink-0" />
            )}
            <span>{feedback.message}</span>
          </div>
          <button
            onClick={() => setFeedback(null)}
            className="text-slate-400 hover:text-slate-600 font-bold ml-4"
          >
            ✕
          </button>
        </div>
      )}

      {/* 3. Metric KPI Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {/* Pending Review */}
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-2xs border-l-4 border-l-[#D97706]">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-[#64748B]">
            <span>Pending Review</span>
            <Clock className="h-4 w-4 text-[#D97706]" />
          </div>
          <div className="mt-2 text-2xl font-bold text-[#D97706]">
            {data?.stats?.pending_count ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-[#64748B]">
            Awaiting administrator approval
          </div>
        </div>

        {/* Approved in Queue */}
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-2xs border-l-4 border-l-[#16A34A]">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-[#64748B]">
            <span>Approved in Queue</span>
            <CheckCircle2 className="h-4 w-4 text-[#16A34A]" />
          </div>
          <div className="mt-2 text-2xl font-bold text-[#16A34A]">
            {data?.stats?.approved_count ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-[#64748B]">
            Validated external detail links
          </div>
        </div>

        {/* Total Whitelist Registry */}
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-2xs border-l-4 border-l-[#2563EB]">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-[#64748B]">
            <span>Whitelist Registry</span>
            <ShieldCheck className="h-4 w-4 text-[#2563EB]" />
          </div>
          <div className="mt-2 text-2xl font-bold text-[#2563EB]">
            {data?.stats?.whitelist_total ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-[#64748B]">
            Permitted portal destinations
          </div>
        </div>

        {/* Blocked Blacklist */}
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-2xs border-l-4 border-l-[#DC2626]">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-[#64748B]">
            <span>Blocked Blacklist</span>
            <ShieldAlert className="h-4 w-4 text-[#DC2626]" />
          </div>
          <div className="mt-2 text-2xl font-bold text-[#DC2626]">
            {data?.stats?.blacklist_total ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-[#64748B]">
            SSRF & malicious domain filters
          </div>
        </div>
      </div>

      {/* 4. Primary Action: Approve External Domain Section */}
      <div className="rounded-xl border border-[#E2E8F0] bg-white p-6 shadow-xs space-y-4">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-base font-bold text-[#172033] flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-[#2563EB]" />
              Approve External Domain
            </h3>
            <p className="text-xs text-[#64748B]">
              Authorize discovered external hostnames for deep web scraping. Approvals append the domain to <code className="font-mono bg-slate-100 px-1 py-0.5 rounded text-[11px]">config/approved_domains.txt</code>.
            </p>
          </div>
        </div>

        {data?.pending_hostnames && data.pending_hostnames.length > 0 ? (
          <div className="rounded-xl border border-blue-100 bg-blue-50/40 p-4 sm:p-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="flex-1">
                <label className="block text-xs font-semibold text-[#172033] mb-1.5">
                  Select external domain to approve:
                </label>
                <div className="relative">
                  <select
                    value={selectedHost}
                    onChange={(e) => setSelectedHost(e.target.value)}
                    className="w-full rounded-lg border border-[#E2E8F0] bg-white px-3.5 py-2.5 text-xs font-medium text-[#172033] shadow-2xs focus:border-[#2563EB] focus:outline-none focus:ring-2 focus:ring-blue-100"
                  >
                    {data.pending_hostnames.map((h) => {
                      const count = data.queue.filter(
                        (q) => q.destination_hostname.toLowerCase() === h.toLowerCase()
                      ).length;
                      return (
                        <option key={h} value={h}>
                          {h} ({count} link{count !== 1 ? 's' : ''} discovered)
                        </option>
                      );
                    })}
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1 sm:pt-5">
                <button
                  type="button"
                  onClick={() => handleApprove()}
                  disabled={actionLoading || !selectedHost}
                  className="inline-flex items-center gap-2 rounded-xl bg-[#2563EB] px-5 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-[#1D4ED8] disabled:opacity-50 transition-colors"
                >
                  <ShieldCheck className="h-4 w-4" />
                  {actionLoading ? 'Processing...' : 'Approve Domain'}
                </button>

                <button
                  type="button"
                  onClick={() => handleReject(selectedHost, false)}
                  disabled={actionLoading || !selectedHost}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs font-medium text-[#64748B] hover:bg-slate-50 hover:text-[#DC2626] disabled:opacity-50 transition-colors"
                  title="Reject domain without blacklisting"
                >
                  <XCircle className="h-4 w-4" />
                  Reject
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50/70 p-4 text-xs font-medium text-[#16A34A]">
            <CheckCircle2 className="h-5 w-5 shrink-0 text-[#16A34A]" />
            <div>
              <strong>Queue Cleared:</strong> All identified external domains have been processed and approved! No pending authorization requests exist.
            </div>
          </div>
        )}
      </div>

      {/* 5. Navigation Tabs */}
      <div className="flex border-b border-[#E2E8F0]">
        <button
          onClick={() => setActiveTab('queue')}
          className={`flex items-center gap-2 border-b-2 px-5 py-3 text-xs font-semibold transition-colors ${
            activeTab === 'queue'
              ? 'border-[#2563EB] text-[#2563EB]'
              : 'border-transparent text-[#64748B] hover:text-[#172033]'
          }`}
        >
          <Layers className="h-4 w-4" />
          Review Queue
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] ${
              activeTab === 'queue'
                ? 'bg-blue-100 text-[#2563EB]'
                : 'bg-slate-100 text-[#64748B]'
            }`}
          >
            {data?.queue.length ?? 0}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('approved')}
          className={`flex items-center gap-2 border-b-2 px-5 py-3 text-xs font-semibold transition-colors ${
            activeTab === 'approved'
              ? 'border-[#2563EB] text-[#2563EB]'
              : 'border-transparent text-[#64748B] hover:text-[#172033]'
          }`}
        >
          <ShieldCheck className="h-4 w-4" />
          Approved Whitelist
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] ${
              activeTab === 'approved'
                ? 'bg-blue-100 text-[#2563EB]'
                : 'bg-slate-100 text-[#64748B]'
            }`}
          >
            {data?.approved_domains.length ?? 0}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('blocked')}
          className={`flex items-center gap-2 border-b-2 px-5 py-3 text-xs font-semibold transition-colors ${
            activeTab === 'blocked'
              ? 'border-[#2563EB] text-[#2563EB]'
              : 'border-transparent text-[#64748B] hover:text-[#172033]'
          }`}
        >
          <ShieldAlert className="h-4 w-4" />
          Blocked Blacklist
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] ${
              activeTab === 'blocked'
                ? 'bg-blue-100 text-[#2563EB]'
                : 'bg-slate-100 text-[#64748B]'
            }`}
          >
            {data?.blocked_domains.length ?? 0}
          </span>
        </button>
      </div>

      {/* 6. TAB 1: Review Queue List View */}
      {activeTab === 'queue' && (
        <div className="space-y-4">
          {/* Search & Filter Toolbar */}
          <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              {/* Search input */}
              <div className="relative flex-1">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-[#64748B]" />
                <input
                  type="text"
                  placeholder="Filter by destination host, discovery URL, or anchor text..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] pl-9 pr-3 py-2 text-xs text-[#172033] placeholder-slate-400 focus:border-[#2563EB] focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-100"
                />
              </div>

              {/* Status Filter */}
              <div className="flex items-center gap-2">
                <Filter className="h-3.5 w-3.5 text-[#64748B]" />
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="rounded-lg border border-[#E2E8F0] bg-slate-50 px-2.5 py-1.5 text-xs font-medium text-[#172033]"
                >
                  <option value="all">All Statuses ({data?.queue.length ?? 0})</option>
                  <option value="pending">Pending ({data?.stats?.pending_count ?? 0})</option>
                  <option value="approved">Approved ({data?.stats?.approved_count ?? 0})</option>
                  <option value="rejected">Rejected ({data?.stats?.rejected_count ?? 0})</option>
                </select>
              </div>
            </div>
          </div>

          {/* Cards List */}
          {filteredQueue.length > 0 ? (
            <div className="space-y-3">
              {filteredQueue.map((item, idx) => {
                const isPending = item.review_status === 'pending';
                const isApproved = item.review_status === 'approved';
                const isRejected = item.review_status === 'rejected';

                return (
                  <div
                    key={`${item.destination_hostname}-${idx}`}
                    className="group rounded-xl border border-[#E2E8F0] bg-white p-4 sm:p-5 shadow-2xs hover:shadow-xs transition-shadow space-y-3"
                  >
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2.5">
                          <Globe className="h-4 w-4 text-[#2563EB]" />
                          <span className="font-mono text-sm font-bold text-[#172033]">
                            {item.destination_hostname}
                          </span>

                          {/* Status Badge */}
                          {isPending && (
                            <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-[10px] font-semibold text-[#D97706]">
                              <Clock className="h-3 w-3" />
                              PENDING
                            </span>
                          )}
                          {isApproved && (
                            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-[10px] font-semibold text-[#16A34A]">
                              <CheckCircle2 className="h-3 w-3" />
                              APPROVED
                            </span>
                          )}
                          {isRejected && (
                            <span className="inline-flex items-center gap-1 rounded-full border border-red-200 bg-red-50 px-2.5 py-0.5 text-[10px] font-semibold text-[#DC2626]">
                              <XCircle className="h-3 w-3" />
                              REJECTED
                            </span>
                          )}
                        </div>

                        {/* Discovery Context */}
                        <div className="text-xs text-[#64748B] flex flex-wrap items-center gap-1.5 pt-0.5">
                          <span>Discovered on:</span>
                          <a
                            href={item.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 font-mono text-[#2563EB] hover:underline"
                          >
                            {item.source_url.length > 70
                              ? `${item.source_url.substring(0, 70)}...`
                              : item.source_url}
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        </div>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center gap-2 pt-1 sm:pt-0">
                        {isPending && (
                          <>
                            <button
                              onClick={() => handleApprove(item.destination_hostname)}
                              disabled={actionLoading}
                              className="inline-flex items-center gap-1 rounded-lg bg-[#2563EB] px-3 py-1.5 text-xs font-semibold text-white shadow-2xs hover:bg-[#1D4ED8] disabled:opacity-50 transition-colors"
                            >
                              <Check className="h-3.5 w-3.5" />
                              Approve
                            </button>
                            <button
                              onClick={() => handleReject(item.destination_hostname, false)}
                              disabled={actionLoading}
                              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-medium text-[#64748B] hover:text-[#DC2626] hover:bg-red-50 disabled:opacity-50 transition-colors"
                              title="Reject link"
                            >
                              <XCircle className="h-3.5 w-3.5" />
                              Reject
                            </button>
                          </>
                        )}
                        <button
                          onClick={() => handleRemove(item.destination_hostname, item.external_url)}
                          disabled={actionLoading}
                          className="rounded-lg p-1.5 text-slate-400 hover:text-[#DC2626] hover:bg-slate-100 disabled:opacity-50 transition-colors"
                          title="Remove from queue"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Additional Metadata Strip */}
                    <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-2.5 text-[11px] text-[#64748B]">
                      {item.anchor_text && (
                        <span className="rounded bg-slate-100 px-2 py-0.5 font-medium text-slate-700">
                          Anchor: "{item.anchor_text}"
                        </span>
                      )}
                      {item.discovery_reason && (
                        <span className="rounded bg-blue-50 px-2 py-0.5 font-medium text-blue-700">
                          {item.discovery_reason}
                        </span>
                      )}
                      {item.source_hostname && (
                        <span className="rounded bg-slate-50 px-2 py-0.5 text-slate-600">
                          Source Portal: {item.source_hostname}
                        </span>
                      )}
                      {item.external_url && (
                        <a
                          href={item.external_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="ml-auto inline-flex items-center gap-1 text-[11px] font-medium text-[#2563EB] hover:underline"
                        >
                          Inspect Candidate Link <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            /* Empty State */
            <div className="rounded-xl border border-[#E2E8F0] bg-white p-12 text-center shadow-xs space-y-3">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-50 text-[#64748B] border border-slate-200">
                <ShieldCheck className="h-6 w-6 text-emerald-600" />
              </div>
              <h4 className="text-base font-bold text-[#172033]">No Pending External Domains</h4>
              <p className="mx-auto max-w-md text-xs text-[#64748B] leading-relaxed">
                All discovered external domains have been reviewed, or no new external domains have been detected.
              </p>
              <div className="pt-2 text-[11px] text-[#64748B]">
                New external domains will automatically appear here when candidate job postings are discovered during multi-site crawling runs.
              </div>
            </div>
          )}
        </div>
      )}

      {/* 7. TAB 2: Approved Whitelist Registry */}
      {activeTab === 'approved' && (
        <div className="space-y-4">
          {/* Add Trusted Domain Form */}
          <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-3">
            <h4 className="text-sm font-bold text-[#172033] flex items-center gap-2">
              <Plus className="h-4 w-4 text-[#2563EB]" />
              Authorize New Domain to Whitelist
            </h4>
            <form onSubmit={handleAddManualDomain} className="flex gap-2">
              <input
                type="text"
                placeholder="e.g. careers.google.com or jobsearch.sg"
                value={manualDomain}
                onChange={(e) => setManualDomain(e.target.value)}
                className="flex-1 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-2 text-xs text-[#172033] placeholder-slate-400 focus:border-[#2563EB] focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-100"
              />
              <button
                type="submit"
                disabled={isAddingManual || !manualDomain.trim()}
                className="inline-flex items-center gap-1.5 rounded-lg bg-[#2563EB] px-4 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-[#1D4ED8] disabled:opacity-50 transition-colors"
              >
                <Plus className="h-3.5 w-3.5" />
                {isAddingManual ? 'Adding...' : 'Authorize Domain'}
              </button>
            </form>
          </div>

          {/* Search bar for Whitelist */}
          <div className="flex items-center justify-between gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-[#64748B]" />
              <input
                type="text"
                placeholder="Search approved domains registry..."
                value={whitelistSearch}
                onChange={(e) => setWhitelistSearch(e.target.value)}
                className="w-full rounded-lg border border-[#E2E8F0] bg-white pl-9 pr-3 py-2 text-xs text-[#172033] placeholder-slate-400 focus:border-[#2563EB] focus:outline-none focus:ring-1 focus:ring-blue-100"
              />
            </div>
            <span className="text-xs font-semibold text-[#64748B]">
              {filteredWhitelist.length} Approved Portal{filteredWhitelist.length !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Grid of Approved Whitelist Domains */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
            {filteredWhitelist.map((domain) => (
              <div
                key={domain}
                className="flex items-center justify-between rounded-xl border border-[#E2E8F0] bg-white p-3.5 shadow-2xs hover:border-blue-200 transition-colors"
              >
                <div className="flex items-center gap-2.5 truncate">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-[#16A34A] border border-emerald-100">
                    <CheckCircle2 className="h-4 w-4" />
                  </div>
                  <span className="font-mono text-xs font-semibold text-[#172033] truncate">
                    {domain}
                  </span>
                </div>
                <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-[#16A34A] border border-emerald-100">
                  Approved
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 8. TAB 3: Blocked Blacklist */}
      {activeTab === 'blocked' && (
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-6 shadow-xs space-y-4">
          <div className="flex items-start gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-[#DC2626] border border-red-100 shrink-0">
              <ShieldAlert className="h-4 w-4" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-[#172033]">
                Malicious & Blocked Domain Blacklist
              </h4>
              <p className="text-xs text-[#64748B] mt-0.5">
                Domains in this registry are blocked unconditionally from all HTTP/HTTPS traversal and Playwright rendering to prevent SSRF vulnerabilities and unwanted crawling. Configured in <code className="font-mono bg-slate-100 px-1 py-0.5 rounded text-[11px]">config/blocked_domains.txt</code>.
              </p>
            </div>
          </div>

          {data?.blocked_domains && data.blocked_domains.length > 0 ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 pt-2">
              {data.blocked_domains.map((dom) => (
                <div
                  key={dom}
                  className="flex items-center justify-between rounded-xl border border-red-200 bg-red-50/50 p-3.5"
                >
                  <span className="font-mono text-xs font-semibold text-[#DC2626]">{dom}</span>
                  <span className="rounded-md bg-red-100 px-2 py-0.5 text-[10px] font-semibold text-[#DC2626]">
                    Blocked
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-8 text-center text-xs text-[#64748B]">
              <Info className="mx-auto h-5 w-5 text-slate-400 mb-1" />
              No explicitly blocked domains currently recorded in the blacklist. All private, loopback, and cloud metadata IPs remain protected by default SSRF security rules.
            </div>
          )}
        </div>
      )}
    </div>
  );
};

