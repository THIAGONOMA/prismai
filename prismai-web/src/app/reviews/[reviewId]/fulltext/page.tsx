"use client";

import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { documentsApi, type Document, type EligibilityDecision } from "@/lib/api/documents";
import { useJobStream } from "@/hooks/useJobStream";
import { useFlow } from "@/hooks/useFlow";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Progress } from "@/components/ui/Progress";
import { DOC_STATUS, lookupVocab } from "@/lib/vocab";
import { useState, useRef } from "react";

export default function FulltextPage() {
  const { reviewId } = useParams() as { reviewId: string };
  const qc = useQueryClient();
  const { invalidate } = useFlow(reviewId);
  const [fetchJobId, setFetchJobId] = useState<string | null>(null);
  const [eligJobId, setEligJobId] = useState<string | null>(null);
  const fetchStream = useJobStream(fetchJobId);
  const eligStream = useJobStream(eligJobId);

  const { data: docs } = useQuery({
    queryKey: ["documents", reviewId],
    queryFn: () => documentsApi.list(reviewId),
    refetchInterval: (fetchJobId && !fetchStream.done) ? 5000 : false,
  });
  const { data: eligDecisions } = useQuery({
    queryKey: ["eligibility", reviewId],
    queryFn: () => documentsApi.eligibilityDecisions(reviewId),
  });

  const fetchFt = useMutation({
    mutationFn: () => documentsApi.fetchFulltext(reviewId),
    onSuccess: (r) => setFetchJobId(r.job_id),
  });
  const runElig = useMutation({
    mutationFn: () => documentsApi.runEligibility(reviewId),
    onSuccess: (r) => setEligJobId(r.job_id),
  });

  if (fetchStream.done && fetchJobId) {
    qc.invalidateQueries({ queryKey: ["documents", reviewId] });
    invalidate();
    setFetchJobId(null);
  }
  if (eligStream.done && eligJobId) {
    qc.invalidateQueries({ queryKey: ["eligibility", reviewId] });
    invalidate();
    setEligJobId(null);
  }

  const [uploadRecordId, setUploadRecordId] = useState("");
  const uploadRef = useRef<HTMLInputElement>(null);
  const upload = useMutation({
    mutationFn: (file: File) => documentsApi.upload(reviewId, uploadRecordId, file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents", reviewId] }),
  });

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">Full-text & Elegibilidade</h2>
        <div className="flex gap-2">
          <Button onClick={() => fetchFt.mutate()} loading={fetchFt.isPending || (!!fetchJobId && !fetchStream.done)}>
            Buscar full-text
          </Button>
          <Button variant="secondary" onClick={() => runElig.mutate()} loading={runElig.isPending || (!!eligJobId && !eligStream.done)}>
            Avaliar elegibilidade
          </Button>
        </div>
      </div>

      {fetchJobId && !fetchStream.done && (
        <Card>
          <p className="text-xs text-zinc-500 mb-2">Buscando full-text: {fetchStream.progress}/{fetchStream.total}</p>
          <Progress value={fetchStream.progress} max={fetchStream.total} />
        </Card>
      )}
      {eligJobId && !eligStream.done && (
        <Card>
          <p className="text-xs text-zinc-500 mb-2">Elegibilidade: {eligStream.progress}/{eligStream.total}</p>
          <Progress value={eligStream.progress} max={eligStream.total} />
        </Card>
      )}

      <Card>
        <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">Upload manual</h3>
        <div className="flex gap-3 items-center">
          <input
            placeholder="record_id"
            value={uploadRecordId}
            onChange={(e) => setUploadRecordId(e.target.value)}
            className="rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-800 w-48"
          />
          <input ref={uploadRef} type="file" accept=".pdf" className="text-sm" />
          <Button
            variant="secondary"
            onClick={() => { if (uploadRef.current?.files?.[0]) upload.mutate(uploadRef.current.files[0]); }}
            loading={upload.isPending}
          >
            Upload
          </Button>
        </div>
      </Card>

      <Card>
        <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">Documentos ({docs?.length ?? 0})</h3>
        {docs && docs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-700">
                  <th className="text-left py-2 px-2">Record ID</th>
                  <th className="text-left py-2 px-2">Status</th>
                  <th className="text-left py-2 px-2">Fonte</th>
                  <th className="text-right py-2 px-2">Páginas</th>
                  <th className="text-right py-2 px-2">OCR</th>
                </tr>
              </thead>
              <tbody>
                {docs.map((d: Document) => {
                  const st = lookupVocab(DOC_STATUS, d.status, { label: d.status, color: "text-zinc-500" });
                  return (
                    <tr key={d.record_id} className="border-b border-zinc-100 dark:border-zinc-800">
                      <td className="py-1.5 px-2 font-mono">{d.record_id.slice(0, 16)}</td>
                      <td className="py-1.5 px-2">
                        <Badge className={`${(st as { color: string }).color}`}>{(st as { label: string }).label}</Badge>
                      </td>
                      <td className="py-1.5 px-2 text-zinc-500">{d.fetch_source ?? "—"}</td>
                      <td className="py-1.5 px-2 text-right tabular-nums">{d.n_pages || "—"}</td>
                      <td className="py-1.5 px-2 text-right tabular-nums">{d.ocr_confidence != null ? d.ocr_confidence.toFixed(2) : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-zinc-400">Nenhum documento.</p>
        )}
      </Card>

      {eligDecisions && eligDecisions.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">Decisões de elegibilidade</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-700">
                  <th className="text-left py-2 px-2">Documento</th>
                  <th className="text-left py-2 px-2">Decisão</th>
                  <th className="text-left py-2 px-2">Motivo exclusão</th>
                  <th className="text-left py-2 px-2">Confiança</th>
                </tr>
              </thead>
              <tbody>
                {eligDecisions.map((d: EligibilityDecision, i: number) => (
                  <tr key={i} className="border-b border-zinc-100 dark:border-zinc-800">
                    <td className="py-1.5 px-2 font-mono">{d.document_id?.slice(0, 16) ?? "—"}</td>
                    <td className="py-1.5 px-2">{d.decision}</td>
                    <td className="py-1.5 px-2 text-zinc-500">{d.exclusion_reason ?? "—"}</td>
                    <td className="py-1.5 px-2">{d.confidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
