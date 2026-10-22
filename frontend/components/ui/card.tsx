import type { ReactNode } from "react";

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-2xl border border-[#1c2430] bg-[#0f1620]/95 p-5 shadow-[0_20px_50px_rgba(0,0,0,0.16)] ${className}`}>
      {children}
    </div>
  );
}
