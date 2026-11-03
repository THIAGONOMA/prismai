"use client";

import { useParams, usePathname } from "next/navigation";
import Link from "next/link";
import { useFlow } from "@/hooks/useFlow";
import { PrismaFunnel } from "@/components/prisma/PrismaFunnel";

const NAV = [
  { href: "", label: "Painel" },
  { href: "/protocol", label: "Protocolo" },
  { href: "/screening", label: "Triagem" },
  { href: "/fulltext", label: "Full-text" },
  { href: "/extraction", label: "Extração" },
  { href: "/synthesis", label: "Síntese" },
  { href: "/grade", label: "GRADE" },
  { href: "/report", label: "Relatório" },
  { href: "/living", label: "Living" },
];

export default function ReviewLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const reviewId = params.reviewId as string;
  const pathname = usePathname();
  const { flow } = useFlow(reviewId);

  const basePath = `/reviews/${reviewId}`;

  return (
    <div className="flex flex-col min-h-screen">
      <header className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 sticky top-0 z-20">
        <div className="mx-auto max-w-7xl px-6 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Link href="/" className="text-sm font-bold text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors">
                PrismAI
              </Link>
              <span className="text-zinc-300 dark:text-zinc-600">/</span>
              <span className="font-semibold text-sm">{reviewId}</span>
            </div>
          </div>
          <div className="mt-3">
            <PrismaFunnel flow={flow} compact />
          </div>
          <nav className="mt-3 flex gap-1 overflow-x-auto pb-1 -mb-px">
            {NAV.map((item) => {
              const full = basePath + item.href;
              const active = item.href === "" ? pathname === basePath : pathname.startsWith(full);
              return (
                <Link
                  key={item.href}
                  href={full}
                  className={`whitespace-nowrap px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    active
                      ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                      : "text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 dark:hover:text-zinc-100 dark:hover:bg-zinc-800"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>
      <main className="flex-1 mx-auto max-w-7xl w-full px-6 py-6">
        {children}
      </main>
    </div>
  );
}
