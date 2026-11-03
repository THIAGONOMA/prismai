"use client";

import type { FunnelData } from "@/lib/api/synthesis";

interface Props {
  data: FunnelData;
  width?: number;
  height?: number;
}

export function FunnelPlot({ data, width = 400, height = 350 }: Props) {
  const pad = { top: 30, right: 30, bottom: 40, left: 60 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const allYi = data.points.map((p) => p.yi);
  const allSe = data.points.map((p) => p.se);
  const yiMin = Math.min(...allYi, data.pooled) - 0.5;
  const yiMax = Math.max(...allYi, data.pooled) + 0.5;
  const seMax = Math.max(...allSe) * 1.1;

  const scaleX = (v: number) => pad.left + ((v - yiMin) / (yiMax - yiMin)) * plotW;
  const scaleY = (v: number) => pad.top + (v / seMax) * plotH;
  const pooledX = scaleX(data.pooled);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full max-w-[25rem]" style={{ fontFamily: "'Geist', system-ui, sans-serif" }}>
      <text x={width / 2} y={16} textAnchor="middle" fontSize={11} fontWeight={600} className="fill-zinc-600 dark:fill-zinc-400">
        Funnel Plot
      </text>

      {/* pseudo-CI region */}
      <polygon
        points={`${pooledX},${pad.top} ${scaleX(data.pooled - 1.96 * seMax)},${pad.top + plotH} ${scaleX(data.pooled + 1.96 * seMax)},${pad.top + plotH}`}
        fill="#f4f4f5"
        className="dark:fill-zinc-800"
        opacity={0.6}
      />

      {/* pooled line */}
      <line x1={pooledX} y1={pad.top} x2={pooledX} y2={pad.top + plotH} stroke="#a1a1aa" strokeWidth={1} strokeDasharray="4 3" />

      {/* points */}
      {data.points.map((p, i) => (
        <circle key={i} cx={scaleX(p.yi)} cy={scaleY(p.se)} r={3.5} fill="#18181b" className="dark:fill-zinc-200" opacity={0.8} />
      ))}

      {/* axes */}
      <line x1={pad.left} y1={pad.top + plotH} x2={pad.left + plotW} y2={pad.top + plotH} stroke="#d4d4d8" />
      <line x1={pad.left} y1={pad.top} x2={pad.left} y2={pad.top + plotH} stroke="#d4d4d8" />
      <text x={width / 2} y={height - 4} textAnchor="middle" fontSize={10} className="fill-zinc-500">Efeito</text>
      <text x={14} y={pad.top + plotH / 2} textAnchor="middle" fontSize={10} className="fill-zinc-500" transform={`rotate(-90, 14, ${pad.top + plotH / 2})`}>SE</text>
    </svg>
  );
}
