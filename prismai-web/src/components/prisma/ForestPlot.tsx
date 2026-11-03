"use client";

import type { ForestData } from "@/lib/api/synthesis";

interface Props {
  data: ForestData;
  width?: number;
  height?: number;
}

export function ForestPlot({ data, width = 700, height: propHeight }: Props) {
  const rowH = 28;
  const labelW = 180;
  const plotL = labelW + 20;
  const plotR = width - 80;
  const plotW = plotR - plotL;
  const topPad = 40;
  const bottomPad = 40;
  const rows = data.studies.length;
  const height = propHeight ?? topPad + rows * rowH + rowH + bottomPad;

  const allVals = [
    ...data.studies.map((s) => s.ci_low),
    ...data.studies.map((s) => s.ci_high),
    data.pooled.ci_low,
    data.pooled.ci_high,
  ].filter((v): v is number => v != null && isFinite(v));
  const xMin = Math.min(...allVals, 0);
  const xMax = Math.max(...allVals, 0);
  const pad = (xMax - xMin) * 0.1 || 0.5;
  const domainMin = xMin - pad;
  const domainMax = xMax + pad;

  const scaleX = (v: number) => plotL + ((v - domainMin) / (domainMax - domainMin)) * plotW;
  const zeroX = scaleX(0);

  const maxW = Math.max(...data.studies.map((s) => s.weight), 1);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full max-w-[44rem]" style={{ fontFamily: "'Geist', system-ui, sans-serif" }}>
      <text x={plotL + plotW / 2} y={16} textAnchor="middle" className="fill-zinc-600 dark:fill-zinc-400" fontSize={11} fontWeight={600}>
        {data.measure.toUpperCase()} — modelo {data.model} (I²={((data.i2 ?? 0) * 100).toFixed(0)}%)
      </text>

      {/* null line */}
      <line x1={zeroX} y1={topPad - 5} x2={zeroX} y2={topPad + rows * rowH + rowH} stroke="#a1a1aa" strokeWidth={1} strokeDasharray="4 3" />

      {data.studies.map((s, i) => {
        const y = topPad + i * rowH + rowH / 2;
        const x1 = scaleX(s.ci_low);
        const x2 = scaleX(s.ci_high);
        const cx = scaleX(s.yi);
        const r = 3 + (s.weight / maxW) * 5;
        return (
          <g key={s.label + i}>
            <text x={labelW} y={y + 4} textAnchor="end" fontSize={10} className="fill-zinc-700 dark:fill-zinc-300">
              {s.label.length > 24 ? s.label.slice(0, 22) + "…" : s.label}
            </text>
            <line x1={x1} y1={y} x2={x2} y2={y} stroke="#71717a" strokeWidth={1.5} />
            <rect x={cx - r} y={y - r} width={r * 2} height={r * 2} fill={s.incluido ? "#18181b" : "#a1a1aa"} rx={1} />
            <text x={plotR + 8} y={y + 4} fontSize={9} className="fill-zinc-500">
              {s.yi.toFixed(2)} [{s.ci_low.toFixed(2)}, {s.ci_high.toFixed(2)}]
            </text>
          </g>
        );
      })}

      {/* pooled diamond */}
      {(() => {
        const y = topPad + rows * rowH + rowH / 2;
        const cx = scaleX(data.pooled.yi);
        const lx = scaleX(data.pooled.ci_low);
        const rx = scaleX(data.pooled.ci_high);
        const dh = 7;
        return (
          <g>
            <text x={labelW} y={y + 4} textAnchor="end" fontSize={10} fontWeight={700} className="fill-zinc-900 dark:fill-zinc-100">
              Pooled
            </text>
            <polygon points={`${lx},${y} ${cx},${y - dh} ${rx},${y} ${cx},${y + dh}`} fill="#18181b" className="dark:fill-zinc-200" />
            <text x={plotR + 8} y={y + 4} fontSize={9} fontWeight={600} className="fill-zinc-700 dark:fill-zinc-300">
              {data.pooled.yi.toFixed(2)} [{data.pooled.ci_low.toFixed(2)}, {data.pooled.ci_high.toFixed(2)}]
            </text>
          </g>
        );
      })()}

      {/* x axis */}
      <line x1={plotL} y1={topPad + rows * rowH + rowH + 10} x2={plotR} y2={topPad + rows * rowH + rowH + 10} stroke="#d4d4d8" strokeWidth={1} />
      <text x={plotL} y={height - 5} fontSize={9} className="fill-zinc-400">{domainMin.toFixed(1)}</text>
      <text x={plotR} y={height - 5} textAnchor="end" fontSize={9} className="fill-zinc-400">{domainMax.toFixed(1)}</text>
      <text x={zeroX} y={height - 5} textAnchor="middle" fontSize={9} className="fill-zinc-500">0</text>
    </svg>
  );
}
