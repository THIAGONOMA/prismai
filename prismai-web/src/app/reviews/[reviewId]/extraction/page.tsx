"use client";

import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { extractionApi, type Extraction, type ExtractionCell } from "@/lib/api/extraction";
import { useJobStream } from "@/hooks/useJobStream";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Progress } from "@/components/ui/Progress";
import { RobTrafficLight } from "@/components/prisma/RobTrafficLight";
import { CONFIDENCE, lookupVocab } from "@/lib/vocab";
import { useState } from "react";

export default function ExtractionPage() {
  const { reviewId } = useParams() as { reviewId: string };
  const qc = useQueryClient();
  const [extJobId, setExtJobId] = useState<string | null>(null);
  const [robJobId, setRobJobId] = useState<string | null>(null);
  const extStream = useJobStream(extJobId);
  const robStream = useJobStream(robJobId);

  const { data: extractions } = useQuery({
    queryKey: ["extractions", reviewId],
    queryFn: () => extractionApi.list(reviewId),
  });
  const { data: robAssessments } = useQuery({
    queryKey: ["rob", reviewId],
    queryFn: () => extractionApi.robList(reviewId),
  });

  const runExt = useMutation({
    mutationFn: () => extractionApi.run(reviewId),
    onSuccess: (r) => setExtJobId(r.job_id),
  });
  const runRob = useMutation({
    mutationFn: () => extractionApi.robRun(reviewId),
    onSuccess: (r) => setRobJobId(r.job_id),
  });

  if (extStream.done && extJobId) {
    qc.invalidateQueries({ queryKey: ["extractions", reviewId] });
    setExtJobId(null);
  }
  if (robStream.done && robJobId) {
    qc.invalidateQueries({ queryKey: ["rob", reviewId] });
    setRobJobId(null);
  }

  const [selected, setSelected] = useState<string | null>(null);
  const selectedExt = extractions?.find((e: Extraction) => e.record_id === selected);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">Extração & RoB 2</h2>
        <div className="flex gap-2">
          <Button onClick={() => runExt.mutate()} loading={runExt.isPending || (!!extJobId && !extStream.done)}>
            Extrair dados
          </Button>
          <Button variant="secondary" onClick={() => runRob.mutate()} loading={runRob.isPending || (!!robJobId && !robStream.done)}>
            Avaliar RoB 2
          </Button>
        </div>
      </div>

      {extJobId && !extStream.done && (
        <Card>
          <p className="text-xs text-zinc-500 mb-2">Extração: {extStream.progress}/{extStream.total}</p>
          <Progress value={extStream.progress} max={extStream.total} />
        </Card>
      )}
      {robJobId && !robStream.done && (
        <Card>
          <p className="text-xs text-zinc-500 mb-2">RoB: {robStream.progress}/{robStream.total}</p>
          <Progress value={robStream.progress} max={robStream.total} />
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1">
          <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">Estudos extraídos</h3>
          <div className="space-y-1 max-h-96 overflow-y-auto">
            {extractions?.map((e: Extraction) => (
              <button
                key={e.record_id}
                onClick={() => setSelected(e.record_id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${
                  selected === e.record_id ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900" : "hover:bg-zinc-100 dark:hover:bg-zinc-800"
                }`}
              >
                <span className="font-mono">{e.record_id.slice(0, 20)}</span>
                <span className="ml-2 text-zinc-400">{e.cells.length} células</span>
              </button>
            )) ?? <p className="text-sm text-zinc-400">Nenhuma extração.</p>}
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">
            {selectedExt ? `Células — ${selectedExt.record_id.slice(0, 20)}` : "Selecione um estudo"}
          </h3>
          {selectedExt ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-xs">
                <thead>
                  <tr className="border-b border-zinc-200 dark:border-zinc-700">
                    <th className="text-left py-2 px-2">Campo</th>
                    <th className="text-left py-2 px-2">Bloco</th>
                    <th className="text-left py-2 px-2">Valor</th>
                    <th className="text-left py-2 px-2">Conf.</th>
                    <th className="text-left py-2 px-2">Âncora</th>
                    <th className="text-left py-2 px-2">Flags</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedExt.cells.map((c: ExtractionCell, i: number) => {
                    const conf = lookupVocab(CONFIDENCE, c.confidence ?? "low", { label: c.confidence ?? "low", color: "text-zinc-500" });
                    return (
                      <tr key={i} className={`border-b border-zinc-100 dark:border-zinc-800 ${c.needs_human_confirmation ? "bg-amber-50 dark:bg-amber-950" : ""}`}>
                        <td className="py-1.5 px-2 font-medium">{c.field}</td>
                        <td className="py-1.5 px-2 text-zinc-500">{c.block}</td>
                        <td className="py-1.5 px-2 font-mono">{String(c.value ?? "—")}</td>
                        <td className={`py-1.5 px-2 ${(conf as { color: string }).color}`}>{(conf as { label: string }).label}</td>
                        <td className="py-1.5 px-2 text-zinc-400">
                          {c.page != null ? `p.${c.page}` : ""}
                          {c.evidence_text ? ` "${c.evidence_text.slice(0, 40)}…"` : ""}
                        </td>
                        <td className="py-1.5 px-2">
                          {c.needs_human_confirmation && <Badge className="bg-amber-100 text-amber-700 text-[10px]">Confirmar</Badge>}
                          {c.flags?.map((f, j) => <Badge key={j} className="bg-zinc-100 text-zinc-600 text-[10px] ml-1">{f}</Badge>)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {selectedExt.consistency_flags && selectedExt.consistency_flags.length > 0 && (
                <div className="mt-3 text-xs text-amber-600">
                  Flags de consistência: {selectedExt.consistency_flags.join(", ")}
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-zinc-400">Selecione um estudo à esquerda para ver as células extraídas.</p>
          )}
        </Card>
      </div>

      <Card>
        <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">Risco de Viés (RoB 2) — Semáforo</h3>
        <RobTrafficLight assessments={robAssessments ?? []} />
      </Card>
    </div>
  );
}
