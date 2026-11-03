"use client";

interface Props {
  value: number;
  max: number;
  indeterminate?: boolean;
  className?: string;
}

export function Progress({ value, max, indeterminate, className = "" }: Props) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className={`h-2 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-700 ${className}`}>
      <div
        className={`h-full rounded-full bg-zinc-800 dark:bg-zinc-200 transition-all duration-300 ${indeterminate ? "animate-pulse w-full" : ""}`}
        style={indeterminate ? undefined : { width: `${pct}%` }}
      />
    </div>
  );
}
