"use client";

import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { screeningApi, type Decision, type Conflict } from "@/lib/api/screening";
import { useJobStream } from "@/hooks/useJobStream";
import { useFlow } from "@/hooks/useFlow";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Progress } from "@/components/ui/Progress";
import { SCREENING_DECISION, CONFIDENCE, lookupVocab } from "@/lib/vocab";
import { useState } from "react";

export default function ScreeningPage() {
  const { reviewId } = useParams() as { reviewId: string };
  const qc = useQueryClient();
  const { invalidate } = useFlow(reviewId);
  const [jobId, setJobId] = useState<string | null>(null);
  const { progress, total, done } = useJobStream(jobId);

  const { data: decisions } = useQuery({
    queryKey: ["decisions", reviewId],
    queryFn: () => screeningApi.decisions(reviewId),
    refetchInterval: jobId && !done ? 5000 : false,
  });
  const { data: conflicts } = useQuery({
    queryKey: ["conflicts", reviewId],
    queryFn: () => screeningApi.conflicts(reviewId),
  });
  const { data: agreement } = useQuery({
    queryKey: ["agreement", reviewId],
    queryFn: () => screeningApi.agreement(reviewId).catch(() => null),
  });

  const run = useMutation({
    mutationFn: () => screeningApi.run(reviewId),
    onSuccess: (r) => setJobId(r.job_id),
  });

  if (done && jobId) {
    qc.invalidateQueries({ queryKey: ["decisions", reviewId] });
    qc.invalidateQueries({ queryKey: ["conflicts", reviewId] });
    qc.invalidateQueries({ queryKey: ["agreement", reviewId] });
    invalidate();
    setJobId(null);
  }

  const resolve = useMutation({
    mutationFn: ({ rid, decision }: { rid: string; decision: string }) =>
      screeningApi.resolveConflict(reviewId, rid, decision),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["conflicts", reviewId] });
      qc.invalidateQueries({ queryKey: ["agreement", reviewId] });
    },
  });

  const pending = conflicts?.filter((c) => c.status === "pending") ?? [];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">Triagem</h2>
        <Button onClick={() => run.mutate()} loading={run.isPending || (!!jobId && !done)}>
          {jobId && !done ? "Triando…" : "Iniciar triagem"}
        </Button>
      </div>

      {jobId && !done && (
        <Card>
          <p className="text-xs text-zinc-500 mb-2">Progresso: {progress}/{total}</p>
          <Progress value={progress} max={total} />
        </Card>
      )}

      {agreement && (
        <Card>
          <h3 className="text-sm font-semibold mb-2 text-zinc-600 dark:text-zinc-400">Concordância</h3>
          <div className="flex gap-6 text-sm">
            <span>κ = <strong>{agreement.kappa.toFixed(3)}</strong></span>
            <span>{agreement.n_agree} concordam</span>
            <span>{agreement.n_conflict} conflitos</span>
            <span>{agreement.n_total} total</span>
          </div>
        </Card>
      )}

      {pending.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">
            Conflitos pendentes ({pending.length})
          </h3>
          <div className="space-y-3">
            {pending.map((c: Conflict) => (
              <div key={c.registro_id} className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-2">
                <div className="text-xs">
                  <p className="font-mono">{c.registro_id.slice(0, 16)}</p>
                  <p className="text-zinc-400">
                    {c.screener_a}: {c.decision_a} vs {c.screener_b}: {c.decision_b} (score: {c.disagreement_score.toFixed(2)})
                  </p>
                </div>
                <div className="flex gap-1">
                  <Button variant="ghost" className="text-xs" onClick={() => resolve.mutate({ rid: c.registro_id, decision: "include" })}>
                    Incluir
                  </Button>
                  <Button variant="ghost" className="text-xs" onClick={() => resolve.mutate({ rid: c.registro_id, decision: "exclude" })}>
                    Excluir
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card>
        <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">
          Decisões ({decisions?.length ?? 0})
        </h3>
        {decisions && decisions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-700">
                  <th className="text-left py-2 px-2">Registro</th>
                  <th className="text-left py-2 px-2">Decisão</th>
                  <th className="text-left py-2 px-2">Confiança</th>
                  <th className="text-left py-2 px-2">Razões</th>
                </tr>
              </thead>
              <tbody>
                {decisions.map((d: Decision) => {
                  const dec = lookupVocab(SCREENING_DECISION, d.decision, { label: d.decision, color: "text-zinc-500" });
                  const conf = lookupVocab(CONFIDENCE, d.confidence, { label: d.confidence, color: "text-zinc-500" });
                  return (
                    <tr key={d.registro_id} className="border-b border-zinc-100 dark:border-zinc-800">
                      <td className="py-1.5 px-2 font-mono">{d.registro_id.slice(0, 16)}</td>
                      <td className="py-1.5 px-2">
                        <Badge className={(dec as { bg?: string; border?: string }).bg + " " + (dec as { border?: string }).border + " " + (dec as { color: string }).color}>
                          {(dec as { label: string }).label}
                        </Badge>
                      </td>
                      <td className={`py-1.5 px-2 ${(conf as { color: string }).color}`}>{(conf as { label: string }).label}</td>
                      <td className="py-1.5 px-2 text-zinc-500">{d.reasons.join("; ")}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-zinc-400">Nenhuma decisão ainda.</p>
        )}
      </Card>
    </div>
  );
}
