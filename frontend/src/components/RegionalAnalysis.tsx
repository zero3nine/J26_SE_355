import React, { useState, useEffect } from 'react';
import {
  Compass,
  RefreshCw,
  Layers,
  ChevronDown,
  ChevronUp,
  Download,
  CheckCircle2,
  AlertTriangle,
  Info,
  BarChart3,
  DollarSign,
  ShieldAlert,
  Sliders,
  Briefcase,
  FileSpreadsheet,
} from 'lucide-react';
import { SecurityNotice } from './SecurityNotice';

// Country visual styling config
const COUNTRY_CONFIG: Record<
  string,
  { label: string; flag: string; bg: string; text: string; border: string; hex: string }
> = {
  'Sri Lanka': {
    label: 'Sri Lanka (Focal)',
    flag: '🇱🇰',
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    border: 'border-blue-200',
    hex: '#2563EB',
  },
  India: {
    label: 'India',
    flag: '🇮🇳',
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-200',
    hex: '#D97706',
  },
  Singapore: {
    label: 'Singapore',
    flag: '🇸🇬',
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
    hex: '#16A34A',
  },
  Malaysia: {
    label: 'Malaysia',
    flag: '🇲🇾',
    bg: 'bg-purple-50',
    text: 'text-purple-700',
    border: 'border-purple-200',
    hex: '#9333EA',
  },
};

const TARGET_COUNTRIES_LIST = ['Sri Lanka', 'India', 'Singapore', 'Malaysia'];

// ==============================================================================
// Typical Grouped Bar Chart (Clustered Vertical Bars with Shared Axes & Legend)
// ==============================================================================
interface BarChartProps {
  skills: string[];
  chartData: any[];
}

