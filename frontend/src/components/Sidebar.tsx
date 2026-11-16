import React from 'react';
import {
  LayoutDashboard,
  LineChart,
  DownloadCloud,
  FileText,
  Sparkles,
  Database,
  Cpu,
  CheckSquare,
  AlertOctagon,
  Globe,
  UserCheck,
  ShieldCheck,
  Network,
  Compass,
  TrendingUp,
  Briefcase,
  ExternalLink,
  RefreshCw,
} from 'lucide-react';
import { NavigationItem } from '../types/dashboard';

interface SidebarProps {
  currentPath: string;
  onNavigate: (item: NavigationItem) => void;
  isOpen?: boolean;
  onClose?: () => void;
  isScrapingActive?: boolean;
}

const DEFAULT_ITEMS: NavigationItem[] = [
  {
    id: 'research-dashboard',
    name: 'Research Dashboard',
    path: '/dashboard',
    icon: 'LayoutDashboard',
    type: 'react',
    isMigrated: true,
    badge: 'Active',
  },
  {
    id: '0-user-dashboard',
    name: '0 User Dashboard',
    path: '/pages/0_User_Dashboard',
    icon: 'LineChart',
    type: 'streamlit',
    isMigrated: false,
  },
  {
    id: '1-collect-data',
    name: '1 Collect Data',
    path: '/pages/1_Collect_Data',
    icon: 'DownloadCloud',
    type: 'react',
    isMigrated: true,
    badge: 'Active',
  },
  {
    id: '2-raw-data',
    name: '2 Raw Data',
    path: '/pages/2_Raw_Data',
    icon: 'FileText',
    type: 'react',
    isMigrated: true,
    badge: 'Active',
  },
  {
    id: '3-clean-data',
    name: '3 Clean Data',
    path: '/pages/3_Clean_Data',
    icon: 'Sparkles',
    type: 'react',
    isMigrated: true,
    badge: 'Active',
  },
  {
    id: '4-master-dataset',
    name: '4 Master Dataset',
    path: '/pages/4_Master_Dataset',
    icon: 'Database',
    type: 'streamlit',
    isMigrated: false,
  },
  {
    id: '5-extract-skills',
    name: '5 Extract Skills',
    path: '/pages/5_Extract_Skills',
    icon: 'Cpu',
    type: 'streamlit',
    isMigrated: false,
  },
  {
    id: '6-quality-report',
    name: '6 Quality Report',
    path: '/pages/6_Quality_Report',
    icon: 'CheckSquare',
    type: 'streamlit',
    isMigrated: false,
  },
  {
    id: '7-failure-logs',
    name: '7 Failure Logs',
    path: '/pages/7_Failure_Logs',
    icon: 'AlertOctagon',
    type: 'react',
    isMigrated: true,
    badge: 'Active',
  },
  {
    id: '8-external-domains',
    name: '8 External Domains',
    path: '/pages/8_External_Domains',
    icon: 'Globe',
    type: 'react',
    isMigrated: true,
    badge: 'Active',
  },
  {
    id: '9-manual-reviews',
    name: '9 Manual Reviews',
    path: '/pages/9_Manual_Reviews',
    icon: 'UserCheck',
    type: 'streamlit',
    isMigrated: false,
  },
  {
    id: '10-scraping-validation',
    name: '10 Scraping Validation',
    path: '/pages/10_Scraping_Validation',
    icon: 'ShieldCheck',
    type: 'react',
    isMigrated: true,
    badge: 'Active',
    isIndividual: true,
  },
  {
    id: '11-skill-relationship-analysis',
    name: '11 Skill Relationship Analysis',
    path: '/pages/11_Skill_Relationship_Analysis',
    icon: 'Network',
    type: 'streamlit',
    isMigrated: false,
  },
  {
    id: '12-regional-analysis',
    name: '12 Regional Analysis',
    path: '/pages/12_Regional_Analysis',
    icon: 'Compass',
    type: 'react',
    isMigrated: true,
    badge: 'Active',
    isIndividual: true,
  },
  {
    id: '13-temporal-analysis',
    name: '13 Temporal Analysis',
    path: '/pages/13_Temporal_Analysis',
    icon: 'TrendingUp',
    type: 'streamlit',
    isMigrated: false,
  },
  {
    id: '14-role-skill-analysis',
    name: '14 Role Skill Analysis',
    path: '/pages/14_Role_Skill_Analysis',
    icon: 'Briefcase',
    type: 'streamlit',
    isMigrated: false,
  },
];

