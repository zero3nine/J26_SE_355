import React from 'react';
import { Briefcase, RefreshCw, CheckCircle2, Globe } from 'lucide-react';
import { ScrapingStatusInfo } from './CollectData';

interface HeaderProps {
  onToggleSidebar?: () => void;
  scrapingStatus?: ScrapingStatusInfo | null;
  onNavigateToCollect?: () => void;
  onNavigateToRawData?: () => void;
  onNavigateToHome?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onToggleSidebar,
  scrapingStatus,
  onNavigateToCollect,
  onNavigateToRawData,
  onNavigateToHome,
}) => {
  return (
    <header className="sticky top-0 z-30 flex h-20 w-full items-center justify-between border-b border-[#E2E8F0] bg-white px-6 md:px-8 shadow-xs">
      <div className="flex items-center gap-4">
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="md:hidden inline-flex items-center justify-center rounded-lg p-2 text-[#64748B] hover:bg-slate-100 focus:outline-none"
            aria-label="Toggle navigation"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        )}
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-[#2563EB] border border-blue-100">
            <Briefcase className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl md:text-2xl font-bold tracking-tight text-[#172033]">
              IT Job Advertisement Data Collector
            </h1>
            <p className="text-xs md:text-sm text-[#64748B]">
              Multi-site academic console for scraping, cleaning, and preparing IT job boards data
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {onNavigateToHome && (
          <button
            type="button"
            onClick={onNavigateToHome}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-3 py-1.5 text-xs font-semibold text-[#172033] shadow-2xs hover:bg-slate-50 hover:text-[#2563EB] hover:border-blue-200 transition-colors"
            title="Return to Public Landing Page & Research Overview"
          >
            <Globe className="h-3.5 w-3.5 text-[#2563EB]" />
            <span className="hidden sm:inline">Public Portal</span>
          </button>
        )}

        {/* Background Scraping Active Pill */}
        {scrapingStatus?.active && (
          <button
            type="button"
            onClick={onNavigateToCollect}
            className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50/90 px-3.5 py-1.5 text-xs font-semibold text-[#2563EB] shadow-2xs hover:bg-blue-100 transition-all cursor-pointer"
            title="Scraping in progress. Click to view Collect Data console."
          >
            <RefreshCw className="h-3.5 w-3.5 animate-spin text-[#2563EB]" />
            <span className="hidden sm:inline">Scraping in Background:</span>
            <span className="font-mono">
              {scrapingStatus.progress ? `${Math.round((scrapingStatus.progress.ratio || 0) * 100)}%` : 'Running'}
            </span>
          </button>
        )}

        {/* Scrape Completed Pill */}
        {!scrapingStatus?.active && scrapingStatus?.result && (
          <button
            type="button"
            onClick={onNavigateToRawData}
            className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3.5 py-1.5 text-xs font-semibold text-[#16A34A] shadow-2xs hover:bg-emerald-100 transition-all cursor-pointer"
            title="Scrape finished! Click to inspect raw records."
          >
            <CheckCircle2 className="h-3.5 w-3.5 text-[#16A34A]" />
            <span className="hidden sm:inline">Scrape Complete:</span>
            <span>{scrapingStatus.result.records_collected} jobs</span>
          </button>
        )}

        {/* System Active Badge */}
        <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50/80 px-3.5 py-1.5 text-xs font-semibold text-[#16A34A] shadow-2xs">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-[#16A34A]"></span>
          </span>
          <span className="tracking-wide">System Active</span>
        </div>
      </div>
    </header>
  );
};
