"use client";

import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { reportApi, type ChecklistItem } from "@/lib/api/report";
import { useJobStream } from "@/hooks/useJobStream";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Progress } from "@/components/ui/Progress";
import { APPROVAL_STATUS } from "@/lib/vocab";
import { useState } from "react";

export default function ReportPage() {
  const { reviewId } = useParams() as { reviewId: string };
  const qc = useQueryClient();
  const [jobId, setJobId] = useState<string | null>(null);
  const stream = useJobStream(jobId);

  const { data: report } = useQuery({
    queryKey: ["report", reviewId],
    queryFn: () => reportApi.get(reviewId).catch(() => null),
  });
  const { data: checklist } = useQuery({
    queryKey: ["checklist", reviewId],
    queryFn: () => reportApi.checklist(reviewId).catch(() => null),
  });

  const run = useMutation({
    mutationFn: () => reportApi.run(reviewId),
    onSuccess: (r) => setJobId(r.job_id),
  });

  if (stream.done && jobId) {
    qc.invalidateQueries({ queryKey: ["report", reviewId] });
    qc.invalidateQueries({ queryKey: ["checklist", reviewId] });
    setJobId(null);
  }

  const approve = useMutation({
    mutationFn: () => reportApi.approve(reviewId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["report", reviewId] }),
  });

  const flowSvgUrl = reportApi.flowSvgUrl(reviewId);
  const st = APPROVAL_STATUS[(report?.status ?? "draft") as keyof typeof APPROVAL_STATUS] ?? APPROVAL_STATUS.draft;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">Relatório PRISMA</h2>
        <div className="flex gap-2">
          <Button onClick={() => run.mutate()} loading={run.isPending || (!!jobId && !stream.done)}>
            {jobId && !stream.done ? "Gerando…" : "Gerar relatório"}
          </Button>
          {report && report.status !== "approved" && (
            <Button variant="secondary" onClick={() => approve.mutate()}>Aprovar</Button>
          )}
        </div>
      </div>

      {jobId && !stream.done && (
        <Card>
          <p className="text-xs text-zinc-500 mb-2">Relatório em andamento…</p>
          <Progress value={0} max={0} indeterminate />
        </Card>
      )}

      <Card>
        <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">Diagrama PRISMA 2020</h3>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={flowSvgUrl} alt="PRISMA Flow Diagram" className="max-w-full rounded border border-zinc-200 dark:border-zinc-700" />
      </Card>

      {checklist && (
        <Card>
          <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">
            Checklist PRISMA ({checklist.n_atendidos}/{checklist.itens.length} itens atendidos)
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-700">
                  <th className="text-left py-2 px-2 w-12">#</th>
                  <th className="text-left py-2 px-2">Seção</th>
                  <th className="text-left py-2 px-2">Item</th>
                  <th className="text-center py-2 px-2 w-16">Status</th>
                </tr>
              </thead>
              <tbody>
                {checklist.itens.map((item: ChecklistItem) => (
                  <tr key={item.numero} className="border-b border-zinc-100 dark:border-zinc-800">
                    <td className="py-1 px-2 font-mono">{item.numero}</td>
                    <td className="py-1 px-2 text-zinc-500">{item.secao}</td>
                    <td className="py-1 px-2">{item.titulo}</td>
                    <td className="py-1 px-2 text-center">
                      {item.atendido ? (
                        <span className="text-emerald-500">✓</span>
                      ) : (
                        <span className="text-zinc-300">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {report && report.sections && report.sections.length > 0 && (
        <Card>
          <div className="flex items-center gap-3 mb-4">
            <h3 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400">Manuscrito</h3>
            <Badge className={`${st.bg} ${st.color}`}>{st.label}</Badge>
          </div>
          <div className="space-y-4">
            {report.sections.map((s) => (
              <div key={s.key}>
                <h4 className="text-sm font-semibold mb-1">{s.titulo}</h4>
                <div className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed whitespace-pre-wrap">
                  {s.corpo}
                </div>
                {s.flags && s.flags.length > 0 && (
                  <div className="mt-1 flex gap-1">
                    {s.flags.map((f, i) => <Badge key={i} className="bg-amber-100 text-amber-700 text-[10px]">{f}</Badge>)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card>
        <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">Downloads</h3>
        <div className="flex gap-3">
          <a href={reportApi.downloadMd(reviewId)} className="text-sm text-zinc-600 hover:text-zinc-900 underline">Markdown</a>
          <a href={reportApi.downloadHtml(reviewId)} className="text-sm text-zinc-600 hover:text-zinc-900 underline">HTML</a>
          <a href={reportApi.downloadDocx(reviewId)} className="text-sm text-zinc-600 hover:text-zinc-900 underline">DOCX</a>
          <a href={reportApi.exportZip(reviewId)} className="text-sm text-zinc-600 hover:text-zinc-900 underline">Export ZIP</a>
        </div>
      </Card>
    </div>
  );
}
