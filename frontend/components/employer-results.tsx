"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  countVerifiedEligible,
  parseEmployerResults,
  type EmployerResultRow,
} from "@/lib/employer-results";
import { verificationIsPositive, verificationLabel } from "@/lib/verification-label";

const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

function badgeTone(row: EmployerResultRow): "green" | "amber" | "cyan" | "slate" {
  const status = row.proof.proof_data?.verification_status;
  if (verificationIsPositive(row.proof)) {
    return "green";
  }
  if (status === "failed") {
    return "amber";
  }
  if (status === "unknown") {
    return "cyan";
  }
  return "slate";
}

export function EmployerResults() {
  const [rows, setRows] = useState<EmployerResultRow[] | null>(null);
  const [jobCount, setJobCount] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [resultsResponse, jobsResponse] = await Promise.all([
          fetch(`${apiUrl}/api/employer/results`),
          fetch(`${apiUrl}/api/employer/jobs`),
        ]);
        const resultsPayload = await resultsResponse.json().catch(() => null);
        const jobsPayload = await jobsResponse.json().catch(() => null);
        if (!resultsResponse.ok) {
          const detail =
            resultsPayload &&
            typeof resultsPayload === "object" &&
            typeof (resultsPayload as { detail?: unknown }).detail === "string"
              ? (resultsPayload as { detail: string }).detail
              : `Employer results request failed (${resultsResponse.status}).`;
          throw new Error(detail);
        }
        const parsed = parseEmployerResults(resultsPayload);
        const listedJobs =
          jobsPayload && typeof jobsPayload === "object" && Array.isArray((jobsPayload as { jobs?: unknown }).jobs)
            ? (jobsPayload as { jobs: unknown[] }).jobs.length
            : null;
        if (!cancelled) {
          setRows(parsed);
          setJobCount(resultsResponse.ok && jobsResponse.ok ? listedJobs : null);
          setError("");
        }
      } catch (loadError) {
        if (!cancelled) {
          setRows(null);
          setJobCount(null);
          setError(loadError instanceof Error ? loadError.message : "Employer results could not be loaded.");
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const verified = rows ? countVerifiedEligible(rows) : null;
  const unknown = rows
    ? rows.filter((row) => row.proof.proof_data?.verification_status === "unknown").length
    : null;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        {[
          ["Active jobs", jobCount === null ? "—" : String(jobCount)],
          ["Recorded results", rows === null ? "—" : String(rows.length)],
          ["Verified eligible", verified === null ? "—" : String(verified)],
          ["Outcome unknown", unknown === null ? "—" : String(unknown)],
        ].map(([label, value]) => (
          <Card key={label} className="p-4">
            <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#9aa7b8]">{label}</div>
            <div className="mt-3 text-3xl font-semibold tracking-[-0.05em] text-white">{value}</div>
          </Card>
        ))}
      </div>

      <h2 className="text-2xl font-semibold tracking-[-0.05em] text-white">Candidate verifications</h2>

      {error ? <p className="text-sm text-[#ff9b9b]">{error}</p> : null}
      {rows === null && !error ? <p className="text-sm text-[#9aa7b8]">Loading stored Midnight results…</p> : null}

      <Card className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-[#101821] text-[#9aa7b8]">
              <tr>
                <th className="px-5 py-4 font-medium">Upload</th>
                <th className="px-5 py-4 font-medium">Role</th>
                <th className="px-5 py-4 font-medium">Match</th>
                <th className="px-5 py-4 font-medium">Midnight status</th>
              </tr>
            </thead>
            <tbody>
              {rows && rows.length === 0 ? (
                <tr className="border-t border-[#1c2430]">
                  <td className="px-5 py-6 text-[#9aa7b8]" colSpan={4}>
                    No candidate verifications have been recorded.
                  </td>
                </tr>
              ) : null}
              {(rows ?? []).map((row) => (
                <tr key={`${row.uploadId}:${row.jobId}`} className="border-t border-[#1c2430]">
                  <td className="px-5 py-4 font-medium text-[#edf3f8]">{row.uploadId}</td>
                  <td className="px-5 py-4 text-[#edf3f8]">
                    {row.company ? `${row.jobTitle} — ${row.company}` : row.jobTitle}
                  </td>
                  <td className="px-5 py-4 text-[#7adcc8]">
                    {row.matchScore === null ? "—" : `${row.matchScore}%`}
                  </td>
                  <td className="px-5 py-4">
                    <Badge tone={badgeTone(row)}>{verificationLabel(row.proof)}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
