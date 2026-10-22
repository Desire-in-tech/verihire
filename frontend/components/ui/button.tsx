import Link from "next/link";
import type { ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";

type ButtonProps = {
  children: ReactNode;
  variant?: ButtonVariant;
  className?: string;
  href?: string;
  type?: "button" | "submit" | "reset";
  onClick?: () => void;
  disabled?: boolean;
};

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-[#31d4c7] text-[#061312] shadow-[0_10px_26px_rgba(49,212,199,0.16)] hover:bg-[#68e2d8]",
  secondary:
    "border border-[#2b3442] bg-[#111821] text-[#edf3f8] hover:bg-[#171f2a]",
  ghost: "bg-transparent text-[#dfe9f8] hover:bg-white/5",
};

export function Button({
  children,
  variant = "primary",
  className = "",
  href,
  type = "button",
  onClick,
  disabled = false,
}: ButtonProps) {
  const sharedClassName = `inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#31d4c7] focus-visible:ring-offset-2 focus-visible:ring-offset-[#080b10] ${variantClasses[variant]} ${className}`;

  if (href) {
    return (
      <Link href={href} className={sharedClassName}>
        {children}
      </Link>
    );
  }

  return (
    <button type={type} className={sharedClassName} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  );
}
