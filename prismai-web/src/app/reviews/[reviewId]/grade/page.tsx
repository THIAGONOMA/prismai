"use client";

import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { gradeApi, type GradeAssessment, type SofEntry } from "@/lib/api/grade";
import { useJobStream } from "@/hooks/useJobStream";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Progress } from "@/components/ui/Progress";
import { GRADE_CERTAINTY, GRADE_DOMAIN, GRADE_RATING, APPROVAL_STATUS } from "@/lib/vocab";
import { useState } from "react";

export default function GradePage() {
  const { reviewId } = useParams() as { reviewId: string };
  const qc = useQueryClient();
  const [jobId, setJobId] = useState<string | null>(null);
  const stream = useJobStream(jobId);

  const { data: assessments } = useQuery({
    queryKey: ["grade", reviewId],
    queryFn: () => gradeApi.list(reviewId),
  });
  const { data: sof } = useQuery({
    queryKey: ["sof", reviewId],
    queryFn: () => gradeApi.sof(reviewId).catch(() => null),
  });

  const run = useMutation({
    mutationFn: () => gradeApi.run(reviewId),
    onSuccess: (r) => setJobId(r.job_id),
  });

  if (stream.done && jobId) {
    qc.invalidateQueries({ queryKey: ["grade", reviewId] });
    qc.invalidateQueries({ queryKey: ["sof", reviewId] });
    setJobId(null);
  }

  const approve = useMutation({
    mutationFn: (key: string) => gradeApi.approve(reviewId, key),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["grade", reviewId] }),
  });

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">GRADE</h2>
        <Button onClick={() => run.mutate()} loading={run.isPending || (!!jobId && !stream.done)}>
          {jobId && !stream.done ? "Avaliando…" : "Avaliar GRADE"}
        </Button>
      </div>

      {jobId && !stream.done && (
        <Card>
          <p className="text-xs text-zinc-500 mb-2">GRADE em andamento…</p>
          <Progress value={0} max={0} indeterminate />
        </Card>
      )}

      {assessments && assessments.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">Avaliações</h3>
          <div className="space-y-4">
            {assessments.map((a: GradeAssessment) => {
              const cert = GRADE_CERTAINTY[a.final_certainty as keyof typeof GRADE_CERTAINTY] ?? GRADE_CERTAINTY.low;
              const st = APPROVAL_STATUS[a.status as keyof typeof APPROVAL_STATUS] ?? APPROVAL_STATUS.draft;
              return (
                <div key={a.outcome_key} className="border rounded-lg p-4 border-zinc-200 dark:border-zinc-700">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <span className="font-medium text-sm">{a.outcome_key}</span>
                      <Badge className={`${cert.bg} ${cert.color}`}>{cert.icon} {cert.label}</Badge>
                      <Badge className={`${st.bg} ${st.color}`}>{st.label}</Badge>
                    </div>
                    {a.status !== "approved" && (
                      <Button variant="ghost" className="text-xs" onClick={() => approve.mutate(a.outcome_key)}>
                        Aprovar
                      </Button>
                    )}
                  </div>
                  <table className="min-w-full text-xs">
                    <thead>
                      <tr className="border-b border-zinc-200 dark:border-zinc-700">
                        <th className="text-left py-1 px-2">Domínio</th>
                        <th className="text-center py-1 px-2">Rating</th>
                        <th className="text-left py-1 px-2">Justificativa</th>
                      </tr>
                    </thead>
                    <tbody>
                      {a.domains.map((d) => {
                        const domLabel = GRADE_DOMAIN[d.domain as keyof typeof GRADE_DOMAIN] ?? d.domain;
                        const rat = GRADE_RATING[d.rating] ?? { label: String(d.rating), color: "text-zinc-500" };
                        return (
                          <tr key={d.domain} className="border-b border-zinc-100 dark:border-zinc-800">
                            <td className="py-1 px-2">{domLabel}</td>
                            <td className={`py-1 px-2 text-center font-semibold ${rat.color}`}>{rat.label}</td>
                            <td className="py-1 px-2 text-zinc-500">{d.justificativa}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {sof && sof.entries && sof.entries.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">Summary of Findings</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-700">
                  <th className="text-left py-2 px-2">Desfecho</th>
                  <th className="text-center py-2 px-2">k</th>
                  <th className="text-center py-2 px-2">N</th>
                  <th className="text-center py-2 px-2">Efeito [IC 95%]</th>
                  <th className="text-center py-2 px-2">Certeza</th>
                </tr>
              </thead>
              <tbody>
                {sof.entries.map((e: SofEntry) => {
                  const cert = GRADE_CERTAINTY[e.certainty as keyof typeof GRADE_CERTAINTY] ?? GRADE_CERTAINTY.low;
                  return (
                    <tr key={e.outcome_key} className="border-b border-zinc-100 dark:border-zinc-800">
                      <td className="py-1.5 px-2 font-medium">{e.outcome_key}</td>
                      <td className="py-1.5 px-2 text-center tabular-nums">{e.k_studies}</td>
                      <td className="py-1.5 px-2 text-center tabular-nums">{e.n_participants ?? "—"}</td>
                      <td className="py-1.5 px-2 text-center font-mono">
                        {e.pooled_effect?.toFixed(2)} [{e.ci_low?.toFixed(2)}, {e.ci_high?.toFixed(2)}]
                      </td>
                      <td className="py-1.5 px-2 text-center">
                        <Badge className={`${cert.bg} ${cert.color}`}>{cert.icon}</Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
