import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";

const productCards = [
  ["○", "Candidate", "Your CV contains more than your qualifications. You shouldn't have to expose your entire history just to prove a requirement."],
  ["▦", "Employer", "Hiring teams need trustworthy signals. But receiving more candidate data doesn't necessarily mean receiving better verification."],
  ["✦", "AI", "AI needs data. Privacy needs boundaries. VeriHire puts those ideas together."],
];

const flowCards = [
  ["01", "Understand", "AI analyzes the role and candidate evidence to determine relevant qualifications."],
  ["02", "Verify", "Candidates create private proof for their relevant skills, experience, and credentials."],
  ["03", "Decide", "Employers evaluate verified facts and AI-backed insights without unnecessary exposure."],
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#070b10] text-[#edf3f8]">
      <nav className="sticky top-0 z-20 border-b border-[#1c2430] bg-[#080b10]/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 md:px-8">
          <Link href="/" className="flex items-center gap-3">
            <div className="relative h-10 w-10 overflow-hidden rounded-xl">
              <Image
                src="https://res.cloudinary.com/f7ko7ayw/image/upload/v1788009964/VeriHire_Logo_BG2_b2ddm0.png"
                alt="VeriHire logo"
                width={40}
                height={40}
                className="object-cover"
              />
            </div>
            <span className="text-lg font-semibold tracking-[-0.04em]">VeriHire</span>
          </Link>

          <div className="hidden items-center gap-8 text-sm text-[#b3c0cf] md:flex">
            <a href="#product" className="transition hover:text-white">Product</a>
            <a href="#how" className="transition hover:text-white">How it works</a>
            <Link href="/dashboard" className="transition hover:text-white">For Candidates</Link>
            <Link href="/employer" className="transition hover:text-white">For Employers</Link>
          </div>

          <div className="flex items-center gap-3">
            <Button href="/login" variant="ghost" className="hidden sm:inline-flex">Sign in</Button>
            <Button href="/signup">Get started</Button>
          </div>
        </div>
      </nav>

      <main>
        <section className="mx-auto max-w-6xl px-4 pb-16 pt-20 md:px-8 md:pt-28">
          <div className="mb-5 inline-flex rounded-full border border-[#244e4b] bg-[#102826] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#85d8cc]">
            Privacy-first hiring verification
          </div>
          <h1 className="max-w-4xl text-5xl font-semibold leading-none tracking-[-0.07em] text-white md:text-7xl">
            Verify more.
            <span className="block bg-gradient-to-r from-[#94e9dd] via-[#cfdafe] to-[#7de5d4] bg-clip-text text-transparent">
              Reveal less.
            </span>
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-[#9aa7b8]">
            AI-powered hiring verification that helps candidates prove relevant qualifications without exposing private information unnecessarily.
          </p>

          <div className="mt-8 flex flex-wrap gap-4">
            <Button href="/signup">Get started</Button>
            <Button href="#how" variant="secondary">See how it works</Button>
          </div>

          <div className="mt-8 flex flex-wrap gap-6 text-sm text-[#9aa7b8]">
            <span>Privacy-first</span>
            <span>AI-powered</span>
            <span>Verifiable</span>
          </div>

          <div className="relative mt-16 overflow-hidden rounded-[28px] border border-[#1d2530] bg-[#0d1218] p-6 md:p-10">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-[#2a3442] bg-[#101821] p-5 text-left">
                <div className="mb-3 text-[#7adcc8]">◎</div>
                <div className="text-sm font-medium text-[#ebf2f8]">Candidate data encrypted</div>
              </div>
              <div className="rounded-2xl border border-[#2a3442] bg-[#101821] p-5 text-left">
                <div className="mb-3 text-[#7adcc8]">✓</div>
                <div className="text-sm font-medium text-[#ebf2f8]">Qualification verified</div>
              </div>
              <div className="rounded-2xl border border-[#2a3442] bg-[#101821] p-5 text-left">
                <div className="mb-3 text-[#7adcc8]">0</div>
                <div className="text-sm font-medium text-[#ebf2f8]">Personal details disclosed</div>
              </div>
            </div>
          </div>
        </section>

        <section id="product" className="mx-auto max-w-6xl px-4 py-16 md:px-8">
          <div className="mb-10">
            <div className="mb-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#85d8cc]">A better signal</div>
            <h2 className="max-w-2xl text-3xl font-semibold tracking-[-0.05em] text-white md:text-5xl">
              Hiring shouldn’t require giving away everything.
            </h2>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {productCards.map(([icon, title, text]) => (
              <div key={title} className="rounded-2xl border border-[#1d2530] bg-[#0f1620] p-6">
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-[#2a3747] bg-[#121d26] text-[#7adcc8]">
                  {icon}
                </div>
                <h3 className="mb-2 text-xl font-semibold text-white">{title}</h3>
                <p className="text-[#9aa7b8]">{text}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="how" className="mx-auto max-w-6xl px-4 py-16 md:px-8">
          <div className="mb-8">
            <div className="mb-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#85d8cc]">How it works</div>
            <h2 className="text-3xl font-semibold tracking-[-0.05em] text-white md:text-5xl">A private path to proof.</h2>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {flowCards.map(([step, title, text]) => (
              <div key={step} className="rounded-2xl border border-[#1d2530] bg-[#0f1620] p-6">
                <div className="mb-3 text-sm font-semibold text-[#7adcc8]">{step}</div>
                <h3 className="mb-2 text-xl font-semibold text-white">{title}</h3>
                <p className="text-[#9aa7b8]">{text}</p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
