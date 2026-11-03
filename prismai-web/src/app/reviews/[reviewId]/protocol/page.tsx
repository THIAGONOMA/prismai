"use client";

import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { reviewsApi, type Protocol } from "@/lib/api/reviews";
import { searchApi } from "@/lib/api/search";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useState, useRef } from "react";

const EMPTY_PROTOCOL: Protocol = { pergunta: "", P: "", I: "", C: "", O: "", desenho: "", inclusao: [""], exclusao: [""] };

export default function ProtocolPage() {
  const { reviewId } = useParams() as { reviewId: string };
  const qc = useQueryClient();
  const { data: protocol, isLoading } = useQuery({
    queryKey: ["protocol", reviewId],
    queryFn: () => reviewsApi.getProtocol(reviewId).catch(() => null),
  });
  const { data: runs } = useQuery({
    queryKey: ["import-runs", reviewId],
    queryFn: () => searchApi.importRuns(reviewId),
  });

  const [form, setForm] = useState<Protocol>(EMPTY_PROTOCOL);
  const [initialized, setInitialized] = useState(false);
  if (protocol && !initialized) { setForm(protocol); setInitialized(true); }

  const save = useMutation({
    mutationFn: () => reviewsApi.setProtocol(reviewId, form),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["protocol", reviewId] }),
  });

  const [searchQuery, setSearchQuery] = useState("");
  const [searchSource, setSearchSource] = useState("openalex");
  const search = useMutation({
    mutationFn: () => searchApi.run(reviewId, searchQuery, searchSource),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["import-runs", reviewId] }),
  });

  const fileRef = useRef<HTMLInputElement>(null);
  const importFile = useMutation({
    mutationFn: (file: File) => searchApi.importFile(reviewId, file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["import-runs", reviewId] }),
  });

  function updateField(field: keyof Protocol, value: string | string[]) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function updateList(field: "inclusao" | "exclusao", idx: number, val: string) {
    setForm((prev) => {
      const arr = [...prev[field]];
      arr[idx] = val;
      return { ...prev, [field]: arr };
    });
  }

  if (isLoading) return <p className="text-sm text-zinc-400">Carregando…</p>;

  return (
    <div className="space-y-8 max-w-3xl">
      <Card>
        <h2 className="text-sm font-semibold mb-4 text-zinc-600 dark:text-zinc-400">Protocolo PICO</h2>
        <div className="space-y-3">
          <label className="block">
            <span className="text-xs font-medium text-zinc-500">Pergunta de pesquisa</span>
            <Input value={form.pergunta} onChange={(e) => updateField("pergunta", e.target.value)} />
          </label>
          <div className="grid grid-cols-2 gap-3">
            {(["P", "I", "C", "O"] as const).map((k) => (
              <label key={k} className="block">
                <span className="text-xs font-medium text-zinc-500">{k}</span>
                <Input value={form[k]} onChange={(e) => updateField(k, e.target.value)} />
              </label>
            ))}
          </div>
          <label className="block">
            <span className="text-xs font-medium text-zinc-500">Desenho do estudo</span>
            <Input value={form.desenho} onChange={(e) => updateField("desenho", e.target.value)} />
          </label>
          <div className="grid grid-cols-2 gap-3">
            {(["inclusao", "exclusao"] as const).map((field) => (
              <div key={field}>
                <span className="text-xs font-medium text-zinc-500">{field === "inclusao" ? "Critérios de inclusão" : "Critérios de exclusão"}</span>
                {form[field].map((v, i) => (
                  <Input key={i} value={v} onChange={(e) => updateList(field, i, e.target.value)} className="mt-1" />
                ))}
                <button
                  type="button"
                  onClick={() => setForm((p) => ({ ...p, [field]: [...p[field], ""] }))}
                  className="mt-1 text-xs text-zinc-500 hover:text-zinc-900"
                >
                  + Adicionar
                </button>
              </div>
            ))}
          </div>
          <Button onClick={() => save.mutate()} loading={save.isPending}>Salvar protocolo</Button>
        </div>
      </Card>

      <Card>
        <h2 className="text-sm font-semibold mb-4 text-zinc-600 dark:text-zinc-400">Busca em bases</h2>
        <div className="flex gap-3 items-end">
          <label className="flex-1">
            <span className="text-xs font-medium text-zinc-500">Query</span>
            <Input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="systematic review AND ..." />
          </label>
          <label>
            <span className="text-xs font-medium text-zinc-500">Fonte</span>
            <select
              value={searchSource}
              onChange={(e) => setSearchSource(e.target.value)}
              className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
            >
              <option value="openalex">OpenAlex</option>
              <option value="crossref">Crossref</option>
            </select>
          </label>
          <Button onClick={() => search.mutate()} loading={search.isPending} disabled={!searchQuery.trim()}>
            Buscar
          </Button>
        </div>
        {search.data && (
          <p className="mt-2 text-xs text-zinc-500">
            {search.data.total_found} encontrados, {search.data.imported} importados, {search.data.duplicates} duplicatas
          </p>
        )}
      </Card>

      <Card>
        <h2 className="text-sm font-semibold mb-4 text-zinc-600 dark:text-zinc-400">Importar arquivo</h2>
        <div className="flex gap-3 items-center">
          <input ref={fileRef} type="file" accept=".csv,.ris,.bib" className="text-sm" />
          <Button
            variant="secondary"
            onClick={() => { if (fileRef.current?.files?.[0]) importFile.mutate(fileRef.current.files[0]); }}
            loading={importFile.isPending}
          >
            Importar
          </Button>
        </div>
        {importFile.data && (
          <p className="mt-2 text-xs text-zinc-500">
            {importFile.data.imported} importados, {importFile.data.duplicates} duplicatas ({importFile.data.format})
          </p>
        )}
      </Card>

      {runs && runs.length > 0 && (
        <Card>
          <h2 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">Histórico de importações</h2>
          <div className="space-y-2">
            {runs.map((r, i) => (
              <div key={i} className="flex justify-between text-xs border-b border-zinc-100 dark:border-zinc-800 pb-2">
                <span className="font-mono">{r.source}</span>
                <span>{r.imported} importados / {r.duplicates} duplicatas / {r.total_found} encontrados</span>
                {r.created_at && <span className="text-zinc-400">{new Date(r.created_at).toLocaleString("pt-BR")}</span>}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
