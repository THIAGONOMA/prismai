"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { reviewsApi, type Review } from "@/lib/api/reviews";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import Link from "next/link";
import { useState } from "react";

export default function Home() {
  const qc = useQueryClient();
  const { data: reviews, isLoading } = useQuery({ queryKey: ["reviews"], queryFn: reviewsApi.list });
  const [newId, setNewId] = useState("");
  const create = useMutation({
    mutationFn: (id: string) => reviewsApi.create(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["reviews"] }); setNewId(""); },
  });

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <header className="mb-10">
        <h1 className="text-2xl font-bold tracking-tight">PrismAI</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Copiloto para revisões sistemáticas — PRISMA 2020
        </p>
      </header>

      <Card className="mb-8">
        <h2 className="text-sm font-semibold mb-3 text-zinc-600 dark:text-zinc-400">Nova revisão</h2>
        <form
          onSubmit={(e) => { e.preventDefault(); if (newId.trim()) create.mutate(newId.trim()); }}
          className="flex gap-3"
        >
          <Input
            placeholder="Identificador da revisão (slug)"
            value={newId}
            onChange={(e) => setNewId(e.target.value)}
          />
          <Button type="submit" loading={create.isPending} disabled={!newId.trim()}>
            Criar
          </Button>
        </form>
        {create.error && <p className="mt-2 text-xs text-red-600">{(create.error as Error).message}</p>}
      </Card>

      <section>
        <h2 className="text-sm font-semibold mb-4 text-zinc-600 dark:text-zinc-400">Revisões</h2>
        {isLoading && <p className="text-sm text-zinc-400">Carregando…</p>}
        {reviews && reviews.length === 0 && <p className="text-sm text-zinc-400">Nenhuma revisão ainda.</p>}
        <div className="grid gap-3">
          {reviews?.map((r: Review) => (
            <Link key={r.id} href={`/reviews/${r.id}`}>
              <Card className="hover:border-zinc-400 dark:hover:border-zinc-600 transition-colors cursor-pointer">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{r.id}</p>
                    {r.created_at && <p className="text-xs text-zinc-400">{new Date(r.created_at).toLocaleDateString("pt-BR")}</p>}
                  </div>
                  {r.living_enabled && (
                    <span className="text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300 px-2 py-0.5 rounded-full">
                      Living
                    </span>
                  )}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