const TypicalGroupedBarChart: React.FC<BarChartProps> = ({ skills, chartData }) => {
  const [hovered, setHovered] = useState<{
    skill: string;
    category: string;
    country: string;
    demand_pct: number;
    mention_count: number;
    eligible_ads_denominator: number;
    ci_lower_95: number;
    ci_upper_95: number;
    x: number;
    y: number;
  } | null>(null);

  if (!skills || skills.length === 0) {
    return <div className="p-8 text-center text-xs text-slate-400">No skill demand records meet current criteria.</div>;
  }

  // Find max pct in the displayed subset
  let maxPct = 0;
  chartData.forEach((r) => {
    if (skills.includes(r.skill_name)) {
      maxPct = Math.max(maxPct, Number(r.demand_pct || 0));
    }
  });

  const yMax = Math.min(100, Math.max(20, Math.ceil((maxPct * 1.15) / 10) * 10));
  const ticks = [0, 0.25, 0.5, 0.75, 1.0].map((t) => Math.round(t * yMax));

  // Geometry
  const height = 390;
  const marginTop = 30;
  const marginBottom = 95;
  const marginLeft = 60;
  const marginRight = 30;
  const plotHeight = height - marginTop - marginBottom;

  const groupWidth = Math.max(58, Math.floor(860 / skills.length));
  const svgWidth = marginLeft + marginRight + skills.length * groupWidth;

  const barGap = 2;
  const clusterWidth = groupWidth * 0.76;
  const barWidth = Math.max(6, (clusterWidth - (TARGET_COUNTRIES_LIST.length - 1) * barGap) / TARGET_COUNTRIES_LIST.length);
  const clusterOffset = (groupWidth - (TARGET_COUNTRIES_LIST.length * barWidth + (TARGET_COUNTRIES_LIST.length - 1) * barGap)) / 2;

  return (
    <div className="relative w-full overflow-x-auto rounded-lg border border-[#E2E8F0] bg-white p-2">
      <div style={{ width: `${Math.max(svgWidth, 860)}px`, position: 'relative' }}>
        <svg
          viewBox={`0 0 ${Math.max(svgWidth, 860)} ${height}`}
          style={{ width: `${Math.max(svgWidth, 860)}px`, height: `${height}px` }}
          className="font-sans select-none block"
        >
          {/* Y Axis Grid Lines & Ticks */}
          {ticks.map((tickVal) => {
            const y = marginTop + plotHeight - (tickVal / yMax) * plotHeight;
            return (
              <g key={tickVal}>
                <line
                  x1={marginLeft}
                  x2={Math.max(svgWidth, 860) - marginRight}
                  y1={y}
                  y2={y}
                  stroke="#E2E8F0"
                  strokeDasharray={tickVal === 0 ? undefined : '3 3'}
                />
                <text
                  x={marginLeft - 8}
                  y={y + 4}
                  textAnchor="end"
                  className="text-[10px] fill-[#64748B] font-mono font-medium"
                >
                  {tickVal}%
                </text>
              </g>
            );
          })}

          {/* Y Axis Title */}
          <text
            x={-(marginTop + plotHeight / 2)}
            y={16}
            transform="rotate(-90)"
            textAnchor="middle"
            className="text-[11px] font-semibold fill-[#64748B]"
          >
            Skill Demand (% of Eligible Ads)
          </text>

          {/* X Axis Baseline */}
          <line
            x1={marginLeft}
            x2={Math.max(svgWidth, 860) - marginRight}
            y1={marginTop + plotHeight}
            y2={marginTop + plotHeight}
            stroke="#94A3B8"
            strokeWidth="1.5"
          />

          {/* Skill Clusters */}
          {skills.map((skillName, i) => {
            const groupStartX = marginLeft + i * groupWidth;
            const skillRows = chartData.filter((r) => r.skill_name === skillName);
            const category = skillRows[0]?.category || '';

            return (
              <g key={skillName}>
                {/* Vertical Bars for each country */}
                {TARGET_COUNTRIES_LIST.map((cName, j) => {
                  const row = skillRows.find((r) => r.country === cName);
                  const pct = row ? Number(row.demand_pct || 0) : 0;
                  const mentions = row ? row.mention_count || 0 : 0;
                  const denom = row ? row.eligible_ads_denominator || 0 : 0;
                  const ciLow = row ? row.ci_lower_95 || 0 : 0;
                  const ciHigh = row ? row.ci_upper_95 || 0 : 0;
                  const conf = COUNTRY_CONFIG[cName] || { hex: '#2563EB' };

                  const barX = groupStartX + clusterOffset + j * (barWidth + barGap);
                  const barH = pct > 0 ? Math.max(2, (pct / yMax) * plotHeight) : 0;
                  const barY = marginTop + plotHeight - barH;

                  return (
                    <rect
                      key={cName}
                      x={barX}
                      y={barY}
                      width={barWidth}
                      height={barH}
                      fill={conf.hex}
                      rx="2"
                      className="cursor-pointer transition-opacity hover:opacity-80"
                      onMouseEnter={() => {
                        setHovered({
                          skill: skillName,
                          category,
                          country: cName,
                          demand_pct: pct,
                          mention_count: mentions,
                          eligible_ads_denominator: denom,
                          ci_lower_95: ciLow,
                          ci_upper_95: ciHigh,
                          x: barX + barWidth / 2,
                          y: barY,
                        });
                      }}
                      onMouseLeave={() => setHovered(null)}
                    />
                  );
                })}

                {/* X Axis Skill Label Rotated */}
                <text
                  x={groupStartX + groupWidth / 2}
                  y={marginTop + plotHeight + 14}
                  transform={`rotate(-45, ${groupStartX + groupWidth / 2}, ${marginTop + plotHeight + 14})`}
                  textAnchor="end"
                  className="text-[11px] font-medium fill-[#172033]"
                >
                  {skillName}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Floating Hover Tooltip */}
        {hovered && (
          <div
            className={`pointer-events-none absolute z-30 -translate-x-1/2 rounded-lg border border-slate-700 bg-slate-900/95 px-3.5 py-2.5 text-xs text-white shadow-xl backdrop-blur-xs min-w-[210px] ${
              hovered.y < 130 ? 'translate-y-4' : '-translate-y-full -mt-2'
            }`}
            style={{
              left: `${hovered.x}px`,
              top: `${hovered.y}px`,
            }}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold text-sky-400">{hovered.skill}</span>
              <span className="text-[10px] text-slate-400 font-mono">{hovered.category}</span>
            </div>
            <div className="mt-1 border-t border-slate-700 pt-1.5 space-y-1 text-[11px]">
              <div className="flex justify-between">
                <span className="text-slate-300">Labor Market:</span>
                <span className="font-semibold text-white">
                  {COUNTRY_CONFIG[hovered.country]?.flag} {hovered.country}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-300">Demand Rate:</span>
                <span className="font-bold font-mono text-emerald-400">{hovered.demand_pct.toFixed(1)}%</span>
              </div>
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>Mentions (k):</span>
                <span className="font-mono">k={hovered.mention_count} / N={hovered.eligible_ads_denominator}</span>
              </div>
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>Wilson 95% CI:</span>
                <span className="font-mono">[{hovered.ci_lower_95}%, {hovered.ci_upper_95}%]</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ==============================================================================
// Typical 2D Skill Demand Heatmap (Continuous Matrix Grid of Solid Tiles)
// ==============================================================================
interface HeatmapProps {
  skills: string[];
  chartData: any[];
}

const TypicalSkillDemandHeatmap: React.FC<HeatmapProps> = ({ skills, chartData }) => {
  const [hoveredCell, setHoveredCell] = useState<{
    skill: string;
    category: string;
    country: string;
    demand_pct: number;
    mention_count: number;
    eligible_ads_denominator: number;
    ci_lower_95: number;
    ci_upper_95: number;
    is_unobserved: boolean;
  } | null>(null);

  if (!skills || skills.length === 0) {
    return <div className="p-8 text-center text-xs text-slate-400">No skill demand records meet current criteria.</div>;
  }

  // Calculate max percentage across displayed skills
  let maxPct = 0;
  chartData.forEach((r) => {
    if (skills.includes(r.skill_name)) {
      maxPct = Math.max(maxPct, Number(r.demand_pct || 0));
    }
  });

  const getContinuousBlue = (pct: number) => {
    if (pct <= 0) {
      return { bg: '#F8FAFC', text: '#94A3B8' };
    }
    const domainMax = Math.max(maxPct, 25);
    const ratio = Math.min(1, Math.max(0, pct / domainMax));

    // Continuous smooth interpolation from ice blue (#EFF6FF: 239, 246, 255)
    // to deep academic cobalt (#1E3A8A: 30, 58, 138)
    const r = Math.round(239 + ratio * (30 - 239));
    const g = Math.round(246 + ratio * (58 - 246));
    const b = Math.round(255 + ratio * (138 - 255));

    const bg = `rgb(${r}, ${g}, ${b})`;
    const text = ratio > 0.42 ? '#FFFFFF' : '#1E3A8A';
    return { bg, text };
  };

  return (
    <div className="space-y-3">
      {/* Legend for Heatmap Intensity Bar */}
      <div className="flex items-center justify-end gap-2 text-[11px] text-[#64748B]">
        <span className="font-medium">Demand Rate Intensity:</span>
        <div className="flex items-center gap-1.5 font-mono text-[10px]">
          <span className="rounded px-1.5 py-0.5 border border-[#E2E8F0] bg-[#F8FAFC] text-slate-400">0%</span>
          <div className="h-3 w-32 rounded border border-slate-200 bg-gradient-to-r from-[#EFF6FF] via-[#60A5FA] to-[#1E3A8A]"></div>
          <span className="font-semibold text-[#172033]">{Math.round(maxPct)}%+</span>
        </div>
      </div>

      {/* Heatmap Matrix Grid */}
      <div className="overflow-x-auto border border-[#E2E8F0] rounded-xl bg-white shadow-2xs">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="border-b border-[#E2E8F0] bg-slate-50 text-[11px] font-bold text-[#172033]">
              <th className="py-2.5 px-4 text-left w-52">Canonical Technical Skill</th>
              <th className="py-2.5 px-3 text-left w-36 font-semibold text-[#64748B]">Category</th>
              {TARGET_COUNTRIES_LIST.map((c) => (
                <th key={c} className="py-2.5 px-4 text-center font-bold min-w-[110px]">
                  {COUNTRY_CONFIG[c]?.flag} {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E2E8F0]">
            {skills.map((skillName) => {
              const skillRows = chartData.filter((r) => r.skill_name === skillName);
              const category = skillRows[0]?.category || '—';

              return (
                <tr key={skillName} className="hover:bg-slate-50/40">
                  <td className="py-2 px-4 font-semibold text-[#172033] border-r border-[#E2E8F0]">
                    {skillName}
                  </td>
                  <td className="py-2 px-3 text-[#64748B] text-[11px] truncate max-w-[140px] border-r border-[#E2E8F0]">
                    {category}
                  </td>
                  {TARGET_COUNTRIES_LIST.map((cName) => {
                    const row = skillRows.find((r) => r.country === cName);
                    const pct = row ? Number(row.demand_pct || 0) : 0;
                    const mentions = row ? row.mention_count || 0 : 0;
                    const denom = row ? row.eligible_ads_denominator || 0 : 0;
                    const ciLow = row ? row.ci_lower_95 || 0 : 0;
                    const ciHigh = row ? row.ci_upper_95 || 0 : 0;
                    const isUnobserved = !row || pct === 0;

                    const { bg, text } = getContinuousBlue(pct);
                    const isSelected = hoveredCell?.skill === skillName && hoveredCell?.country === cName;

                    return (
                      <td
                        key={cName}
                        className="p-0 border border-slate-200/80 text-center relative"
                        onMouseEnter={() =>
                          setHoveredCell({
                            skill: skillName,
                            category,
                            country: cName,
                            demand_pct: pct,
                            mention_count: mentions,
                            eligible_ads_denominator: denom,
                            ci_lower_95: ciLow,
                            ci_upper_95: ciHigh,
                            is_unobserved: isUnobserved,
                          })
                        }
                        onMouseLeave={() => setHoveredCell(null)}
                      >
                        <div
                          className={`flex h-10 w-full items-center justify-center font-mono font-bold text-xs transition-all cursor-pointer ${
                            isSelected ? 'ring-2 ring-blue-600 ring-inset z-10' : ''
                          }`}
                          style={{ backgroundColor: bg, color: text }}
                        >
                          {pct.toFixed(1)}%
                        </div>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Heatmap Tooltip Detail Box */}
      {hoveredCell && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 rounded-lg border border-blue-200 bg-blue-50/80 px-4 py-2.5 text-xs text-[#172033] shadow-xs">
          <div className="flex items-center gap-2">
            <span className="font-bold text-[#2563EB]">{hoveredCell.skill}</span>
            <span className="text-[#64748B]">({hoveredCell.category})</span>
            <span>•</span>
            <span className="font-semibold">
              {COUNTRY_CONFIG[hoveredCell.country]?.flag} {hoveredCell.country}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-4 font-mono text-[11px]">
            <span>
              Demand: <strong className="text-[#2563EB]">{hoveredCell.demand_pct.toFixed(1)}%</strong>
            </span>
            <span>
              Mentions: <strong>k={hoveredCell.mention_count} / N={hoveredCell.eligible_ads_denominator}</strong>
            </span>
            <span>
              95% Wilson CI: <strong>[{hoveredCell.ci_lower_95}%, {hoveredCell.ci_upper_95}%]</strong>
            </span>
            <span className="rounded bg-white px-2 py-0.5 border border-blue-200 text-[10px] font-semibold text-blue-800">
              {hoveredCell.is_unobserved ? 'Unobserved / Zero Count' : 'Validated Sample'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

// ==============================================================================
// Typical 4x4 Country Similarity Matrix Heatmap (Continuous Solid Matrix)
// ==============================================================================
const SIMILARITY_METRIC_INFO: Record<
  string,
  {
    title: string;
    shortTitle: string;
    desc: string;
    minLabel: string;
    maxLabel: string;
  }
> = {
  cosine_similarity: {
    title: 'Cosine Similarity',
    shortTitle: 'Cosine Sim',
    desc: 'Proportional canonical skill vector angle alignment (0.0000 to 1.0000). Reflects structural concordance in national skill priorities.',
    minLabel: '0.00',
    maxLabel: '1.0000',
  },
  jaccard_top10_similarity: {
    title: 'Jaccard Overlap Index (Top 10)',
    shortTitle: 'Jaccard Top-10',
    desc: 'Intersection-over-Union of the top-10 most frequently demanded canonical technical skills (0.0000 to 1.0000).',
    minLabel: '0.00',
    maxLabel: '1.0000',
  },
  spearman_rank_correlation: {
    title: 'Spearman Rank Correlation',
    shortTitle: 'Spearman Rank',
    desc: 'Monotonic concordance of skill demand rank orders across markets (-1.0000 to +1.0000). Invariant to baseline ad volume.',
    minLabel: '≤0.00',
    maxLabel: '1.0000',
  },
};

interface SimHeatmapProps {
  metricKey: 'cosine_similarity' | 'jaccard_top10_similarity' | 'spearman_rank_correlation';
  matrixData: any;
  countries: string[];
  pairwise: any[];
  compact?: boolean;
}

const TypicalSimilarityMatrixHeatmap: React.FC<SimHeatmapProps> = ({
  metricKey,
  matrixData,
  countries,
  pairwise,
  compact = false,
}) => {
  const [hoveredCell, setHoveredCell] = useState<{
    c1: string;
    c2: string;
    val: number;
    sampleA?: number;
    sampleB?: number;
    isSparse?: boolean;
  } | null>(null);

  const info = SIMILARITY_METRIC_INFO[metricKey] || {
    title: 'Similarity Metric',
    shortTitle: 'Score',
    desc: '',
    minLabel: '0.00',
    maxLabel: '1.0000',
  };

  const getContinuousSimColor = (val: number) => {
    if (val === null || val === undefined || isNaN(val)) {
      return { bg: '#F8FAFC', text: '#94A3B8' };
    }

    let ratio: number;
    if (metricKey === 'spearman_rank_correlation') {
      if (val <= 0) {
        return { bg: '#F1F5F9', text: '#64748B' };
      }
      ratio = Math.min(1, Math.max(0, val / 1.0));
    } else {
      ratio = Math.min(1, Math.max(0, val / 1.0));
    }

    // Continuous interpolation from ice blue (#EFF6FF: 239, 246, 255)
    // to deep academic navy (#1E3A8A: 30, 58, 138)
    const r = Math.round(239 + ratio * (30 - 239));
    const g = Math.round(246 + ratio * (58 - 246));
    const b = Math.round(255 + ratio * (138 - 255));

    const bg = `rgb(${r}, ${g}, ${b})`;
    const text = ratio > 0.45 ? '#FFFFFF' : '#1E3A8A';
    return { bg, text };
  };

  const activeCountries = countries && countries.length > 0 ? countries : TARGET_COUNTRIES_LIST;

  return (
    <div className="space-y-3">
      {/* Header & Gradient Legend */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E2E8F0] pb-3">
        <div>
          <h4 className="text-sm font-bold text-[#172033]">
            {info.title} Matrix Heatmap (4×4 Symmetric)
          </h4>
          <p className="text-[11px] text-[#64748B]">{info.desc}</p>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-[#64748B]">
          <span className="font-medium">Intensity:</span>
          <div className="flex items-center gap-1.5 font-mono text-[10px]">
            <span className="rounded px-1.5 py-0.5 border border-[#E2E8F0] bg-[#F8FAFC] text-slate-400">
              {info.minLabel}
            </span>
            <div className="h-3 w-28 rounded border border-slate-200 bg-gradient-to-r from-[#EFF6FF] via-[#60A5FA] to-[#1E3A8A]"></div>
            <span className="font-semibold text-[#172033]">{info.maxLabel}</span>
          </div>
        </div>
      </div>

      {/* 4x4 Continuous Matrix Grid */}
      <div className="overflow-x-auto border border-[#E2E8F0] rounded-xl bg-white shadow-2xs">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="border-b border-[#E2E8F0] bg-slate-50 text-[11px] font-bold text-[#172033]">
              <th className="py-2.5 px-3 text-left w-36">Reference Market</th>
              {activeCountries.map((c) => (
                <th key={c} className="py-2.5 px-3 text-center min-w-[95px]">
                  {COUNTRY_CONFIG[c]?.flag} {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E2E8F0]">
            {activeCountries.map((c1) => (
              <tr key={c1} className="hover:bg-slate-50/40">
                <td className="py-3 px-3 font-bold text-[#172033] border-r border-[#E2E8F0] whitespace-nowrap">
                  {COUNTRY_CONFIG[c1]?.flag} {c1}
                </td>
                {activeCountries.map((c2) => {
                  const val = matrixData?.[c1]?.[c2] ?? (c1 === c2 ? 1.0 : 0.0);

                  const pair = pairwise?.find(
                    (p: any) =>
                      (p.country_a === c1 && p.country_b === c2) ||
                      (p.country_a === c2 && p.country_b === c1)
                  );

                  const { bg, text } = getContinuousSimColor(val);
                  const isSelected = hoveredCell?.c1 === c1 && hoveredCell?.c2 === c2;

                  return (
                    <td
                      key={c2}
                      className="p-0 border border-slate-200/80 text-center relative"
                      onMouseEnter={() =>
                        setHoveredCell({
                          c1,
                          c2,
                          val,
                          sampleA: pair?.sample_size_a,
                          sampleB: pair?.sample_size_b,
                          isSparse: pair?.sparse_sample_flag,
                        })
                      }
                      onMouseLeave={() => setHoveredCell(null)}
                    >
                      <div
                        className={`flex ${
                          compact ? 'h-11' : 'h-13'
                        } w-full items-center justify-center font-mono font-bold text-xs transition-all cursor-pointer ${
                          isSelected ? 'ring-2 ring-blue-600 ring-inset z-10' : ''
                        }`}
                        style={{ backgroundColor: bg, color: text }}
                      >
                        {val.toFixed(4)}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Hover Detail Card */}
      {hoveredCell && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 rounded-lg border border-blue-200 bg-blue-50/80 px-4 py-2.5 text-xs text-[#172033] shadow-xs">
          <div className="flex items-center gap-2">
            <span className="font-bold text-[#2563EB]">
              {COUNTRY_CONFIG[hoveredCell.c1]?.flag} {hoveredCell.c1} ↔ {COUNTRY_CONFIG[hoveredCell.c2]?.flag} {hoveredCell.c2}
            </span>
            <span className="text-[#64748B]">({info.shortTitle})</span>
          </div>
          <div className="flex flex-wrap items-center gap-4 font-mono text-[11px]">
            <span>
              Similarity Score: <strong className="text-[#2563EB]">{hoveredCell.val.toFixed(4)}</strong>
            </span>
            {hoveredCell.c1 === hoveredCell.c2 ? (
              <span className="rounded bg-white px-2 py-0.5 border border-blue-200 text-[10px] font-semibold text-blue-800">
                Diagonal: Perfect Self-Alignment (1.0000)
              </span>
            ) : (
              <>
                {hoveredCell.sampleA !== undefined && (
                  <span>
                    Sample Sizes: <strong>{hoveredCell.sampleA} vs {hoveredCell.sampleB} vacancies</strong>
                  </span>
                )}
                <span
                  className={`rounded px-2 py-0.5 border text-[10px] font-semibold ${
                    hoveredCell.isSparse
                      ? 'bg-amber-100 text-amber-800 border-amber-300'
                      : 'bg-emerald-100 text-emerald-800 border-emerald-300'
                  }`}
                >
                  {hoveredCell.isSparse ? 'High Uncertainty (N<10)' : 'Adequate Sample'}
                </span>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export const RegionalAnalysis: React.FC = () => {
  // Analytical Scope: Comparative Regional vs Single-Batch Role Segmentation
  const [analyticalScope, setAnalyticalScope] = useState<'comparative' | 'single_batch'>('comparative');

  // Summary State (KPIs, Market info, sample denominators)
  const [summary, setSummary] = useState<any>(null);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [refreshSuccess, setRefreshSuccess] = useState<string | null>(null);

  // Architecture Expander
  const [architectureOpen, setArchitectureOpen] = useState<boolean>(false);

  // Internal Navigation (Tabs 1 to 6)
  const [activeTab, setActiveTab] = useState<number>(1);

  // --- Tab 1: Skill Demand & Gaps ---
  const [visMode, setVisMode] = useState<'bar' | 'heatmap' | 'dual'>('bar');
  const [selectedCategory, setSelectedCategory] = useState<string>('All Categories');
  const [topK, setTopK] = useState<number>(15);
  const [skillDemandData, setSkillDemandData] = useState<any>(null);
  const [loadingDemand, setLoadingDemand] = useState<boolean>(false);
  const [comparator, setComparator] = useState<string>('India');
  const [gapsData, setGapsData] = useState<any>(null);
  const [loadingGaps, setLoadingGaps] = useState<boolean>(false);
  const [exactTableOpen, setExactTableOpen] = useState<boolean>(false);
  const [demandSearch, setDemandSearch] = useState<string>('');

  // --- Tab 2: Role Distribution ---
  const [rolesData, setRolesData] = useState<any>(null);
  const [loadingRoles, setLoadingRoles] = useState<boolean>(false);
  const [selectedRole, setSelectedRole] = useState<string>('');

  // --- Tab 3: Salary & Compensation ---
  const [salaryData, setSalaryData] = useState<any>(null);
  const [loadingSalary, setLoadingSalary] = useState<boolean>(false);
  const [exchangeOpen, setExchangeOpen] = useState<boolean>(false);

  // --- Tab 4: Profile Similarities ---
  const [simData, setSimData] = useState<any>(null);
  const [loadingSim, setLoadingSim] = useState<boolean>(false);
  const [selectedSimMetric, setSelectedSimMetric] = useState<
    'cosine_similarity' | 'jaccard_top10_similarity' | 'spearman_rank_correlation' | 'all'
  >('cosine_similarity');

  // --- Tab 5: Sensitivity Analysis ---
  const [sensData, setSensData] = useState<any>(null);
  const [loadingSens, setLoadingSens] = useState<boolean>(false);

  // --- Tab 6: Eligibility Funnel & Audit ---
  const [funnelData, setFunnelData] = useState<any>(null);
  const [loadingFunnel, setLoadingFunnel] = useState<boolean>(false);

  // --- Scope 2: Single-Batch Role Segmentation State ---
  const [singleBatchData, setSingleBatchData] = useState<any>(null);
  const [singleExecuting, setSingleExecuting] = useState<boolean>(false);
  const [singleSelectedRole, setSingleSelectedRole] = useState<string>('');
  const [singleSearch, setSingleSearch] = useState<string>('');

  // 1. Initial Load: Fetch Summary
  const fetchSummary = async () => {
    try {
      const res = await fetch('/api/regional/summary');
      if (res.ok) {
        const json = await res.json();
        setSummary(json);
      }
    } catch (e) {
      console.error('Failed to load regional summary:', e);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  // Refresh from Master DB
  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      setRefreshSuccess(null);
      const res = await fetch('/api/regional/refresh', { method: 'POST' });
      if (res.ok) {
        const json = await res.json();
        setSummary(json);
        setRefreshSuccess('Refreshed harmonized records from Master SQLite Database.');
        // Refresh currently active tab
        if (activeTab === 1) fetchSkillDemand();
        if (activeTab === 2) fetchRoles();
        if (activeTab === 3) fetchSalary();
        if (activeTab === 4) fetchSimilarities();
        if (activeTab === 5) fetchSensitivity();
        if (activeTab === 6) fetchFunnel();
        setTimeout(() => setRefreshSuccess(null), 4000);
      }
    } catch (e) {
      console.error('Refresh failed:', e);
    } finally {
      setRefreshing(false);
    }
  };

  // 2. Tab Data Loaders
  const fetchSkillDemand = async () => {
    try {
      setLoadingDemand(true);
      const params = new URLSearchParams({
        top_n: topK.toString(),
      });
      if (selectedCategory && selectedCategory !== 'All Categories') {
        params.append('category', selectedCategory);
      }
      const res = await fetch(`/api/regional/skill-demand?${params.toString()}`);
      if (res.ok) {
        const json = await res.json();
        setSkillDemandData(json);
      }
    } catch (e) {
      console.error('Failed to load skill demand:', e);
    } finally {
      setLoadingDemand(false);
    }
  };

  const fetchSkillGaps = async (comp: string) => {
    try {
      setLoadingGaps(true);
      const res = await fetch(`/api/regional/skill-gaps?comparator=${encodeURIComponent(comp)}`);
      if (res.ok) {
        const json = await res.json();
        setGapsData(json);
      }
    } catch (e) {
      console.error('Failed to load skill gaps:', e);
    } finally {
      setLoadingGaps(false);
    }
  };

  const fetchRoles = async (roleName?: string) => {
    try {
      setLoadingRoles(true);
      const url = roleName
        ? `/api/regional/roles?selected_role=${encodeURIComponent(roleName)}`
        : '/api/regional/roles';
      const res = await fetch(url);
      if (res.ok) {
        const json = await res.json();
        setRolesData(json);
        if (!selectedRole && json.selected_role) {
          setSelectedRole(json.selected_role);
        }
      }
    } catch (e) {
      console.error('Failed to load roles:', e);
    } finally {
      setLoadingRoles(false);
    }
  };

  const fetchSalary = async () => {
    try {
      setLoadingSalary(true);
      const res = await fetch('/api/regional/salary');
      if (res.ok) {
        const json = await res.json();
        setSalaryData(json);
      }
    } catch (e) {
      console.error('Failed to load salary:', e);
    } finally {
      setLoadingSalary(false);
    }
  };

  const fetchSimilarities = async () => {
    try {
      setLoadingSim(true);
      const res = await fetch('/api/regional/similarities');
      if (res.ok) {
        const json = await res.json();
        setSimData(json);
      }
    } catch (e) {
      console.error('Failed to load similarities:', e);
    } finally {
      setLoadingSim(false);
    }
  };

  const fetchSensitivity = async () => {
    try {
      setLoadingSens(true);
      const res = await fetch('/api/regional/sensitivity');
      if (res.ok) {
        const json = await res.json();
        setSensData(json);
      }
    } catch (e) {
      console.error('Failed to load sensitivity:', e);
    } finally {
      setLoadingSens(false);
    }
  };

  const fetchFunnel = async () => {
    try {
      setLoadingFunnel(true);
      const res = await fetch('/api/regional/eligibility-funnel');
      if (res.ok) {
        const json = await res.json();
        setFunnelData(json);
      }
    } catch (e) {
      console.error('Failed to load funnel:', e);
    } finally {
      setLoadingFunnel(false);
    }
  };

  // Scope 2: Single-Batch Role Segmentation Loader
  const fetchSingleBatchData = async () => {
    try {
      const res = await fetch('/api/regional/role-segmentation');
      if (res.ok) {
        const json = await res.json();
        setSingleBatchData(json);
        if (json.role_options && json.role_options.length > 0 && !singleSelectedRole) {
          setSingleSelectedRole(json.role_options[0]);
        }
      }
    } catch (e) {
      console.error('Failed to load single-batch role segmentation:', e);
    }
  };

  const handleExecuteSingleRoleAnalysis = async () => {
    try {
      setSingleExecuting(true);
      const res = await fetch('/api/regional/role-segmentation/execute', { method: 'POST' });
      if (res.ok) {
        const json = await res.json();
        setSingleBatchData(json);
        if (json.role_options && json.role_options.length > 0) {
          setSingleSelectedRole(json.role_options[0]);
        }
      }
    } catch (e) {
      console.error('Role classification failed:', e);
    } finally {
      setSingleExecuting(false);
    }
  };

  // Trigger loads on tab change
  useEffect(() => {
    if (analyticalScope === 'comparative') {
      if (activeTab === 1) {
        fetchSkillDemand();
        fetchSkillGaps(comparator);
      } else if (activeTab === 2) {
        fetchRoles(selectedRole);
      } else if (activeTab === 3) {
        fetchSalary();
      } else if (activeTab === 4) {
        fetchSimilarities();
      } else if (activeTab === 5) {
        fetchSensitivity();
      } else if (activeTab === 6) {
        fetchFunnel();
      }
    } else {
      fetchSingleBatchData();
    }
  }, [activeTab, analyticalScope]);

  // Handle Tab 1 filter updates
  useEffect(() => {
    if (activeTab === 1 && analyticalScope === 'comparative') {
      fetchSkillDemand();
    }
  }, [selectedCategory, topK]);

  useEffect(() => {
    if (activeTab === 1 && analyticalScope === 'comparative') {
      fetchSkillGaps(comparator);
    }
  }, [comparator]);

  // Handle Tab 2 role selection
  const handleSelectRole = (r: string) => {
    setSelectedRole(r);
    fetchRoles(r);
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-16">
      {/* Page Title & Subtitle */}
      <div className="flex flex-col gap-1 border-b border-[#E2E8F0] pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-[#172033]">Regional Analysis</h2>
          <p className="text-xs text-[#64748B]">
            Empirical multi-country comparative labor market intelligence and role-segmented skill demand.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-[#2563EB]">
            <Compass className="h-3.5 w-3.5" />
            Individual Research Subsystem
          </span>
        </div>
      </div>

      {/* Security Notice */}
      <SecurityNotice />

      {/* 1. Analytical Scope Selection (Segmented Control) */}
      <div className="rounded-xl border border-[#E2E8F0] bg-white p-2 shadow-xs">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => setAnalyticalScope('comparative')}
            className={`flex items-start gap-3 rounded-lg p-3 text-left transition-all ${
              analyticalScope === 'comparative'
                ? 'bg-blue-50/80 border border-blue-200 text-[#172033] shadow-2xs'
                : 'hover:bg-slate-50 border border-transparent text-[#64748B]'
            }`}
          >
            <div
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                analyticalScope === 'comparative'
                  ? 'bg-[#2563EB] text-white shadow-xs'
                  : 'bg-slate-100 text-[#64748B]'
              }`}
            >
              <Compass className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2 font-semibold text-xs text-[#172033]">
                Comparative Regional Market Analysis
                {analyticalScope === 'comparative' && (
                  <span className="rounded bg-[#2563EB] px-1.5 py-0.2 text-[10px] font-bold text-white">
                    Active Scope
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-[11px] text-[#64748B] leading-tight">
                Sri Lanka (Focal Market) vs. India, Singapore, Malaysia across skill gaps, compensation, and profile similarities.
              </p>
            </div>
          </button>

          <button
            type="button"
            onClick={() => setAnalyticalScope('single_batch')}
            className={`flex items-start gap-3 rounded-lg p-3 text-left transition-all ${
              analyticalScope === 'single_batch'
                ? 'bg-blue-50/80 border border-blue-200 text-[#172033] shadow-2xs'
                : 'hover:bg-slate-50 border border-transparent text-[#64748B]'
            }`}
          >
            <div
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                analyticalScope === 'single_batch'
                  ? 'bg-[#2563EB] text-white shadow-xs'
                  : 'bg-slate-100 text-[#64748B]'
              }`}
            >
              <Briefcase className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2 font-semibold text-xs text-[#172033]">
                Single-Batch Role Segmentation
                {analyticalScope === 'single_batch' && (
                  <span className="rounded bg-[#2563EB] px-1.5 py-0.2 text-[10px] font-bold text-white">
                    Active Scope
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-[11px] text-[#64748B] leading-tight">
                Taxonomic classification into IT roles, separating core technical skills from periphery terms (lexical vs semantic).
              </p>
            </div>
          </button>
        </div>
      </div>

      {/* =========================================================================
          SCOPE 1: Comparative Regional IT Labour-Market Analysis
         ========================================================================= */}
      {analyticalScope === 'comparative' && (
        <div className="space-y-6">
          {/* Main Scope Control Card */}
          <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h3 className="text-base font-bold text-[#172033]">
                  Comparative Regional IT Labour-Market Analysis
                </h3>
                <p className="text-xs text-[#64748B] max-w-3xl mt-0.5">
                  Empirical quantitative comparison of technical skill demand, role distributions, and compensation disclosure across{' '}
                  <strong className="text-[#172033]">Sri Lanka (Focal Market)</strong>,{' '}
                  <strong className="text-[#172033]">India</strong>,{' '}
                  <strong className="text-[#172033]">Singapore</strong>, and{' '}
                  <strong className="text-[#172033]">Malaysia</strong>.
                </p>

                {/* Country Chips */}
                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                  <span className="font-medium text-[#64748B]">Markets Under Study:</span>
                  {Object.entries(COUNTRY_CONFIG).map(([name, conf]) => (
                    <span
                      key={name}
                      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${conf.bg} ${conf.text} ${conf.border}`}
                    >
                      <span>{conf.flag}</span>
                      <span>{conf.label}</span>
                    </span>
                  ))}
                </div>
              </div>

              {/* Refresh Actions & Database Status */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 shrink-0 pt-2 lg:pt-0 border-t lg:border-t-0 border-slate-100">
                <div className="text-xs text-[#64748B]">
                  <div>
                    Source: <strong className="text-[#2563EB]">🗄️ Master Database</strong>
                  </div>
                  <div>
                    Harmonized Records:{' '}
                    <strong className="font-mono text-[#172033]">
                      {summary ? summary.total_harmonized_records?.toLocaleString() : '...'}
                    </strong>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-3 py-2 text-xs font-semibold text-[#172033] shadow-2xs hover:bg-slate-50 disabled:opacity-50 transition-all"
                >
                  <RefreshCw className={`h-3.5 w-3.5 text-[#2563EB] ${refreshing ? 'animate-spin' : ''}`} />
                  {refreshing ? 'Refreshing...' : '🔄 Refresh from Master DB'}
                </button>
              </div>
            </div>

            {refreshSuccess && (
              <div className="mt-3 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
                <CheckCircle2 className="h-4 w-4 text-[#16A34A] shrink-0" />
                {refreshSuccess}
              </div>
            )}
          </div>

          {/* Regional Analysis Pipeline & System Architecture Expander */}
          <div className="rounded-xl border border-[#E2E8F0] bg-white shadow-xs overflow-hidden">
            <button
              type="button"
              onClick={() => setArchitectureOpen(!architectureOpen)}
              className="flex w-full items-center justify-between p-4 text-left hover:bg-slate-50 transition-colors"
            >
              <div className="flex items-center gap-2.5">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-50 text-[#2563EB]">
                  <Layers className="h-4 w-4" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-[#172033]">
                    📐 Regional Analysis Pipeline & System Architecture
                  </h4>
                  <p className="text-[11px] text-[#64748B]">
                    Multi-stage quantitative pipeline for cross-national robustness, strict normalization, and transparent auditing.
                  </p>
                </div>
              </div>
              {architectureOpen ? (
                <ChevronUp className="h-4 w-4 text-[#64748B]" />
              ) : (
                <ChevronDown className="h-4 w-4 text-[#64748B]" />
              )}
            </button>

            {architectureOpen && (
              <div className="border-t border-[#E2E8F0] bg-slate-50/50 p-5 space-y-4 text-xs text-[#172033]">
                {/* 6-Stage Visual Workflow */}
                <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-2.5">
                  <div className="rounded-lg border border-[#E2E8F0] bg-white p-3 shadow-2xs space-y-1">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-[#2563EB]">Stage 1</div>
                    <div className="font-bold text-xs text-[#172033]">Multi-Country Ingestion</div>
                    <p className="text-[11px] text-[#64748B] leading-tight">
                      LK (itpro.lk, topjobs), IN (shine, timesjobs), SG (jobstreet.sg), MY (hiredly)
                    </p>
                  </div>
                  <div className="rounded-lg border border-[#E2E8F0] bg-white p-3 shadow-2xs space-y-1">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-[#2563EB]">Stage 2</div>
                    <div className="font-bold text-xs text-[#172033]">Harmonization & Scrub</div>
                    <p className="text-[11px] text-[#64748B] leading-tight">
                      HTML sanitization, SSRF protection, strict IT vs non-IT role classifier
                    </p>
                  </div>
                  <div className="rounded-lg border border-[#E2E8F0] bg-white p-3 shadow-2xs space-y-1">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-[#2563EB]">Stage 3</div>
                    <div className="font-bold text-xs text-[#172033]">Canonical Mapping</div>
                    <p className="text-[11px] text-[#64748B] leading-tight">
                      100+ ESCO/custom skills, ISO-3166-1 country normalization, regex salaries
                    </p>
                  </div>
                  <div className="rounded-lg border border-[#E2E8F0] bg-white p-3 shadow-2xs space-y-1">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-[#2563EB]">Stage 4</div>
                    <div className="font-bold text-xs text-[#172033]">Eligibility Filtering</div>
                    <p className="text-[11px] text-[#64748B] leading-tight">
                      Independent task filtering: general, skill ($N\ge 1$), and salary (disclosed)
                    </p>
                  </div>
                  <div className="rounded-lg border border-[#E2E8F0] bg-white p-3 shadow-2xs space-y-1">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-[#2563EB]">Stage 5</div>
                    <div className="font-bold text-xs text-[#172033]">Statistical Engine</div>
                    <p className="text-[11px] text-[#64748B] leading-tight">
                      Wilson 95% CIs, two-proportion $z$-tests, artifact detector, 4×4 similarities
                    </p>
                  </div>
                  <div className="rounded-lg border border-[#E2E8F0] bg-white p-3 shadow-2xs space-y-1">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-[#2563EB]">Stage 6</div>
                    <div className="font-bold text-xs text-[#172033]">Audited Deliverables</div>
                    <p className="text-[11px] text-[#64748B] leading-tight">
                      Interactive bar charts, 2D heatmaps, sensitivity scenarios, reproducible CSVs
                    </p>
                  </div>
                </div>

                <div className="rounded-lg border border-blue-200 bg-blue-50/60 p-3 text-[11px] text-blue-950 leading-relaxed">
                  <strong>Academic Research Principle (Proposal 3.5, 3.6, 3.8):</strong> Independent task-specific inclusion criteria prevent salary disclosure scarcity (only ~3.5% in Sri Lanka) from distorting skill demand samples. Nominal local currencies (LKR, INR, SGD, MYR) are strictly preserved with indicative exchange rates; PPP conversions are prohibited.
                </div>
              </div>
            )}
          </div>

          {/* 4 Regional Analytical KPI Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                Focal Market (Sri Lanka)
              </div>
              <div className="mt-1 text-2xl font-bold text-[#2563EB]">
                {summary ? summary.kpis?.focal_market_ads?.toLocaleString() : '—'}
              </div>
              <div className="mt-0.5 text-[11px] text-emerald-600 font-medium">Baseline national IT ads</div>
            </div>

            <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                Regional Comparators
              </div>
              <div className="mt-1 text-2xl font-bold text-[#D97706]">
                {summary ? summary.kpis?.regional_comparators_ads?.toLocaleString() : '—'}
              </div>
              <div className="mt-0.5 text-[11px] text-amber-600 font-medium">IN, SG, MY harmonized ads</div>
            </div>

            <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                Skill-Eligible Vacancies
              </div>
              <div className="mt-1 text-2xl font-bold text-[#16A34A]">
                {summary ? summary.kpis?.skill_eligible_vacancies?.toLocaleString() : '—'}
              </div>
              <div className="mt-0.5 text-[11px] text-slate-500 font-medium">$\ge 1$ verified technical skill</div>
            </div>

            <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                Salary Disclosure Rate
              </div>
              <div className="mt-1 text-2xl font-bold text-[#9333EA]">
                {summary ? `${summary.kpis?.salary_disclosure_rate_pct}%` : '—'}
              </div>
              <div className="mt-0.5 text-[11px] text-purple-600 font-medium">
                {summary ? `${summary.kpis?.salary_disclosed_count} disclosed` : '—'}
              </div>
            </div>
          </div>

          {/* Internal Navigation Tabs (6 Sections) */}
          <div className="border-b border-[#E2E8F0]">
            <div className="flex overflow-x-auto gap-2">
              {[
                { id: 1, label: '1. Skill Demand & Gaps', icon: BarChart3 },
                { id: 2, label: '2. Role Distribution', icon: Briefcase },
                { id: 3, label: '3. Salary & Compensation', icon: DollarSign },
                { id: 4, label: '4. Profile Similarities', icon: Compass },
                { id: 5, label: '5. Sensitivity Analysis', icon: Sliders },
                { id: 6, label: '6. Eligibility Funnel & Audit', icon: ShieldAlert },
              ].map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold whitespace-nowrap transition-all ${
                      isActive
                        ? 'border-[#2563EB] text-[#2563EB] bg-blue-50/50'
                        : 'border-transparent text-[#64748B] hover:border-slate-300 hover:text-[#172033]'
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {tab.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* =====================================================================
              TAB 1: Skill Demand & Gaps
             ===================================================================== */}
          {activeTab === 1 && (
            <div className="space-y-6">
              {/* Metadata Banner */}
              <div className="rounded-xl border border-blue-200 bg-blue-50/60 p-4 text-xs text-[#172033]">
                <div className="flex items-center gap-2 font-bold text-[#2563EB] mb-1">
                  <Info className="h-4 w-4" />
                  Canonical Skill Demand (% of National Vacancies)
                </div>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-[#64748B]">
                  <span>
                    <strong>Observation Window:</strong> August 2026 – October 2026
                  </span>
                  <span>•</span>
                  <span>
                    <strong>Sample Denominators (N):</strong> 🇱🇰 Sri Lanka (N=
                    {summary?.sample_denominators?.['Sri Lanka'] ?? 48}), 🇮🇳 India (N=
                    {summary?.sample_denominators?.['India'] ?? 20}), 🇸🇬 Singapore (N=
                    {summary?.sample_denominators?.['Singapore'] ?? 24}), 🇲🇾 Malaysia (N=
                    {summary?.sample_denominators?.['Malaysia'] ?? 16})
                  </span>
                  <span>•</span>
                  <span>
                    <strong>Formula:</strong> <code>Demand % = (Eligible Ads / Country N) × 100</code> with Wilson 95% CIs.
                  </span>
                </div>
              </div>

              {/* Controls Bar */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs">
                {/* Vis Mode */}
                <div>
                  <label className="block text-[11px] font-semibold text-[#64748B] uppercase mb-1.5">
                    Visualization Mode
                  </label>
                  <div className="flex rounded-lg border border-[#E2E8F0] p-0.5 bg-slate-50">
                    <button
                      type="button"
                      onClick={() => setVisMode('bar')}
                      className={`flex-1 rounded-md py-1.5 text-xs font-semibold transition-all ${
                        visMode === 'bar' ? 'bg-white text-[#2563EB] shadow-2xs' : 'text-[#64748B]'
                      }`}
                    >
                      📊 Grouped Bar
                    </button>
                    <button
                      type="button"
                      onClick={() => setVisMode('heatmap')}
                      className={`flex-1 rounded-md py-1.5 text-xs font-semibold transition-all ${
                        visMode === 'heatmap' ? 'bg-white text-[#2563EB] shadow-2xs' : 'text-[#64748B]'
                      }`}
                    >
                      🔥 Heatmap
                    </button>
                    <button
                      type="button"
                      onClick={() => setVisMode('dual')}
                      className={`flex-1 rounded-md py-1.5 text-xs font-semibold transition-all ${
                        visMode === 'dual' ? 'bg-white text-[#2563EB] shadow-2xs' : 'text-[#64748B]'
                      }`}
                    >
                      📋 Dual View
                    </button>
                  </div>
                </div>

                {/* Filter Category */}
                <div>
                  <label className="block text-[11px] font-semibold text-[#64748B] uppercase mb-1.5">
                    Filter Category
                  </label>
                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="w-full rounded-lg border border-[#E2E8F0] bg-white px-3 py-1.5 text-xs text-[#172033] focus:border-[#2563EB] focus:outline-none"
                  >
                    {skillDemandData?.categories?.map((c: string) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Top Skills Slider */}
                <div>
                  <div className="flex items-center justify-between text-[11px] font-semibold text-[#64748B] uppercase mb-1.5">
                    <span>Top Skills to Display</span>
                    <span className="font-mono text-[#2563EB]">{topK}</span>
                  </div>
                  <input
                    type="range"
                    min={5}
                    max={35}
                    step={5}
                    value={topK}
                    onChange={(e) => setTopK(Number(e.target.value))}
                    className="w-full accent-[#2563EB]"
                  />
                  <div className="flex justify-between text-[10px] text-slate-400">
                    <span>5</span>
                    <span>15</span>
                    <span>25</span>
                    <span>35</span>
                  </div>
                </div>
              </div>

              {/* Chart & Visualizations Area */}
              {loadingDemand ? (
                <div className="flex h-64 items-center justify-center rounded-xl border border-[#E2E8F0] bg-white">
                  <RefreshCw className="h-6 w-6 animate-spin text-[#2563EB]" />
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Mode 1: Typical Grouped Bar Chart */}
                  {(visMode === 'bar' || visMode === 'dual') && (
                    <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-4">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E2E8F0] pb-3">
                        <div>
                          <h4 className="text-sm font-bold text-[#172033]">
                            Top Skill Demand Rate by Country (% of National IT Vacancies)
                          </h4>
                          <p className="text-[11px] text-[#64748B]">
                            Standard vertical clustered bar chart comparing canonical skill demand percentages across target markets.
                          </p>
                        </div>
                        <div className="flex items-center gap-3 text-xs">
                          {Object.entries(COUNTRY_CONFIG).map(([c, conf]) => (
                            <div key={c} className="flex items-center gap-1.5">
                              <span
                                className="h-2.5 w-2.5 rounded-full"
                                style={{ backgroundColor: conf.hex }}
                              ></span>
                              <span className="text-[11px] text-[#172033] font-medium">{conf.flag} {c}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <TypicalGroupedBarChart
                        skills={skillDemandData?.top_skills || []}
                        chartData={skillDemandData?.chart_data || []}
                      />
                    </div>
                  )}

                  {/* Mode 2: Typical Skill Demand Heatmap */}
                  {(visMode === 'heatmap' || visMode === 'dual') && (
                    <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-4">
                      <div className="border-b border-[#E2E8F0] pb-3">
                        <h4 className="text-sm font-bold text-[#172033]">
                          Canonical Skill Demand Intensity Heatmap
                        </h4>
                        <p className="text-[11px] text-[#64748B]">
                          Standard 2D continuous matrix heatmap showing cross-market demand intensity (% of national vacancies).
                        </p>
                      </div>

                      <TypicalSkillDemandHeatmap
                        skills={skillDemandData?.top_skills || []}
                        chartData={skillDemandData?.chart_data || []}
                      />
                    </div>
                  )}
                </div>
              )}

              {/* Skill Gap Divergence (Sri Lanka vs. Selected Comparator) */}
              <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E2E8F0] pb-3">
                  <div>
                    <h4 className="text-sm font-bold text-[#172033]">
                      Skill Gap Divergence (Sri Lanka vs. Comparators)
                    </h4>
                    <p className="text-[11px] text-[#64748B]">
                      Two-proportion $z$-test with 95% confidence intervals and automated zero-count crawler artifact flags.
                    </p>
                  </div>

                  {/* Comparator Selector */}
                  <div className="flex items-center gap-1.5 rounded-lg border border-[#E2E8F0] p-1 bg-slate-50 text-xs">
                    <span className="px-2 text-[11px] font-medium text-[#64748B]">Compare Sri Lanka to:</span>
                    {['India', 'Singapore', 'Malaysia'].map((c) => (
                      <button
                        key={c}
                        onClick={() => setComparator(c)}
                        className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-all ${
                          comparator === c ? 'bg-white text-[#2563EB] shadow-2xs' : 'text-[#64748B] hover:text-[#172033]'
                        }`}
                      >
                        {COUNTRY_CONFIG[c]?.flag} {c}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Gaps Table */}
                {loadingGaps ? (
                  <div className="flex h-40 items-center justify-center">
                    <RefreshCw className="h-5 w-5 animate-spin text-[#2563EB]" />
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-[#E2E8F0] bg-slate-50 text-[11px] font-semibold text-[#64748B]">
                          <th className="py-2.5 px-3">Canonical Skill</th>
                          <th className="py-2.5 px-3">Category</th>
                          <th className="py-2.5 px-3 text-right">Sri Lanka %</th>
                          <th className="py-2.5 px-3 text-right">{comparator} %</th>
                          <th className="py-2.5 px-3 text-right">Gap (pp)</th>
                          <th className="py-2.5 px-3 text-center">95% CI (pp)</th>
                          <th className="py-2.5 px-3 text-right">p-value</th>
                          <th className="py-2.5 px-3 text-center">Evidence Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#E2E8F0]">
                        {gapsData?.records?.slice(0, 25).map((r: any, idx: number) => {
                          const gap = Number(r.gap_pp);
                          const isPos = gap > 0;
                          return (
                            <tr key={idx} className="hover:bg-slate-50 transition-colors">
                              <td className="py-2.5 px-3 font-semibold text-[#172033]">{r.skill_name}</td>
                              <td className="py-2.5 px-3 text-[#64748B] text-[11px]">{r.category}</td>
                              <td className="py-2.5 px-3 text-right font-mono font-medium text-[#172033]">
                                {r.focal_demand_pct}%
                              </td>
                              <td className="py-2.5 px-3 text-right font-mono font-medium text-[#172033]">
                                {r.comparator_demand_pct}%
                              </td>
                              <td className="py-2.5 px-3 text-right font-mono font-bold">
                                <span className={isPos ? 'text-blue-600' : 'text-amber-600'}>
                                  {isPos ? '+' : ''}
                                  {r.gap_pp} pp
                                </span>
                              </td>
                              <td className="py-2.5 px-3 text-center font-mono text-[11px] text-[#64748B]">
                                [{r.gap_ci_lower_95}, {r.gap_ci_upper_95}]
                              </td>
                              <td className="py-2.5 px-3 text-right font-mono text-[11px] text-[#64748B]">
                                {Number(r.p_value).toFixed(4)}
                              </td>
                              <td className="py-2.5 px-3 text-center">
                                <span
                                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${
                                    r.status_color === 'red'
                                      ? 'bg-rose-50 text-rose-700 border border-rose-200'
                                      : r.status_color === 'green'
                                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                      : r.status_color === 'amber'
                                      ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                      : 'bg-slate-100 text-slate-700 border border-slate-200'
                                  }`}
                                >
                                  {r.status_label}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Expandable Exact-Value Data Table & Export */}
              <div className="rounded-xl border border-[#E2E8F0] bg-white shadow-xs overflow-hidden">
                <button
                  type="button"
                  onClick={() => setExactTableOpen(!exactTableOpen)}
                  className="flex w-full items-center justify-between p-4 text-left hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <FileSpreadsheet className="h-4 w-4 text-[#2563EB]" />
                    <span className="text-xs font-bold text-[#172033]">
                      📊 Complete Exact-Value Skill Demand Data Table & Export
                    </span>
                  </div>
                  {exactTableOpen ? (
                    <ChevronUp className="h-4 w-4 text-[#64748B]" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-[#64748B]" />
                  )}
                </button>

                {exactTableOpen && (
                  <div className="border-t border-[#E2E8F0] p-4 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <input
                        type="text"
                        placeholder="Search skill name..."
                        value={demandSearch}
                        onChange={(e) => setDemandSearch(e.target.value)}
                        className="rounded-lg border border-[#E2E8F0] px-3 py-1.5 text-xs text-[#172033] w-full sm:w-64 focus:outline-none focus:border-[#2563EB]"
                      />
                      <a
                        href="/api/regional/download/skill_demand"
                        download
                        className="inline-flex items-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-3 py-1.5 text-xs font-semibold text-[#172033] shadow-2xs hover:bg-slate-50"
                      >
                        <Download className="h-3.5 w-3.5 text-[#2563EB]" />
                        📥 Export All Skill Demand Records (CSV)
                      </a>
                    </div>

                    <div className="max-h-72 overflow-y-auto border border-[#E2E8F0] rounded-lg">
                      <table className="w-full text-left text-xs">
                        <thead className="sticky top-0 bg-slate-50 border-b border-[#E2E8F0]">
                          <tr className="text-[11px] font-semibold text-[#64748B]">
                            <th className="py-2 px-3">Country</th>
                            <th className="py-2 px-3">Canonical Skill</th>
                            <th className="py-2 px-3">Category</th>
                            <th className="py-2 px-3 text-right">Mentions (k)</th>
                            <th className="py-2 px-3 text-right">Sample (N)</th>
                            <th className="py-2 px-3 text-right">Demand %</th>
                            <th className="py-2 px-3 text-center">95% CI Range</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#E2E8F0]">
                          {skillDemandData?.records
                            ?.filter((r: any) =>
                              !demandSearch ||
                              r.skill_name.toLowerCase().includes(demandSearch.toLowerCase()) ||
                              r.country.toLowerCase().includes(demandSearch.toLowerCase())
                            )
                            ?.slice(0, 100)
                            .map((r: any, idx: number) => (
                              <tr key={idx} className="hover:bg-slate-50">
                                <td className="py-1.5 px-3 font-medium text-[#172033]">{r.country}</td>
                                <td className="py-1.5 px-3 font-semibold text-[#2563EB]">{r.skill_name}</td>
                                <td className="py-1.5 px-3 text-[#64748B] text-[11px]">{r.category}</td>
                                <td className="py-1.5 px-3 text-right font-mono">{r.mention_count}</td>
                                <td className="py-1.5 px-3 text-right font-mono">{r.eligible_ads_denominator}</td>
                                <td className="py-1.5 px-3 text-right font-mono font-bold text-[#172033]">
                                  {r.demand_pct}%
                                </td>
                                <td className="py-1.5 px-3 text-center font-mono text-[11px] text-[#64748B]">
                                  [{r.ci_lower_95}, {r.ci_upper_95}]
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* =====================================================================
              TAB 2: Role Distribution
             ===================================================================== */}
          {activeTab === 2 && (
            <div className="space-y-6">
              <div className="rounded-xl border border-blue-200 bg-blue-50/60 p-4 text-xs text-[#172033]">
                <div className="font-bold text-[#2563EB] mb-1">
                  IT Occupational Role Distributions Across Markets
                </div>
                <p className="text-[11px] text-[#64748B]">
                  Job postings are classified into canonical IT roles using multi-keyword title and description matching. Ambiguous postings are explicitly audited as <code>Unclassified</code> rather than silently forced.
                </p>
              </div>

              {loadingRoles ? (
                <div className="flex h-48 items-center justify-center rounded-xl border border-[#E2E8F0] bg-white">
                  <RefreshCw className="h-6 w-6 animate-spin text-[#2563EB]" />
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                  {/* Left Column: Role Frequency by Country */}
                  <div className="lg:col-span-3 rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-3">
                    <h4 className="text-xs font-bold text-[#172033] uppercase tracking-wider">
                      Role Frequency by Country
                    </h4>
                    <div className="overflow-x-auto max-h-96 border border-[#E2E8F0] rounded-lg">
                      <table className="w-full text-left text-xs">
                        <thead className="sticky top-0 bg-slate-50 border-b border-[#E2E8F0]">
                          <tr className="text-[11px] font-semibold text-[#64748B]">
                            <th className="py-2.5 px-3">Role Name</th>
                            {Object.keys(COUNTRY_CONFIG).map((c) => (
                              <th key={c} className="py-2.5 px-3 text-right">
                                {COUNTRY_CONFIG[c].flag} {c}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#E2E8F0]">
                          {rolesData?.role_pivot?.map((r: any, idx: number) => (
                            <tr key={idx} className="hover:bg-slate-50">
                              <td className="py-2 px-3 font-semibold text-[#172033]">{r.role_name}</td>
                              {Object.keys(COUNTRY_CONFIG).map((c) => (
                                <td key={c} className="py-2 px-3 text-right font-mono text-[#64748B]">
                                  {r[c] || 0}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Right Column: Classification Quality Audit */}
                  <div className="lg:col-span-2 rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-3">
                    <h4 className="text-xs font-bold text-[#172033] uppercase tracking-wider">
                      Classification Quality Audit
                    </h4>
                    <div className="overflow-x-auto border border-[#E2E8F0] rounded-lg">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 border-b border-[#E2E8F0]">
                          <tr className="text-[11px] font-semibold text-[#64748B]">
                            <th className="py-2 px-3">Country</th>
                            <th className="py-2 px-3 text-right">Total Ads</th>
                            <th className="py-2 px-3 text-right">Unclassified %</th>
                            <th className="py-2 px-3 text-center">Audit Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#E2E8F0]">
                          {rolesData?.audit_records?.map((r: any, idx: number) => (
                            <tr key={idx} className="hover:bg-slate-50">
                              <td className="py-2.5 px-3 font-medium text-[#172033]">{r.country}</td>
                              <td className="py-2.5 px-3 text-right font-mono text-[#64748B]">
                                {r.total_it_jobs}
                              </td>
                              <td className="py-2.5 px-3 text-right font-mono font-bold text-amber-600">
                                {r.unclassified_pct}%
                              </td>
                              <td className="py-2.5 px-3 text-center">
                                <span
                                  className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold ${
                                    r.unclassified_pct < 15
                                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                      : 'bg-amber-50 text-amber-700 border border-amber-200'
                                  }`}
                                >
                                  {r.classification_quality}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* Role-Segmented Skill Demand Section */}
              <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E2E8F0] pb-3">
                  <div>
                    <h4 className="text-sm font-bold text-[#172033]">Role-Segmented Technical Skill Demand</h4>
                    <p className="text-[11px] text-[#64748B]">
                      Examine canonical skill frequencies within a specific occupational role across countries.
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-[#64748B] font-medium">Role:</span>
                    <select
                      value={selectedRole}
                      onChange={(e) => handleSelectRole(e.target.value)}
                      className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-1.5 text-xs text-[#172033] focus:outline-none focus:border-[#2563EB]"
                    >
                      {rolesData?.available_roles?.map((r: string) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {rolesData?.role_demand_chart?.length === 0 ? (
                  <div className="p-8 text-center text-xs text-[#64748B]">
                    No skills extracted for role "{selectedRole}".
                  </div>
                ) : (
                  <div className="space-y-3 pt-2">
                    {rolesData?.role_demand_chart?.map((item: any) => (
                      <div key={item.skill_name} className="space-y-1">
                        <div className="text-xs font-semibold text-[#172033]">{item.skill_name}</div>
                        <div className="grid grid-cols-4 gap-2">
                          {Object.keys(COUNTRY_CONFIG).map((cName) => {
                            const pct = Number(item[cName] || 0);
                            const conf = COUNTRY_CONFIG[cName];
                            return (
                              <div key={cName} className="space-y-1">
                                <div className="flex items-center justify-between text-[10px]">
                                  <span className="text-slate-500">{conf.flag} {cName}</span>
                                  <span className="font-mono font-bold" style={{ color: conf.hex }}>
                                    {pct.toFixed(1)}%
                                  </span>
                                </div>
                                <div className="h-2.5 w-full rounded-full bg-slate-100 overflow-hidden">
                                  <div
                                    className="h-full rounded-full"
                                    style={{ width: `${Math.min(100, pct)}%`, backgroundColor: conf.hex }}
                                  ></div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* =====================================================================
              TAB 3: Salary & Compensation
             ===================================================================== */}
          {activeTab === 3 && (
            <div className="space-y-6">
              {/* Critical Methodological Notice */}
              <div className="rounded-xl border border-rose-200 bg-rose-50/70 p-4 text-xs text-rose-950">
                <div className="flex items-center gap-2 font-bold text-rose-700 mb-1">
                  <AlertTriangle className="h-4 w-4" />
                  CRITICAL METHODOLOGICAL NOTICE
                </div>
                <p className="text-[11px] text-rose-900 leading-relaxed">
                  Nominal salaries reflect contractual cash offers in local currencies (LKR, INR, SGD, MYR) normalized to monthly equivalents. Nominal values <strong>DO NOT</strong> establish purchasing power parity (PPP), local taxation differences, or living standards. Undisclosed salaries are strictly excluded from denominators rather than converted to zero.
                </p>
              </div>

              {/* Sri Lanka Small Sample Advisory */}
              <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-4 text-xs text-amber-950">
                <div className="flex items-center gap-2 font-bold text-amber-800 mb-1">
                  <ShieldAlert className="h-4 w-4" />
                  🇱🇰 SRI LANKA SALARY DISCLOSURE ADVISORY
                </div>
                <p className="text-[11px] text-amber-900 leading-relaxed">
                  Only <strong>2 out of 57 advertisements (3.51%)</strong> in Sri Lanka disclose numerical compensation (Contractual offers: LKR 50,000 and LKR 75,000 monthly). Small sample warning is active (N &lt; 10). Cross-country compensation comparisons involving Sri Lanka carry extreme statistical uncertainty and must be treated with caution.
                </p>
              </div>

              {/* Disclosed Salary Interval & Range Visualization */}
              <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-4">
                <div className="border-b border-[#E2E8F0] pb-3">
                  <h4 className="text-sm font-bold text-[#172033]">
                    National Disclosed Salary Range Plots (Isolated Local Currencies)
                  </h4>
                  <p className="text-[11px] text-[#64748B]">
                    Horizontal bars: Min to Max Range • Highlighted range: Interquartile Range (IQR, 25th–75th percentile) • Marker: Median Monthly Equivalent.
                  </p>
                </div>

                {loadingSalary ? (
                  <div className="flex h-40 items-center justify-center">
                    <RefreshCw className="h-6 w-6 animate-spin text-[#2563EB]" />
                  </div>
                ) : (
                  <div className="space-y-4 pt-1">
                    {salaryData?.country_salary?.map((item: any) => {
                      const min = Number(item.min_salary || 0);
                      const max = Number(item.max_salary || 0);
                      const median = Number(item.median_salary || 0);
                      const iqr = Number(item.iqr_salary || 0);
                      const conf = COUNTRY_CONFIG[item.country] || { flag: '🌐', hex: '#2563EB' };

                      return (
                        <div key={item.country} className="rounded-lg border border-slate-100 bg-slate-50/50 p-3 space-y-2">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-bold text-[#172033]">
                              {conf.flag} {item.country} ({item.currency})
                            </span>
                            <div className="flex items-center gap-2">
                              {item.small_sample_flag && (
                                <span className="rounded bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-800">
                                  Small Sample (N&lt;10)
                                </span>
                              )}
                              <span className="font-mono text-xs font-semibold text-[#2563EB]">
                                Median: {item.currency} {median.toLocaleString()}
                              </span>
                            </div>
                          </div>

                          {/* Graphical interval representation */}
                          <div className="relative h-6 w-full rounded bg-slate-200 overflow-hidden flex items-center px-2">
                            <div className="w-full flex items-center justify-between text-[10px] font-mono text-[#172033] z-10">
                              <span>Min: {item.currency} {min.toLocaleString()}</span>
                              <span className="bg-white/90 px-1.5 py-0.5 rounded shadow-2xs font-bold">
                                IQR: {item.currency} {iqr.toLocaleString()}
                              </span>
                              <span>Max: {item.currency} {max.toLocaleString()}</span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* National Salary Coverage Table */}
              <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-3">
                <h4 className="text-xs font-bold text-[#172033] uppercase tracking-wider">
                  National Salary Coverage & Distribution Summary
                </h4>
                <div className="overflow-x-auto border border-[#E2E8F0] rounded-lg">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-b border-[#E2E8F0]">
                      <tr className="text-[11px] font-semibold text-[#64748B]">
                        <th className="py-2.5 px-3">Country</th>
                        <th className="py-2.5 px-3">Currency</th>
                        <th className="py-2.5 px-3 text-right">Disclosed / Total</th>
                        <th className="py-2.5 px-3 text-right">Coverage %</th>
                        <th className="py-2.5 px-3 text-right">Median (Monthly)</th>
                        <th className="py-2.5 px-3 text-right">IQR (Monthly)</th>
                        <th className="py-2.5 px-3 text-center">Min - Max</th>
                        <th className="py-2.5 px-3 text-center">Sample Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E2E8F0]">
                      {salaryData?.country_salary?.map((r: any, idx: number) => (
                        <tr key={idx} className="hover:bg-slate-50">
                          <td className="py-2 px-3 font-semibold text-[#172033]">{r.country}</td>
                          <td className="py-2 px-3 font-mono text-[#64748B]">{r.currency}</td>
                          <td className="py-2 px-3 text-right font-mono">
                            {r.disclosed_salary_count} / {r.total_eligible_ads}
                          </td>
                          <td className="py-2 px-3 text-right font-mono font-bold text-[#2563EB]">
                            {r.disclosure_rate_pct}%
                          </td>
                          <td className="py-2 px-3 text-right font-mono font-semibold text-[#172033]">
                            {r.currency} {Number(r.median_salary).toLocaleString()}
                          </td>
                          <td className="py-2 px-3 text-right font-mono text-[#64748B]">
                            {r.currency} {Number(r.iqr_salary).toLocaleString()}
                          </td>
                          <td className="py-2 px-3 text-center font-mono text-[11px] text-[#64748B]">
                            {Number(r.min_salary).toLocaleString()} - {Number(r.max_salary).toLocaleString()}
                          </td>
                          <td className="py-2 px-3 text-center">
                            <span
                              className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold ${
                                r.small_sample_flag
                                  ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                  : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              }`}
                            >
                              {r.small_sample_flag ? 'Small Sample (N<10)' : 'Stable'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Indicative Exchange Rates Expander */}
              <div className="rounded-xl border border-[#E2E8F0] bg-white shadow-xs overflow-hidden">
                <button
                  type="button"
                  onClick={() => setExchangeOpen(!exchangeOpen)}
                  className="flex w-full items-center justify-between p-4 text-left hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Info className="h-4 w-4 text-[#2563EB]" />
                    <span className="text-xs font-bold text-[#172033]">
                      ℹ️ Indicative Reference Exchange Rates (As of October 2026)
                    </span>
                  </div>
                  {exchangeOpen ? (
                    <ChevronUp className="h-4 w-4 text-[#64748B]" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-[#64748B]" />
                  )}
                </button>

                {exchangeOpen && (
                  <div className="border-t border-[#E2E8F0] p-4 space-y-2 text-xs">
                    <p className="text-[11px] text-[#64748B]">
                      Rates provided solely for transparent audit conversion. Strictly prohibited from inferring economic living standards or purchasing power parity.
                    </p>
                    <div className="overflow-x-auto border border-[#E2E8F0] rounded-lg">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 border-b border-[#E2E8F0]">
                          <tr className="text-[11px] font-semibold text-[#64748B]">
                            <th className="py-2 px-3">Currency</th>
                            <th className="py-2 px-3 text-right">Rate to 1.0 USD</th>
                            <th className="py-2 px-3">Effective Date</th>
                            <th className="py-2 px-3">Documented Usage</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#E2E8F0]">
                          {salaryData?.rates?.map((rt: any, idx: number) => (
                            <tr key={idx} className="hover:bg-slate-50">
                              <td className="py-1.5 px-3 font-mono font-bold text-[#172033]">{rt.currency}</td>
                              <td className="py-1.5 px-3 text-right font-mono font-semibold text-[#2563EB]">
                                {rt.rate_to_usd}
                              </td>
                              <td className="py-1.5 px-3 font-mono text-[11px] text-[#64748B]">{rt.rate_date}</td>
                              <td className="py-1.5 px-3 text-[11px] text-[#64748B]">{rt.usage}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* =====================================================================
              TAB 4: Profile Similarities
             ===================================================================== */}
          {activeTab === 4 && (
            <div className="space-y-6">
              <div className="rounded-xl border border-blue-200 bg-blue-50/60 p-4 text-xs text-[#172033]">
                <div className="font-bold text-[#2563EB] mb-1">
                  Cross-National Skill Demand Profile Similarities
                </div>
                <p className="text-[11px] text-[#64748B]">
                  Computes multidimensional similarity between country-level canonical skill demand vectors:
                  <br />
                  <strong>Cosine Similarity:</strong> Proportional alignment of national technical priorities •{' '}
                  <strong>Jaccard Overlap:</strong> Co-occurrence among top-10 in-demand skills •{' '}
                  <strong>Spearman Rank:</strong> Monotonic rank order correlation.
                </p>
              </div>

              {/* Metric Selector for Matrix */}
              <div className="flex flex-wrap items-center gap-2 rounded-xl border border-[#E2E8F0] bg-white p-3 shadow-xs">
                <span className="text-xs font-semibold text-[#172033] mr-2">
                  Select Metric for 4×4 Matrix:
                </span>
                {[
                  { id: 'cosine_similarity', label: 'Cosine Similarity (Proportional Vector Alignment)' },
                  { id: 'jaccard_top10_similarity', label: 'Jaccard Overlap (Top-10 In-Demand Skills)' },
                  { id: 'spearman_rank_correlation', label: 'Spearman Rank Correlation (Monotonic Skill Order)' },
                  { id: 'all', label: 'Compare All 3 Metrics (Side-by-Side)' },
                ].map((m) => (
                  <button
                    key={m.id}
                    onClick={() => setSelectedSimMetric(m.id as any)}
                    className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                      selectedSimMetric === m.id
                        ? 'bg-[#2563EB] text-white shadow-xs'
                        : 'bg-slate-100 text-[#64748B] hover:bg-slate-200'
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>

              {/* 4x4 Symmetric Matrix Heatmap(s) */}
              {loadingSim ? (
                <div className="flex h-40 items-center justify-center rounded-xl border border-[#E2E8F0] bg-white">
                  <RefreshCw className="h-6 w-6 animate-spin text-[#2563EB]" />
                </div>
              ) : selectedSimMetric === 'all' ? (
                <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                  {(['cosine_similarity', 'jaccard_top10_similarity', 'spearman_rank_correlation'] as const).map(
                    (mKey) => (
                      <div key={mKey} className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs">
                        <TypicalSimilarityMatrixHeatmap
                          metricKey={mKey}
                          matrixData={simData?.matrix?.[mKey]}
                          countries={simData?.countries || TARGET_COUNTRIES_LIST}
                          pairwise={simData?.pairwise || []}
                          compact={true}
                        />
                      </div>
                    )
                  )}
                </div>
              ) : (
                <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs">
                  <TypicalSimilarityMatrixHeatmap
                    metricKey={selectedSimMetric}
                    matrixData={simData?.matrix?.[selectedSimMetric]}
                    countries={simData?.countries || TARGET_COUNTRIES_LIST}
                    pairwise={simData?.pairwise || []}
                    compact={false}
                  />
                </div>
              )}

              {/* Pairwise Exact Indices Table */}
              <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-3">
                <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3">
                  <h4 className="text-xs font-bold text-[#172033] uppercase tracking-wider">
                    Pairwise Exact-Value Similarity Indices
                  </h4>
                  <a
                    href="/api/regional/download/similarities"
                    download
                    className="inline-flex items-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-3 py-1.5 text-xs font-semibold text-[#172033] hover:bg-slate-50"
                  >
                    <Download className="h-3.5 w-3.5 text-[#2563EB]" />
                    📥 Export Similarities CSV
                  </a>
                </div>

                <div className="overflow-x-auto border border-[#E2E8F0] rounded-lg">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-b border-[#E2E8F0]">
                      <tr className="text-[11px] font-semibold text-[#64748B]">
                        <th className="py-2.5 px-3">Market Pair</th>
                        <th className="py-2.5 px-3 text-center">Sample Sizes</th>
                        <th className="py-2.5 px-3 text-right">Cosine Similarity</th>
                        <th className="py-2.5 px-3 text-right">Jaccard (Top 10)</th>
                        <th className="py-2.5 px-3 text-right">Spearman Rank Corr.</th>
                        <th className="py-2.5 px-3 text-center">Sample Reliability</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E2E8F0]">
                      {simData?.pairwise?.map((r: any, idx: number) => (
                        <tr key={idx} className="hover:bg-slate-50">
                          <td className="py-2.5 px-3 font-semibold text-[#172033]">
                            {r.country_a} ↔ {r.country_b}
                          </td>
                          <td className="py-2.5 px-3 text-center font-mono text-[11px] text-[#64748B]">
                            {r.sample_size_a} vs {r.sample_size_b}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono font-bold text-[#2563EB]">
                            {Number(r.cosine_similarity).toFixed(4)}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-[#172033]">
                            {Number(r.jaccard_top10_similarity).toFixed(4)}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-[#172033]">
                            {Number(r.spearman_rank_correlation).toFixed(4)}
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            <span
                              className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold ${
                                r.sparse_sample_flag
                                  ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                  : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              }`}
                            >
                              {r.sparse_sample_flag ? 'High Uncertainty (N<10)' : 'Adequate Sample'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* =====================================================================
              TAB 5: Sensitivity Analysis
             ===================================================================== */}
          {activeTab === 5 && (
            <div className="space-y-6">
              <div className="rounded-xl border border-blue-200 bg-blue-50/60 p-4 text-xs text-[#172033]">
                <div className="font-bold text-[#2563EB] mb-1">
                  Systematic Sensitivity & Validation Regimes
                </div>
                <p className="text-[11px] text-[#64748B]">
                  Evaluates whether core analytical conclusions materially shift under 5 alternative filtering regimes (baseline, approved portals only, benchmark verified only, unambiguous roles only, and salary-disclosed subsample).
                </p>
              </div>

              <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-3">
                <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3">
                  <h4 className="text-xs font-bold text-[#172033] uppercase tracking-wider">
                    Sensitivity Scenarios & Stability Assessment
                  </h4>
                  <a
                    href="/api/regional/download/sensitivity"
                    download
                    className="inline-flex items-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-3 py-1.5 text-xs font-semibold text-[#172033] hover:bg-slate-50"
                  >
                    <Download className="h-3.5 w-3.5 text-[#2563EB]" />
                    📥 Export Sensitivity CSV
                  </a>
                </div>

                {loadingSens ? (
                  <div className="flex h-40 items-center justify-center">
                    <RefreshCw className="h-6 w-6 animate-spin text-[#2563EB]" />
                  </div>
                ) : (
                  <div className="overflow-x-auto border border-[#E2E8F0] rounded-lg">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 border-b border-[#E2E8F0]">
                        <tr className="text-[11px] font-semibold text-[#64748B]">
                          <th className="py-2.5 px-3">Scenario</th>
                          <th className="py-2.5 px-3 text-right">Eligible Ads</th>
                          <th className="py-2.5 px-3 text-center">Markets</th>
                          <th className="py-2.5 px-3 text-right">Mean MAD Shift (pp)</th>
                          <th className="py-2.5 px-3 text-right">Max Shift (pp)</th>
                          <th className="py-2.5 px-3 text-center">Stability Assessment</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#E2E8F0]">
                        {sensData?.summary?.map((r: any, idx: number) => (
                          <tr key={idx} className="hover:bg-slate-50">
                            <td className="py-2.5 px-3 font-semibold text-[#172033]">{r.scenario_name}</td>
                            <td className="py-2.5 px-3 text-right font-mono text-[#64748B]">
                              {r.total_eligible_ads}
                            </td>
                            <td className="py-2.5 px-3 text-center font-mono text-[#64748B]">
                              {r.countries_evaluated}
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono font-medium text-[#172033]">
                              {r.mean_abs_demand_shift_pp !== '' ? `${r.mean_abs_demand_shift_pp} pp` : 'N/A'}
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono font-medium text-[#172033]">
                              {r.max_demand_shift_pp !== '' ? `${r.max_demand_shift_pp} pp` : 'N/A'}
                            </td>
                            <td className="py-2.5 px-3 text-center">
                              <span
                                className={`inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                                  r.stability_assessment.includes('Robust') ||
                                  r.stability_assessment.includes('Baseline')
                                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                    : 'bg-amber-50 text-amber-700 border border-amber-200'
                                }`}
                              >
                                {r.stability_assessment}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* =====================================================================
              TAB 6: Eligibility Funnel & Audit
             ===================================================================== */}
          {activeTab === 6 && (
            <div className="space-y-6">
              <div className="rounded-xl border border-blue-200 bg-blue-50/60 p-4 text-xs text-[#172033]">
                <div className="font-bold text-[#2563EB] mb-1">
                  Documented Task Eligibility & Record Attrition Funnel
                </div>
                <p className="text-[11px] text-[#64748B]">
                  Tracks record eligibility and explicit exclusion reasons stage-by-stage across all analytical tasks.
                </p>
              </div>

              {/* Attrition Funnel Table */}
              <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-3">
                <h4 className="text-xs font-bold text-[#172033] uppercase tracking-wider">
                  Multi-Stage Record Retention Funnel
                </h4>

                {loadingFunnel ? (
                  <div className="flex h-40 items-center justify-center">
                    <RefreshCw className="h-6 w-6 animate-spin text-[#2563EB]" />
                  </div>
                ) : (
                  <div className="overflow-x-auto border border-[#E2E8F0] rounded-lg">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 border-b border-[#E2E8F0]">
                        <tr className="text-[11px] font-semibold text-[#64748B]">
                          <th className="py-2.5 px-3">Analytical Task Stage</th>
                          <th className="py-2.5 px-3 text-right">Input Ads</th>
                          <th className="py-2.5 px-3 text-right">Eligible Ads</th>
                          <th className="py-2.5 px-3 text-right">Excluded Ads</th>
                          <th className="py-2.5 px-3 text-right">Retention %</th>
                          <th className="py-2.5 px-3">Primary Exclusion Reasons</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#E2E8F0]">
                        {funnelData?.funnel?.map((r: any, idx: number) => (
                          <tr key={idx} className="hover:bg-slate-50">
                            <td className="py-2.5 px-3 font-semibold text-[#172033]">{r.stage}</td>
                            <td className="py-2.5 px-3 text-right font-mono text-[#64748B]">{r.input_records}</td>
                            <td className="py-2.5 px-3 text-right font-mono font-bold text-[#2563EB]">
                              {r.eligible_records}
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono text-rose-600">
                              {r.excluded_records}
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono font-semibold text-emerald-600">
                              {r.retention_rate_pct}%
                            </td>
                            <td className="py-2.5 px-3 text-[11px] text-[#64748B]">{r.primary_exclusions}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Download Reproducible Research Artifacts (6 CSV buttons) */}
              <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-4">
                <div className="border-b border-[#E2E8F0] pb-3">
                  <h4 className="text-sm font-bold text-[#172033]">
                    Download Reproducible Research Artifacts
                  </h4>
                  <p className="text-[11px] text-[#64748B]">
                    Direct one-click exports for academic verification and peer reproducibility.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  <a
                    href="/api/regional/download/skill_demand"
                    download
                    className="flex items-center justify-between rounded-lg border border-[#E2E8F0] p-3 text-xs font-semibold text-[#172033] hover:bg-slate-50 transition-colors"
                  >
                    <span>📥 Skill Demand CSV</span>
                    <Download className="h-4 w-4 text-[#2563EB]" />
                  </a>

                  <a
                    href="/api/regional/download/skill_gaps"
                    download
                    className="flex items-center justify-between rounded-lg border border-[#E2E8F0] p-3 text-xs font-semibold text-[#172033] hover:bg-slate-50 transition-colors"
                  >
                    <span>📥 Skill Gaps CSV</span>
                    <Download className="h-4 w-4 text-[#2563EB]" />
                  </a>

                  <a
                    href="/api/regional/download/salary_summary"
                    download
                    className="flex items-center justify-between rounded-lg border border-[#E2E8F0] p-3 text-xs font-semibold text-[#172033] hover:bg-slate-50 transition-colors"
                  >
                    <span>📥 Salary Summary CSV</span>
                    <Download className="h-4 w-4 text-[#2563EB]" />
                  </a>

                  <a
                    href="/api/regional/download/similarities"
                    download
                    className="flex items-center justify-between rounded-lg border border-[#E2E8F0] p-3 text-xs font-semibold text-[#172033] hover:bg-slate-50 transition-colors"
                  >
                    <span>📥 Profile Similarities CSV</span>
                    <Download className="h-4 w-4 text-[#2563EB]" />
                  </a>

                  <a
                    href="/api/regional/download/funnel"
                    download
                    className="flex items-center justify-between rounded-lg border border-[#E2E8F0] p-3 text-xs font-semibold text-[#172033] hover:bg-slate-50 transition-colors"
                  >
                    <span>📥 Eligibility Funnel CSV</span>
                    <Download className="h-4 w-4 text-[#2563EB]" />
                  </a>

                  <a
                    href="/api/regional/download/sensitivity"
                    download
                    className="flex items-center justify-between rounded-lg border border-[#E2E8F0] p-3 text-xs font-semibold text-[#172033] hover:bg-slate-50 transition-colors"
                  >
                    <span>📥 Sensitivity Analysis CSV</span>
                    <Download className="h-4 w-4 text-[#2563EB]" />
                  </a>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          SCOPE 2: Single-Batch Role Segmentation
         ========================================================================= */}
      {analyticalScope === 'single_batch' && (
        <div className="space-y-6">
          <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-3">
            <h3 className="text-base font-bold text-[#172033]">Role based skill demand segmentation</h3>
            <p className="text-xs text-[#64748B] max-w-3xl leading-relaxed">
              Groups job postings by IT role, then shows how often each skill appears within that role, separating skills that are core to the role from ones that only show up in a few postings.
            </p>

            <div className="pt-2 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={handleExecuteSingleRoleAnalysis}
                disabled={singleExecuting}
                className="inline-flex items-center gap-2 rounded-xl bg-[#2563EB] px-4 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-[#1D4ED8] disabled:opacity-50 transition-all"
              >
                {singleExecuting ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    Classifying job postings into role categories...
                  </>
                ) : (
                  <>
                    <Briefcase className="h-3.5 w-3.5" />
                    Classify roles & analyze skill demand
                  </>
                )}
              </button>

              {singleBatchData?.has_extracted_data && (
                <span className="text-xs text-slate-500 font-medium">
                  {singleBatchData.extracted_count?.toLocaleString()} extracted records available for role classification.
                </span>
              )}
            </div>
          </div>

          {singleBatchData?.analysis_completed && (
            <div className="space-y-6">
              {/* Job Postings by Role Category Chart */}
              <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-4">
                <h4 className="text-sm font-bold text-[#172033]">Job postings by role category</h4>
                <div className="space-y-2.5">
                  {Object.entries(singleBatchData.role_counts || {})
                    .sort(([, a], [, b]) => (b as number) - (a as number))
                    .map(([roleName, count]: [string, any]) => {
                      const totalJobs = singleBatchData.total_jobs_classified || 1;
                      const pct = Math.min(100, Math.round((count / totalJobs) * 100));
                      return (
                        <div key={roleName} className="space-y-1">
                          <div className="flex items-center justify-between text-xs font-medium">
                            <span className="text-[#172033] font-semibold">{roleName}</span>
                            <span className="font-mono text-[#64748B]">{count} jobs ({pct}%)</span>
                          </div>
                          <div className="h-3 w-full rounded-full bg-slate-100 overflow-hidden">
                            <div
                              className="h-full rounded-full bg-[#2563EB]"
                              style={{ width: `${pct}%` }}
                            ></div>
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>

              {/* Skill Demand by Role — Lexical vs Semantic */}
              <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E2E8F0] pb-3">
                  <div>
                    <h4 className="text-sm font-bold text-[#172033]">
                      Skill demand by role — lexical vs semantic
                    </h4>
                    <p className="text-[11px] text-[#64748B]">
                      Compares extraction detection frequencies across extraction pipelines.
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-[#64748B] font-medium">Choose a role:</span>
                    <select
                      value={singleSelectedRole}
                      onChange={(e) => setSingleSelectedRole(e.target.value)}
                      className="rounded-lg border border-[#E2E8F0] bg-white px-3 py-1.5 text-xs text-[#172033] focus:outline-none focus:border-[#2563EB]"
                    >
                      {singleBatchData?.role_options?.map((r: string) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Filter and display top skills for selected role */}
                {(() => {
                  const roleRows = (singleBatchData.frequencies || []).filter(
                    (f: any) => f.role_name === singleSelectedRole
                  );
                  const skillsMap: Record<string, { lexical: number; semantic: number }> = {};
                  roleRows.forEach((r: any) => {
                    if (!skillsMap[r.skill]) skillsMap[r.skill] = { lexical: 0, semantic: 0 };
                    if (r.method === 'lexical') skillsMap[r.skill].lexical = r.job_count;
                    if (r.method === 'semantic') skillsMap[r.skill].semantic = r.job_count;
                  });

                  const sortedSkills = Object.entries(skillsMap)
                    .map(([skill, counts]) => ({
                      skill,
                      ...counts,
                      total: counts.lexical + counts.semantic,
                    }))
                    .sort((a, b) => b.total - a.total)
                    .slice(0, 10);

                  if (sortedSkills.length === 0) {
                    return (
                      <div className="p-8 text-center text-xs text-[#64748B]">
                        No skills were extracted for '{singleSelectedRole}' yet.
                      </div>
                    );
                  }

                  const maxCount = Math.max(...sortedSkills.map((s) => Math.max(s.lexical, s.semantic, 1)));

                  return (
                    <div className="space-y-3 pt-2">
                      <div className="flex items-center justify-end gap-4 text-xs">
                        <div className="flex items-center gap-1.5">
                          <span className="h-3 w-3 rounded bg-[#2563EB]"></span>
                          <span className="text-[#64748B]">Lexical Skills</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="h-3 w-3 rounded bg-purple-600"></span>
                          <span className="text-[#64748B]">Semantic Skills</span>
                        </div>
                      </div>

                      {sortedSkills.map((item) => (
                        <div key={item.skill} className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-semibold text-[#172033]">{item.skill}</span>
                            <span className="font-mono text-[11px] text-[#64748B]">
                              Lex: {item.lexical} | Sem: {item.semantic}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            <div className="h-2.5 w-full rounded-full bg-slate-100 overflow-hidden">
                              <div
                                className="h-full rounded-full bg-[#2563EB]"
                                style={{ width: `${(item.lexical / maxCount) * 100}%` }}
                              ></div>
                            </div>
                            <div className="h-2.5 w-full rounded-full bg-slate-100 overflow-hidden">
                              <div
                                className="h-full rounded-full bg-purple-600"
                                style={{ width: `${(item.semantic / maxCount) * 100}%` }}
                              ></div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </div>

              {/* Skill Demand by Role Table */}
              <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E2E8F0] pb-3">
                  <h4 className="text-sm font-bold text-[#172033]">Skill demand by role table</h4>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      placeholder="Filter role or skill..."
                      value={singleSearch}
                      onChange={(e) => setSingleSearch(e.target.value)}
                      className="rounded-lg border border-[#E2E8F0] px-3 py-1.5 text-xs text-[#172033] focus:outline-none focus:border-[#2563EB]"
                    />
                    <a
                      href="/api/regional/role-segmentation/download"
                      download
                      className="inline-flex items-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-3 py-1.5 text-xs font-semibold text-[#172033] shadow-2xs hover:bg-slate-50"
                    >
                      <Download className="h-3.5 w-3.5 text-[#2563EB]" />
                      Download role x skill frequency CSV
                    </a>
                  </div>
                </div>

                <div className="max-h-80 overflow-y-auto border border-[#E2E8F0] rounded-lg">
                  <table className="w-full text-left text-xs">
                    <thead className="sticky top-0 bg-slate-50 border-b border-[#E2E8F0]">
                      <tr className="text-[11px] font-semibold text-[#64748B]">
                        <th className="py-2.5 px-3">Role Name</th>
                        <th className="py-2.5 px-3">Skill</th>
                        <th className="py-2.5 px-3">Method</th>
                        <th className="py-2.5 px-3 text-right">Job Count</th>
                        <th className="py-2.5 px-3 text-right">Total Jobs in Role</th>
                        <th className="py-2.5 px-3 text-right">Pct of Role</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E2E8F0]">
                      {(singleBatchData.frequencies || [])
                        .filter(
                          (r: any) =>
                            !singleSearch ||
                            r.role_name.toLowerCase().includes(singleSearch.toLowerCase()) ||
                            r.skill.toLowerCase().includes(singleSearch.toLowerCase())
                        )
                        .map((r: any, idx: number) => (
                          <tr key={idx} className="hover:bg-slate-50">
                            <td className="py-2 px-3 font-semibold text-[#172033]">{r.role_name}</td>
                            <td className="py-2 px-3 font-medium text-[#2563EB]">{r.skill}</td>
                            <td className="py-2 px-3">
                              <span
                                className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-bold ${
                                  r.method === 'lexical'
                                    ? 'bg-blue-50 text-blue-700'
                                    : 'bg-purple-50 text-purple-700'
                                }`}
                              >
                                {r.method}
                              </span>
                            </td>
                            <td className="py-2 px-3 text-right font-mono">{r.job_count}</td>
                            <td className="py-2 px-3 text-right font-mono text-[#64748B]">
                              {r.total_jobs_in_role}
                            </td>
                            <td className="py-2 px-3 text-right font-mono font-bold text-[#172033]">
                              {r.pct_of_role}%
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