const renderIcon = (iconName: string, isSelected: boolean) => {
  const className = `h-4 w-4 shrink-0 transition-colors ${
    isSelected ? 'text-[#2563EB]' : 'text-[#64748B]'
  }`;

  switch (iconName) {
    case 'LayoutDashboard':
      return <LayoutDashboard className={className} />;
    case 'LineChart':
      return <LineChart className={className} />;
    case 'DownloadCloud':
      return <DownloadCloud className={className} />;
    case 'FileText':
      return <FileText className={className} />;
    case 'Sparkles':
      return <Sparkles className={className} />;
    case 'Database':
      return <Database className={className} />;
    case 'Cpu':
      return <Cpu className={className} />;
    case 'CheckSquare':
      return <CheckSquare className={className} />;
    case 'AlertOctagon':
      return <AlertOctagon className={className} />;
    case 'Globe':
      return <Globe className={className} />;
    case 'UserCheck':
      return <UserCheck className={className} />;
    case 'ShieldCheck':
      return <ShieldCheck className={className} />;
    case 'Network':
      return <Network className={className} />;
    case 'Compass':
      return <Compass className={className} />;
    case 'TrendingUp':
      return <TrendingUp className={className} />;
    case 'Briefcase':
      return <Briefcase className={className} />;
    default:
      return <FileText className={className} />;
  }
};

export const Sidebar: React.FC<SidebarProps> = ({
  currentPath,
  onNavigate,
  isOpen = false,
  onClose,
  isScrapingActive = false,
}) => {
  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-40 bg-slate-900/30 backdrop-blur-sm md:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-[#E2E8F0] bg-white transition-transform duration-200 ease-in-out md:static md:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-20 items-center justify-between border-b border-[#E2E8F0] px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#2563EB] text-white font-bold text-sm shadow-sm">
              IT
            </div>
            <span className="font-bold text-sm tracking-wide text-[#172033] uppercase">
              Project J26-SE-355
            </span>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-[#64748B] hover:bg-slate-100 md:hidden"
              aria-label="Close navigation"
            >
              ✕
            </button>
          )}
        </div>

        {/* Navigation list */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
          {/* Quick jump to public portal */}
          <div className="px-1 pb-3">
            <button
              type="button"
              onClick={() => {
                onNavigate({
                  id: 'public-landing',
                  name: 'Public Portal',
                  path: '/',
                  icon: 'Globe',
                  type: 'react',
                  isMigrated: true,
                });
                if (onClose) onClose();
              }}
              className="group flex w-full items-center justify-between rounded-xl border border-[#E2E8F0] bg-slate-50/80 px-3 py-2 text-xs font-semibold text-[#172033] hover:bg-blue-50/80 hover:text-[#2563EB] hover:border-blue-200 transition-all shadow-2xs"
            >
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-[#2563EB] group-hover:rotate-12 transition-transform" />
                <span>Public Portal</span>
              </div>
              <span className="text-[10px] text-[#64748B] group-hover:text-[#2563EB]">← Overview</span>
            </button>
          </div>

          <div className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
            Console Navigation
          </div>

          {DEFAULT_ITEMS.map((item) => {
            const isSelected = currentPath === item.path;

            return (
              <button
                key={item.id}
                onClick={() => {
                  onNavigate(item);
                  if (onClose) onClose();
                }}
                className={`group flex w-full items-center justify-between rounded-lg px-3 py-2 text-xs font-medium transition-all duration-150 ${
                  isSelected
                    ? 'bg-blue-50/90 text-[#2563EB] font-semibold shadow-xs'
                    : 'text-[#172033] hover:bg-slate-50 hover:text-[#2563EB]'
                }`}
              >
                <div className="flex items-center gap-2.5 truncate">
                  {renderIcon(item.icon, isSelected)}
                  <span className="truncate">{item.name}</span>
                </div>

                <div className="flex items-center gap-1.5">
                  {item.path === '/pages/1_Collect_Data' && isScrapingActive ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-[#2563EB] animate-pulse">
                      <RefreshCw className="h-2.5 w-2.5 animate-spin" />
                      Scraping
                    </span>
                  ) : item.badge ? (
                    <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-[#2563EB]">
                      {item.badge}
                    </span>
                  ) : null}
                  {item.type === 'streamlit' && (
                    <span className="opacity-0 group-hover:opacity-100 transition-opacity text-[10px] text-[#64748B]">
                      <ExternalLink className="h-3 w-3" />
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {/* Sidebar Footer info */}
        <div className="border-t border-[#E2E8F0] p-4 bg-slate-50/60">
          <div className="text-[11px] font-medium text-[#64748B]">
            Research Framework
          </div>
          <div className="mt-0.5 text-xs text-[#172033] font-semibold">
            Technical Skill Identification
          </div>
          <div className="mt-1 text-[10px] text-[#64748B]">
            UI Migration Stage 1 • React 18
          </div>
        </div>
      </aside>
    </>
  );
};
