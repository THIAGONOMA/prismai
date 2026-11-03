"use client";

import { ROB2_JUDGMENT } from "@/lib/vocab";
import type { RobAssessment } from "@/lib/api/extraction";

interface Props {
  assessments: RobAssessment[];
}

const DOMAINS = [
  "randomization",
  "deviations",
  "missing_data",
  "measurement",
  "selection",
];
const DOMAIN_LABELS: Record<string, string> = {
  randomization: "D1",
  deviations: "D2",
  missing_data: "D3",
  measurement: "D4",
  selection: "D5",
};

function judgmentColor(j: string) {
  const entry = ROB2_JUDGMENT[j as keyof typeof ROB2_JUDGMENT];
  return entry?.color ?? "#a1a1aa";
}

export function RobTrafficLight({ assessments }: Props) {
  if (assessments.length === 0) return <p className="text-sm text-zinc-400">Nenhuma avaliação RoB 2 disponível.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-xs">
        <thead>
          <tr className="border-b border-zinc-200 dark:border-zinc-700">
            <th className="text-left py-2 px-2 font-medium text-zinc-500">Estudo</th>
            {DOMAINS.map((d) => (
              <th key={d} className="text-center py-2 px-1 font-medium text-zinc-500">{DOMAIN_LABELS[d] ?? d}</th>
            ))}
            <th className="text-center py-2 px-2 font-medium text-zinc-500">Geral</th>
          </tr>
        </thead>
        <tbody>
          {assessments.map((a) => (
            <tr key={a.record_id} className="border-b border-zinc-100 dark:border-zinc-800">
              <td className="py-1.5 px-2 font-mono text-zinc-700 dark:text-zinc-300">{a.record_id.slice(0, 12)}</td>
              {DOMAINS.map((d) => {
                const dr = a.domain_results.find((r) => r.domain === d);
                const j = dr?.judgment ?? "unknown";
                return (
                  <td key={d} className="text-center py-1.5 px-1">
                    <span
                      className="inline-block h-4 w-4 rounded-full"
                      style={{ backgroundColor: judgmentColor(j) }}
                      title={j}
                    />
                  </td>
                );
              })}
              <td className="text-center py-1.5 px-2">
                <span
                  className="inline-block h-4 w-4 rounded-full"
                  style={{ backgroundColor: judgmentColor(a.overall_judgment) }}
                  title={a.overall_judgment}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
