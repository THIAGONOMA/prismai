"use client";

import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { synthesisApi, type SynthesisResult } from "@/lib/api/synthesis";
import { useJobStream } from "@/hooks/useJobStream";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Progress } from "@/components/ui/Progress";
import { ForestPlot } from "@/components/prisma/ForestPlot";
import { FunnelPlot } from "@/components/prisma/FunnelPlot";
import { APPROVAL_STATUS } from "@/lib/vocab";
import { useState } from "react";

export default function SynthesisPage() {
  const { reviewId } = useParams() as { reviewId: string };
  const qc = useQueryClient();
  const [jobId, setJobId] = useState<string | null>(null);
  const stream = useJobStream(jobId);

  const { data: syntheses } = useQuery({
    queryKey: ["syntheses", reviewId],
    queryFn: () => synthesisApi.list(reviewId),
  });

  const run = useMutation({
    mutationFn: () => synthesisApi.run(reviewId),
    onSuccess: (r) => setJobId(r.job_id),
  });

  if (stream.done && jobId) {
    qc.invalidateQueries({ queryKey: ["syntheses", reviewId] });
    setJobId(null);
  }

  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const selected = syntheses?.find((s: SynthesisResult) => s.outcome_key === selectedKey);

  const { data: forest } = useQuery({
    queryKey: ["forest", reviewId, selectedKey],
    queryFn: () => selectedKey ? synthesisApi.forest(reviewId, selectedKey) : null,
    enabled: !!selectedKey,
  });
  const { data: funnel } = useQuery({
    queryKey: ["funnel", reviewId, selectedKey],
    queryFn: () => selectedKey ? synthesisApi.funnel(reviewId, selectedKey) : null,
    enabled: !!selectedKey,
  });

  const approve = useMutation({
    mutationFn: (key: string) => synthesisApi.approve(reviewId, key),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["syntheses", reviewId] }),
  });

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">Meta-análise</h2>
        <Button onClick={() => run.mutate()} loading={run.isPending || (!!jobId && !stream.done)}>
          {jobId && !stream.done ? "Sintetizando…" : "Executar síntese"}
        </Button>
      </div>

      {jobId && !stream.done && (
        <Card>
          <p className="text-xs text-zinc-500 mb-2">Síntese em andamento…</p>
          <Progress value={0} max={0} indeterminate />
        </Card>
      )}

      {syntheses && syntheses.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">Desfechos</h3>
          <div className="space-y-2">
            {syntheses.map((s: SynthesisResult) => {
              const st = APPROVAL_STATUS[s.status as keyof typeof APPROVAL_STATUS] ?? APPROVAL_STATUS.draft;
              return (
                <div
                  key={s.outcome_key}
                  className={`flex items-center justify-between border rounded-lg p-3 cursor-pointer transition-colors ${
                    selectedKey === s.outcome_key ? "border-zinc-400 dark:border-zinc-500" : "border-zinc-200 dark:border-zinc-700 hover:border-zinc-300"
                  }`}
                  onClick={() => setSelectedKey(s.outcome_key)}
                >
                  <div>
                    <p className="text-sm font-medium">{s.outcome_key}</p>
                    <p className="text-xs text-zinc-500">
                      {s.k_studies} estudos · {s.measure} · I²={(((s.i2 ?? 0) * 100).toFixed(0))}%
                      {s.pooled_effect != null && ` · efeito pooled: ${s.pooled_effect.toFixed(3)}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={`${st.bg} ${st.color}`}>{st.label}</Badge>
                    {s.status !== "approved" && (
                      <Button
                        variant="ghost"
                        className="text-xs"
                        onClick={(e) => { e.stopPropagation(); approve.mutate(s.outcome_key); }}
                      >
                        Aprovar
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {selected && forest && (
        <Card>
          <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">Forest Plot — {selected.outcome_key}</h3>
          <ForestPlot data={forest} />
        </Card>
      )}

      {selected && funnel && (
        <Card>
          <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">Funnel Plot — {selected.outcome_key}</h3>
          <FunnelPlot data={funnel} />
        </Card>
      )}
    </div>
  );
}
