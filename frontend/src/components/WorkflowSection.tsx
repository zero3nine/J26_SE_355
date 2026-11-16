import React from 'react';
import {
  DownloadCloud,
  FileSearch,
  Sparkles,
  Cpu,
  Database,
  BarChart3,
  ArrowRight,
} from 'lucide-react';
import { WorkflowStep } from '../types/dashboard';

interface WorkflowSectionProps {
  onStepClick?: (step: WorkflowStep) => void;
}

const WORKFLOW_STEPS: WorkflowStep[] = [
  {
    step: 1,
    title: 'Collect job advertisements',
    description:
      'Submit vacancy URLs from approved portals. Enforces SSRF defenses, polite delays, and domain whitelisting.',
    page: '1_Collect_Data',
    status: 'Collection Stage',
  },
  {
    step: 2,
    title: 'Inspect raw records',
    description:
      'Review raw HTML DOM extracts, image flyer OCR outputs, and crawler execution manifests in real time.',
    page: '2_Raw_Data',
    status: 'Ingestion Review',
  },
  {
    step: 3,
    title: 'Clean and validate data',
    description:
      'Normalize multi-currency compensation, resolve ambiguous IT titles, standardize locations, and eliminate duplicate listings.',
    page: '3_Clean_Data',
    status: 'Normalization',
  },
  {
    step: 4,
    title: 'Extract skills using lexical and semantic methods',
    description:
      'Identify canonical technical skills through dictionary taxonomy matching and dense semantic embedding similarity.',
    page: '5_Extract_Skills',
    status: 'Skill Taxonomy',
  },
  {
    step: 5,
    title: 'Publish approved records to the master dataset',
    description:
      'Commit verified records and extraction runs to persistent SQLite storage for long-term historical traceability.',
    page: '4_Master_Dataset',
    status: 'Persistence',
  },
  {
    step: 6,
    title: 'Run analytical and validation views',
    description:
      'Generate comparative regional skill demand, temporal trends, scraper accuracy benchmarks, and statistical divergence tests.',
    page: '12_Regional_Analysis',
    status: 'Analytics & Audit',
  },
];

const getStepIcon = (step: number) => {
  const className = 'h-4 w-4 text-[#2563EB]';
  switch (step) {
    case 1:
      return <DownloadCloud className={className} />;
    case 2:
      return <FileSearch className={className} />;
    case 3:
      return <Sparkles className={className} />;
    case 4:
      return <Cpu className={className} />;
    case 5:
      return <Database className={className} />;
    case 6:
      return <BarChart3 className={className} />;
    default:
      return <ArrowRight className={className} />;
  }
};

export const WorkflowSection: React.FC<WorkflowSectionProps> = ({ onStepClick }) => {
  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-6 shadow-xs">
      <div className="border-b border-[#E2E8F0] pb-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-[#172033]">Research Data Pipeline Workflow</h2>
            <p className="mt-0.5 text-xs text-[#64748B]">
              Standardized 6-stage lifecycle for collecting, extracting, standardizing, and analyzing IT job boards data
            </p>
          </div>
          <span className="hidden rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-[#2563EB] border border-blue-100 sm:inline-block">
            Sequential Pipeline
          </span>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {WORKFLOW_STEPS.map((item) => (
          <div
            key={item.step}
            onClick={() => onStepClick && onStepClick(item)}
            className="group relative flex flex-col justify-between rounded-xl border border-[#E2E8F0] bg-[#F8FAFC]/50 p-4 transition-all duration-200 hover:border-blue-200 hover:bg-white hover:shadow-sm"
          >
            <div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-100/80 text-xs font-bold text-[#2563EB]">
                    {item.step}
                  </div>
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-blue-100 bg-white">
                    {getStepIcon(item.step)}
                  </div>
                </div>
                <span className="text-[10px] font-semibold uppercase tracking-wider text-[#64748B]">
                  {item.status}
                </span>
              </div>

              <h3 className="mt-3 text-sm font-semibold text-[#172033] group-hover:text-[#2563EB] transition-colors">
                {item.title}
              </h3>
              <p className="mt-1.5 text-xs text-[#64748B] leading-relaxed">
                {item.description}
              </p>
            </div>

            <div className="mt-4 flex items-center justify-between border-t border-[#E2E8F0]/60 pt-2.5 text-[11px] text-[#64748B]">
              <span className="font-mono text-[10px] text-slate-400">Step 0{item.step}</span>
              <span className="inline-flex items-center gap-1 font-medium text-[#2563EB] group-hover:underline">
                View stage <ArrowRight className="h-3 w-3" />
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

