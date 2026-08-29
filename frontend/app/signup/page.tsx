import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function SignupPage() {
  return (
    <div className="flex min-h-screen bg-[#070b10] text-[#edf3f8]">
      <div className="hidden w-1/2 flex-col justify-between border-r border-[#1c2430] bg-[#0d1218] p-10 lg:flex">
        <div className="flex items-center gap-3">
          <div className="relative h-12 w-12 overflow-hidden rounded-xl">
            <Image
              src="https://res.cloudinary.com/f7ko7ayw/image/upload/v1788009964/VeriHire_Logo_BG2_b2ddm0.png"
              alt="VeriHire logo"
              width={48}
              height={48}
              className="object-cover"
            />
          </div>
          <div className="text-2xl font-semibold tracking-[-0.05em]">VeriHire</div>
        </div>

        <div>
          <div className="mb-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#85d8cc]">Private by design</div>
          <h1 className="max-w-md text-4xl font-semibold tracking-[-0.06em] text-white">
            Trust the proof.
            <span className="mt-2 block bg-gradient-to-r from-[#94e9dd] via-[#cfdafe] to-[#7de5d4] bg-clip-text text-transparent">
              Not the paperwork.
            </span>
          </h1>
          <p className="mt-4 max-w-md text-[#9aa7b8]">
            A better way to connect qualified people with trustworthy employers while keeping private information protected.
          </p>
        </div>

        <div className="text-sm text-[#9aa7b8]">© 2026 VeriHire</div>
      </div>

      <div className="flex flex-1 items-center justify-center p-6">
        <div className="w-full max-w-md rounded-[26px] border border-[#1c2430] bg-[#0f1620] p-8 shadow-[0_20px_60px_rgba(0,0,0,0.22)]">
          <Link href="/" className="mb-6 inline-flex text-sm text-[#9aa7b8] hover:text-white">← Back home</Link>
          <h2 className="text-3xl font-semibold tracking-[-0.05em] text-white">Create your account</h2>
          <p className="mt-2 text-[#9aa7b8]">Start proving your qualifications privately.</p>

          <form className="mt-8 space-y-5">
            <div>
              <label className="mb-2 block text-sm text-[#dae5f4]">Full name</label>
              <input
                type="text"
                placeholder="Trina Smith"
                className="w-full rounded-xl border border-[#2a3440] bg-[#0b1118] px-4 py-3 text-[#edf3f8] placeholder:text-[#77869c] outline-none ring-0 transition focus:border-[#31d4c7]"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm text-[#dae5f4]">Email address</label>
              <input
                type="email"
                placeholder="you@example.com"
                className="w-full rounded-xl border border-[#2a3440] bg-[#0b1118] px-4 py-3 text-[#edf3f8] placeholder:text-[#77869c] outline-none ring-0 transition focus:border-[#31d4c7]"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm text-[#dae5f4]">Password</label>
              <input
                type="password"
                placeholder="••••••••"
                className="w-full rounded-xl border border-[#2a3440] bg-[#0b1118] px-4 py-3 text-[#edf3f8] placeholder:text-[#77869c] outline-none ring-0 transition focus:border-[#31d4c7]"
              />
            </div>

            <Button href="/dashboard" className="w-full">Create account</Button>
          </form>

          <div className="mt-6 text-center text-sm text-[#9aa7b8]">
            Already have an account? <Link href="/login" className="text-[#8adbd5]">Sign in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
