import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";

const candidateLinks = [
  { href: "/dashboard", label: "Overview" },
  { href: "/jobs", label: "Jobs" },
  { href: "/applications", label: "Applications" },
  { href: "/verify", label: "Verifications" },
  { href: "/profile", label: "Profile" },
  { href: "/settings", label: "Settings" },
];

const employerLinks = [
  { href: "/employer", label: "Overview" },
  { href: "/employer/jobs", label: "Jobs" },
  { href: "/employer/candidates", label: "Candidates" },
  { href: "/settings", label: "Settings" },
];

export function AppShell({
  children,
  active,
  mode = "candidate",
  title,
  subtitle,
}: {
  children: ReactNode;
  active?: string;
  mode?: "candidate" | "employer";
  title?: string;
  subtitle?: string;
}) {
  const links = mode === "candidate" ? candidateLinks : employerLinks;

  return (
    <div className="min-h-screen bg-[#080b10] text-[#edf3f8]">
      <div className="flex min-h-screen">
        <aside className="hidden w-[250px] shrink-0 border-r border-[#1c2430] bg-[#0a0d12] p-5 lg:block">
          <div className="mb-8 flex items-center gap-3">
            <div className="relative h-10 w-10 overflow-hidden rounded-xl">
              <Image
                src="https://res.cloudinary.com/f7ko7ayw/image/upload/v1788009964/VeriHire_Logo_BG2_b2ddm0.png"
                alt="VeriHire logo"
                width={40}
                height={40}
                className="object-cover"
              />
            </div>
            <div>
              <div className="text-lg font-semibold tracking-[-0.04em]">VeriHire</div>
            </div>
          </div>

          <div className="space-y-2">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center rounded-xl px-3 py-2.5 text-sm transition-colors ${
                  active === link.href
                    ? "border border-[#2d4341] bg-[#101d1d] text-white"
                    : "text-[#9aa7b8] hover:bg-white/5 hover:text-white"
                }`}
              >
                <span className="mr-2 text-[#67d5cb]">•</span>
                {link.label}
              </Link>
            ))}
          </div>

          <div className="mt-8 rounded-2xl border border-[#224c47] bg-[#0f1d1d] p-4">
            <div className="mb-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-[#8fe0ca]">
              Privacy protected
            </div>
            <p className="text-sm text-[#dce8f3]">Only verified qualifications are shared with employers.</p>
          </div>
        </aside>

        <main className="flex-1">
          <header className="border-b border-[#1c2430] bg-[#0b0e13]/90 px-4 py-4 backdrop-blur lg:px-8">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 lg:hidden">
                <div className="relative h-9 w-9 overflow-hidden rounded-lg">
                  <Image
                    src="https://res.cloudinary.com/f7ko7ayw/image/upload/v1788009964/VeriHire_Logo_BG2_b2ddm0.png"
                    alt="VeriHire logo"
                    width={36}
                    height={36}
                    className="object-cover"
                  />
                </div>
              </div>
              <div>
                {title ? <h1 className="text-2xl font-semibold tracking-[-0.04em]">{title}</h1> : null}
                {subtitle ? <p className="text-sm text-[#9aa7b8]">{subtitle}</p> : null}
              </div>
              <div className="flex items-center gap-3">
                <button className="rounded-full border border-[#2a3440] bg-[#121922] px-3 py-2 text-xs font-medium text-[#dfeaf8]">
                  Alerts
                </button>
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#26313a] text-sm font-semibold text-[#dfeaf8]">
                  TR
                </div>
              </div>
            </div>
          </header>

          <div className="px-4 py-6 lg:px-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
