import React, { useState } from 'react';
import { StatCard } from './StatCard';
import { MetricItem } from '../types/dashboard';
import { Clock, RefreshCw } from 'lucide-react';

interface StatsGridProps {
  metrics: {
    submitted_urls: MetricItem;
    successfully_scraped: MetricItem;
    failed_skipped: MetricItem;
    clean_records: MetricItem;
  };
  latestBatch?: {
    batch_id: string;
    elapsed_seconds: number;
    started_at: string;
  } | null;
  onRefresh?: () => void;
  isLoading?: boolean;
}

export const StatsGrid: React.FC<StatsGridProps> = ({
  metrics,
  latestBatch,
  onRefresh,
  isLoading = false,
}) => {
  const [viewMode, setViewMode] = useState<'session' | 'all-time'>('session');

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-base font-bold text-[#172033]">Key Performance Indicators</h2>
          {latestBatch && (
            <span className="hidden items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-[#64748B] sm:inline-flex">
              <Clock className="h-3 w-3" />
              Latest: {latestBatch.batch_id}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-lg border border-[#E2E8F0] bg-white p-0.5 text-xs shadow-2xs">
            <button
              onClick={() => setViewMode('session')}
              className={`rounded-md px-2.5 py-1 font-medium transition-all ${
                viewMode === 'session'
                  ? 'bg-blue-50 text-[#2563EB] font-semibold'
                  : 'text-[#64748B] hover:text-[#172033]'
              }`}
            >
              Active Session
            </button>
            <button
              onClick={() => setViewMode('all-time')}
              className={`rounded-md px-2.5 py-1 font-medium transition-all ${
                viewMode === 'all-time'
                  ? 'bg-blue-50 text-[#2563EB] font-semibold'
                  : 'text-[#64748B] hover:text-[#172033]'
              }`}
            >
              All-Time Totals
            </button>
          </div>

          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isLoading}
              title="Refresh backend metrics"
              className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-[#E2E8F0] bg-white text-[#64748B] hover:bg-slate-50 hover:text-[#172033] disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin text-[#2563EB]' : ''}`} />
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard metric={metrics.submitted_urls} viewMode={viewMode} />
        <StatCard metric={metrics.successfully_scraped} viewMode={viewMode} />
        <StatCard metric={metrics.failed_skipped} viewMode={viewMode} />
        <StatCard metric={metrics.clean_records} viewMode={viewMode} />
      </div>
    </div>
  );
};

