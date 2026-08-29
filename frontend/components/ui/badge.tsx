type BadgeProps = {
  children: React.ReactNode;
  tone?: "green" | "purple" | "cyan" | "amber" | "slate";
  className?: string;
};

const toneClasses: Record<NonNullable<BadgeProps["tone"]>, string> = {
  green: "border border-[#1e4a43] bg-[#102b27] text-[#8fe0ca]",
  purple: "border border-[#3d3b5d] bg-[#201b2e] text-[#c6b7ff]",
  cyan: "border border-[#224f5e] bg-[#0d2330] text-[#9fe8f6]",
  amber: "border border-[#4d3f23] bg-[#291f10] text-[#f7d5a0]",
  slate: "border border-[#2a3440] bg-[#121821] text-[#d2d9e6]",
};

export function Badge({ children, tone = "slate", className = "" }: BadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] ${toneClasses[tone]} ${className}`}>
      {children}
    </span>
  );
}
