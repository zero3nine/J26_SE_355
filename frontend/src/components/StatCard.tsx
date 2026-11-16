import React from 'react';
import { Link2, CheckCircle2, AlertOctagon, Sparkles } from 'lucide-react';
import { MetricItem } from '../types/dashboard';

interface StatCardProps {
  metric: MetricItem;
  viewMode?: 'session' | 'all-time';
}

export const StatCard: React.FC<StatCardProps> = ({ metric, viewMode = 'session' }) => {
  const displayValue = viewMode === 'all-time' ? metric.total_all_time : metric.value;

  const colorStyles = {
    blue: {
      borderAccent: 'border-l-4 border-l-[#2563EB]',
      badgeBg: 'bg-blue-50',
      badgeText: 'text-[#2563EB]',
      iconBorder: 'border-blue-100',
      icon: <Link2 className="h-5 w-5 text-[#2563EB]" />,
    },
    green: {
      borderAccent: 'border-l-4 border-l-[#16A34A]',
      badgeBg: 'bg-emerald-50',
      badgeText: 'text-[#16A34A]',
      iconBorder: 'border-emerald-100',
      icon: <CheckCircle2 className="h-5 w-5 text-[#16A34A]" />,
    },
    red: {
      borderAccent: 'border-l-4 border-l-[#DC2626]',
      badgeBg: 'bg-red-50',
      badgeText: 'text-[#DC2626]',
      iconBorder: 'border-red-100',
      icon: <AlertOctagon className="h-5 w-5 text-[#DC2626]" />,
    },
    purple: {
      borderAccent: 'border-l-4 border-l-[#9333EA]',
      badgeBg: 'bg-purple-50',
      badgeText: 'text-[#9333EA]',
      iconBorder: 'border-purple-100',
      icon: <Sparkles className="h-5 w-5 text-[#9333EA]" />,
    },
  }[metric.color];

  return (
    <div
      className={`relative overflow-hidden rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md ${colorStyles.borderAccent}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-[#64748B]">
          {metric.label}
        </span>
        <div
          className={`flex h-9 w-9 items-center justify-center rounded-lg border ${colorStyles.iconBorder} ${colorStyles.badgeBg}`}
        >
          {colorStyles.icon}
        </div>
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-3xl font-bold tracking-tight text-[#172033]">
          {displayValue.toLocaleString()}
        </span>
        {viewMode === 'session' && metric.total_all_time > 0 && (
          <span className="text-[11px] text-[#64748B]">
            / {metric.total_all_time.toLocaleString()} total
          </span>
        )}
      </div>

      <div className="mt-2 flex items-center gap-1.5 text-xs text-[#64748B]">
        <span className={`inline-block h-1.5 w-1.5 rounded-full ${colorStyles.badgeBg} ${colorStyles.badgeText}`} />
        <span>{metric.trend}</span>
      </div>
    </div>
  );
};

