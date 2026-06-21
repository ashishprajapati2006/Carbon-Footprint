import React from "react";
import { BillAnalysis } from "@/types";

interface UtilityTrendChartProps {
  history: BillAnalysis[];
}

export const UtilityTrendChart: React.FC<UtilityTrendChartProps> = ({ history }) => {
  if (history.length < 1) return null;

  // Sort chronologically (ascending by period) and filter for kWh (electricity) trends
  const kwhHistory = history
    .filter((h) => h.consumption_unit === "kWh")
    .map((h) => ({ period: h.billing_period, val: h.consumption_value }))
    .sort((a, b) => a.period.localeCompare(b.period))
    .slice(-6); // Last 6 periods

  if (kwhHistory.length === 0) return null;

  const maxVal = Math.max(...kwhHistory.map((h) => h.val), 100) * 1.15;
  const svgWidth = 480;
  const svgHeight = 160;
  const chartHeight = 110;

  // Compute X, Y coordinates
  const points = kwhHistory.map((d, i) => {
    const x = 50 + i * (400 / Math.max(1, kwhHistory.length - 1));
    const y = 130 - (d.val / maxVal) * chartHeight;
    return { x, y, val: d.val, label: d.period };
  });

  const pathData = points.reduce((acc, p, i) => {
    return i === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`;
  }, "");

  const areaData =
    points.length > 0
      ? `${pathData} L ${points[points.length - 1].x} 130 L ${points[0].x} 130 Z`
      : "";

  return (
    <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-44 text-xs">
      <defs>
        <linearGradient id="chart-area-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#10b981" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
        </linearGradient>
      </defs>

      {/* Grid lines */}
      <line x1="40" y1="20" x2="460" y2="20" stroke="#1e293b" strokeWidth="1" strokeDasharray="3,3" />
      <line x1="40" y1="75" x2="460" y2="75" stroke="#1e293b" strokeWidth="1" strokeDasharray="3,3" />
      <line x1="40" y1="130" x2="460" y2="130" stroke="#334155" strokeWidth="1" />

      {/* Y Axis Labels */}
      <text x="32" y="24" fill="#64748b" fontSize="7" textAnchor="end" fontFamily="monospace">
        {Math.round(maxVal)}
      </text>
      <text x="32" y="79" fill="#64748b" fontSize="7" textAnchor="end" fontFamily="monospace">
        {Math.round(maxVal / 2)}
      </text>
      <text x="32" y="134" fill="#64748b" fontSize="7" textAnchor="end" fontFamily="monospace">
        0
      </text>

      {/* Area Fill */}
      {areaData && <path d={areaData} fill="url(#chart-area-grad)" />}

      {/* Line Path */}
      {pathData && <path d={pathData} fill="none" stroke="#10b981" strokeWidth="2" />}

      {/* Points & Labels */}
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r="3.5" fill="#10b981" stroke="#0f172a" strokeWidth="1.5" />
          <text x={p.x} y={p.y - 7} fill="#a7f3d0" fontSize="7" fontWeight="bold" textAnchor="middle">
            {Math.round(p.val)}
          </text>
          <text x={p.x} y="145" fill="#64748b" fontSize="8" fontWeight="bold" textAnchor="middle">
            {p.label.substring(5)}
          </text>
        </g>
      ))}
    </svg>
  );
};
