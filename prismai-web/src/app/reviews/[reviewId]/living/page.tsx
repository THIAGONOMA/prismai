"use client";

import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { livingApi, type LivingUpdate } from "@/lib/api/living";
import { useJobStream } from "@/hooks/useJobStream";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Progress } from "@/components/ui/Progress";
import { IMPACT_TYPE } from "@/lib/vocab";
import { useState } from "react";

export default function LivingPage() {
  const { reviewId } = useParams() as { reviewId: string };
  const qc = useQueryClient();
  const [jobId, setJobId] = useState<string | null>(null);
  const stream = useJobStream(jobId);
  const [cron, setCron] = useState("0 3 * * 1");

  const { data: status } = useQuery({
    queryKey: ["living-status", reviewId],
    queryFn: () => livingApi.status(reviewId).catch(() => null),
  });
  const { data: updates } = useQuery({
    queryKey: ["living-updates", reviewId],
    queryFn: () => livingApi.updates(reviewId).catch(() => []),
  });

  const enable = useMutation({
    mutationFn: () => livingApi.enable(reviewId, cron),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["living-status", reviewId] }),
  });
  const disable = useMutation({
    mutationFn: () => livingApi.disable(reviewId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["living-status", reviewId] }),
  });
  const runNow = useMutation({
    mutationFn: () => livingApi.run(reviewId),
    onSuccess: (r) => setJobId(r.job_id),
  });

  if (stream.done && jobId) {
    qc.invalidateQueries({ queryKey: ["living-status", reviewId] });
    qc.invalidateQueries({ queryKey: ["living-updates", reviewId] });
    setJobId(null);
  }

  const isEnabled = status?.enabled ?? false;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">Revisão Viva</h2>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            onClick={() => runNow.mutate()}
            loading={runNow.isPending || (!!jobId && !stream.done)}
          >
            Executar agora
          </Button>
        </div>
      </div>

      {jobId && !stream.done && (
        <Card>
          <p className="text-xs text-zinc-500 mb-2">Atualização em andamento…</p>
          <Progress value={0} max={0} indeterminate />
        </Card>
      )}

      <Card>
        <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">Agendamento</h3>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className={`inline-block h-2.5 w-2.5 rounded-full ${isEnabled ? "bg-emerald-500" : "bg-zinc-300"}`} />
            <span className="text-sm">{isEnabled ? "Ativo" : "Inativo"}</span>
            {status?.cron && <span className="text-xs text-zinc-400 font-mono">{status.cron}</span>}
          </div>
          {!isEnabled ? (
            <div className="flex gap-2 items-center">
              <Input value={cron} onChange={(e) => setCron(e.target.value)} className="w-40 font-mono text-xs" placeholder="cron expr" />
              <Button onClick={() => enable.mutate()} loading={enable.isPending}>Ativar</Button>
            </div>
          ) : (
            <Button variant="danger" onClick={() => disable.mutate()} loading={disable.isPending}>Desativar</Button>
          )}
        </div>
        {status && (
          <p className="mt-2 text-xs text-zinc-500">
            {status.total_updates} atualizações · {status.pending_notifications} notificações pendentes
          </p>
        )}
      </Card>

      {updates && updates.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">Histórico</h3>
          <div className="space-y-4">
            {updates.map((u: LivingUpdate, i: number) => {
              const hasImpact = u.impact_result?.impacto;
              return (
                <div key={i} className={`border rounded-lg p-4 ${hasImpact ? "border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950" : "border-zinc-200 dark:border-zinc-700"}`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-zinc-500">{u.trigger}</span>
                      {u.created_at && <span className="text-xs text-zinc-400">{new Date(u.created_at).toLocaleString("pt-BR")}</span>}
                    </div>
                    {hasImpact && <Badge className="bg-amber-200 text-amber-800">Impacto detectado</Badge>}
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-xs">
                    <div>
                      <span className="text-zinc-500">Novos encontrados:</span> <strong>{u.new_found}</strong>
                    </div>
                    <div>
                      <span className="text-zinc-500">Importados:</span> <strong>{u.new_imported}</strong>
                    </div>
                    <div>
                      <span className="text-zinc-500">Duplicatas:</span> <strong>{u.new_duplicates}</strong>
                    </div>
                  </div>
                  {u.impact_result?.detalhes && u.impact_result.detalhes.length > 0 && (
                    <div className="mt-3 space-y-1">
                      {u.impact_result.detalhes.map((d, j) => {
                        const impType = IMPACT_TYPE[d.tipo as keyof typeof IMPACT_TYPE] ?? { label: d.tipo, color: "text-zinc-500" };
                        return (
                          <div key={j} className="text-xs flex items-start gap-2">
                            <Badge className={`${impType.color} bg-transparent`}>{impType.label}</Badge>
                            <span className="text-zinc-600 dark:text-zinc-400">{d.descricao}</span>
                            {d.antes != null && d.depois != null && (
                              <span className="text-zinc-400">{d.antes.toFixed(3)} → {d.depois.toFixed(3)}</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}
