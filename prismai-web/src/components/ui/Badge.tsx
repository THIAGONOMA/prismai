"use client";

interface Props {
  children: React.ReactNode;
  className?: string;
}

export function Badge({ children, className = "" }: Props) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}>
      {children}
    </span>
  );
}
