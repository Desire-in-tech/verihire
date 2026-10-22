"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { writeEmployerToken } from "@/lib/session";

const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

type AuthMode = "login" | "signup";

function detailFrom(payload: unknown, status: number): string {
  if (payload && typeof payload === "object" && typeof (payload as { detail?: unknown }).detail === "string") {
    return (payload as { detail: string }).detail;
  }
  return `Request failed (${status}).`;
}

export function AuthForm({ mode }: { mode: AuthMode }) {
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (password.length < 12) {
      setError("Use a password of at least 12 characters.");
      return;
    }
    setPending(true);
    setError("");
    try {
      const body =
        mode === "signup"
          ? { email, password, display_name: displayName }
          : { email, password };
      const response = await fetch(`${apiUrl}/api/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(detailFrom(payload, response.status));
      }
      const token = payload && typeof payload === "object" ? (payload as { token?: unknown }).token : null;
      if (typeof token !== "string" || !token) {
        throw new Error("The server did not return a session.");
      }
      writeEmployerToken(token);
      router.push("/employer");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "The request failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
      {mode === "signup" ? (
        <div>
          <label className="mb-2 block text-sm text-[#dae5f4]" htmlFor="display-name">
            Employer name
          </label>
          <input
            id="display-name"
            type="text"
            required
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            placeholder="Example Hiring"
            className="w-full rounded-xl border border-[#2a3440] bg-[#0b1118] px-4 py-3 text-[#edf3f8] placeholder:text-[#77869c] outline-none ring-0 transition focus:border-[#31d4c7]"
          />
        </div>
      ) : null}

      <div>
        <label className="mb-2 block text-sm text-[#dae5f4]" htmlFor="email">
          Email address
        </label>
        <input
          id="email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@example.com"
          className="w-full rounded-xl border border-[#2a3440] bg-[#0b1118] px-4 py-3 text-[#edf3f8] placeholder:text-[#77869c] outline-none ring-0 transition focus:border-[#31d4c7]"
        />
      </div>

      <div>
        <label className="mb-2 block text-sm text-[#dae5f4]" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          type="password"
          required
          minLength={12}
          autoComplete={mode === "signup" ? "new-password" : "current-password"}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="At least 12 characters"
          className="w-full rounded-xl border border-[#2a3440] bg-[#0b1118] px-4 py-3 text-[#edf3f8] placeholder:text-[#77869c] outline-none ring-0 transition focus:border-[#31d4c7]"
        />
      </div>

      {error ? <p className="text-sm text-[#ff9b9b]">{error}</p> : null}
      <Button type="submit" disabled={pending} className="w-full disabled:cursor-not-allowed disabled:opacity-60">
        {pending ? "Working…" : mode === "signup" ? "Create employer account" : "Sign in"}
      </Button>
    </form>
  );
}
