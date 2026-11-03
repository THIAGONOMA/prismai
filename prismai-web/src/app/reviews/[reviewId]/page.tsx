"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { reviewsApi } from "@/lib/api/reviews";
import { useFlow } from "@/hooks/useFlow";
import { Card } from "@/components/ui/Card";
import { PrismaFunnel } from "@/components/prisma/PrismaFunnel";
import Link from "next/link";

export default function ReviewDashboard() {
  const { reviewId } = useParams() as { reviewId: string };
  const { data: review } = useQuery({ queryKey: ["review", reviewId], queryFn: () => reviewsApi.get(reviewId) });
  const { flow } = useFlow(reviewId);

  const phases = [
    { label: "1. Protocolo", href: "protocol", done: false },
    { label: "2. Busca", href: "protocol", done: false },
    { label: "3. Triagem", href: "screening", count: flow?.registros_triados },
    { label: "4. Full-text", href: "fulltext", count: flow?.fulltext_buscados },
    { label: "5. Extração", href: "extraction", count: flow?.estudos_incluidos },
    { label: "6. Síntese", href: "synthesis" },
    { label: "7. GRADE", href: "grade" },
    { label: "8. Relatório", href: "report" },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-bold">{review?.id ?? reviewId}</h1>
        <p className="text-sm text-zinc-500 mt-1">
          {review?.created_at ? `Criada em ${new Date(review.created_at).toLocaleDateString("pt-BR")}` : ""}
        </p>
      </div>

      <Card>
        <h2 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 mb-3">Funil PRISMA</h2>
        <PrismaFunnel flow={flow} />
      </Card>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {phases.map((p) => (
          <Link key={p.label} href={`/reviews/${reviewId}/${p.href}`}>
            <Card className="hover:border-zinc-400 dark:hover:border-zinc-600 transition-colors cursor-pointer text-center">
              <p className="text-xs font-medium text-zinc-500">{p.label}</p>
              {p.count !== undefined && (
                <p className="text-2xl font-bold tabular-nums mt-1">{p.count.toLocaleString("pt-BR")}</p>
              )}
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
