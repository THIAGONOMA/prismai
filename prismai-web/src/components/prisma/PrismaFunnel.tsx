"use client";

import { motion } from "framer-motion";
import type { FlowCounts } from "@/lib/api/report";
import { FLOW_DISCREPANCY_LABEL } from "@/lib/vocab";

interface Props {
  flow?: FlowCounts;
  compact?: boolean;
}

interface StageProps {
  label: string;
  count: number;
  accent?: string;
  delay: number;
}

function Stage({ label, count, accent = "bg-zinc-800 dark:bg-zinc-200", delay }: StageProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.3 }}
      className="flex flex-col items-center gap-1"
    >
      <div className={`${accent} text-white dark:text-zinc-900 rounded-lg px-3 py-1.5 text-xs font-semibold tabular-nums min-w-[3.5rem] text-center`}>
        {count.toLocaleString("pt-BR")}
      </div>
      <span className="text-[10px] text-zinc-500 dark:text-zinc-400 text-center leading-tight">{label}</span>
    </motion.div>
  );
}

function Arrow() {
  return (
    <div className="flex items-center text-zinc-300 dark:text-zinc-600">
      <svg width="20" height="12" viewBox="0 0 20 12"><path d="M0 6h16m0 0l-4-4m4 4l-4 4" stroke="currentColor" strokeWidth="1.5" fill="none" /></svg>
    </div>
  );
}

export function PrismaFunnel({ flow, compact }: Props) {
  if (!flow) {
    return (
      <div className="flex items-center justify-center py-4 text-sm text-zinc-400">
        Carregando funil PRISMA…
      </div>
    );
  }

  const stages: { label: string; count: number; accent?: string }[] = [
    { label: "Identificados", count: flow.identificados_total },
    { label: "Duplicatas", count: flow.duplicatas_removidas, accent: "bg-zinc-500" },
    { label: "Triados", count: flow.registros_triados },
    { label: "Excluídos", count: flow.registros_excluidos, accent: "bg-red-500" },
    { label: "Full-text", count: flow.fulltext_buscados },
    { label: "Não recuperados", count: flow.fulltext_nao_recuperados, accent: "bg-amber-500" },
    { label: "Avaliados", count: flow.fulltext_avaliados },
    { label: "Incluídos", count: flow.estudos_incluidos, accent: "bg-emerald-600" },
  ];

  const hasDiscrepancies = flow.discrepancias && flow.discrepancias.length > 0;

  return (
    <div className="space-y-3">
      <div className={`flex items-center gap-1 overflow-x-auto pb-2 ${compact ? "scale-90 origin-left" : ""}`}>
        {stages.map((s, i) => (
          <div key={s.label} className="flex items-center gap-1">
            {i > 0 && <Arrow />}
            <Stage label={s.label} count={s.count} accent={s.accent} delay={i * 0.05} />
          </div>
        ))}
      </div>
      {hasDiscrepancies && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950 p-3 text-xs text-amber-700 dark:text-amber-300 space-y-1">
          <p className="font-semibold">⚠ Discrepâncias no fluxo</p>
          {flow.discrepancias.map((d) => (
            <p key={d.invariante}>
              {FLOW_DISCREPANCY_LABEL[d.invariante] ?? d.invariante}: esperado {d.esperado}, encontrado {d.encontrado}
              {d.detalhe && ` — ${d.detalhe}`}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
