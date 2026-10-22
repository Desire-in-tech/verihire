"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { CVUploadResult } from "@/lib/verihire-data";
import { verificationIsPositive, verificationLabel } from "@/lib/verification-label";

const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

type ListedJob = {
  job_id: string;
  title: string;
  company: string;
};

function listedJobsFromPayload(payload: unknown): ListedJob[] {
  if (!payload || typeof payload !== "object" || !Array.isArray((payload as { jobs?: unknown }).jobs)) {
    throw new Error("Job list response did not include a jobs array.");
  }

  return (payload as { jobs: unknown[] }).jobs.map((job) => {
    if (!job || typeof job !== "object") {
      throw new Error("Job list response included an incomplete job.");
    }
    const record = job as { job_id?: unknown; title?: unknown; company?: unknown };
    if (typeof record.job_id !== "string" || !record.job_id.trim() || typeof record.title !== "string" || !record.title.trim()) {
      throw new Error("Job list response included an incomplete job.");
    }
    return {
      job_id: record.job_id,
      title: record.title,
      company: typeof record.company === "string" ? record.company : "",
    };
  });
}

export function CvUploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const [jobs, setJobs] = useState<ListedJob[] | null>(null);
  const [jobsError, setJobsError] = useState("");
  const [selectedJobId, setSelectedJobId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState<CVUploadResult | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadJobs() {
      try {
        const response = await fetch(`${apiUrl}/api/jobs`);
        const payload = await response.json().catch(() => null);
        if (!response.ok) {
          const detail = payload && typeof payload === "object" && typeof (payload as { detail?: unknown }).detail === "string"
            ? (payload as { detail: string }).detail
            : `Job list request failed (${response.status}).`;
          throw new Error(detail);
        }
        const listed = listedJobsFromPayload(payload);
        if (!cancelled) {
          setJobs(listed);
          setJobsError(listed.length === 0 ? "No jobs are available to select." : "");
        }
      } catch (loadError) {
        if (!cancelled) {
          setJobs(null);
          setSelectedJobId("");
          setJobsError(loadError instanceof Error ? loadError.message : "The job list could not be loaded.");
        }
      }
    }

    void loadJobs();
    return () => {
      cancelled = true;
    };
  }, []);

  function validatePdf(candidate: File) {
    const hasPdfExtension = candidate.name.toLowerCase().endsWith(".pdf");
    const hasPdfMimeType = !candidate.type || candidate.type === "application/pdf";

    if (!hasPdfExtension || !hasPdfMimeType) {
      return "CVs must be uploaded as PDF files.";
    }

    return "";
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setResult(null);
    setMessage("");
    setError(selected ? validatePdf(selected) : "");
    setFile(selected);
  }

  const pdfError = file ? validatePdf(file) : "";
  const selectedJob = jobs?.find((job) => job.job_id === selectedJobId) ?? null;
  const canSubmit = Boolean(file) && !pdfError && Boolean(selectedJob) && !jobsError && !isUploading;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (jobsError || !jobs) {
      setError(jobsError || "The job list is not available.");
      return;
    }
    if (!selectedJob) {
      setError("Select a job before uploading.");
      return;
    }
    if (!file) {
      setError("Choose a PDF CV before uploading.");
      return;
    }

    const validationError = validatePdf(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsUploading(true);
    setError("");
    setMessage("");
    setResult(null);

    try {
      const body = new FormData();
      body.append("file", file);
      body.append("job_id", selectedJob.job_id);

      const response = await fetch(`${apiUrl}/api/upload-cv`, {
        method: "POST",
        body,
      });
      const payload = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(payload?.detail ?? "The CV could not be processed.");
      }

      setResult(payload as CVUploadResult);
      setMessage("CV uploaded. Your profile was matched without exposing your source document.");
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "The CV could not be processed.");
    } finally {
      setIsUploading(false);
    }
  }

  const firstMatch = result?.matching_results[0];
  const firstProof = result?.proof_results[0];

  return (
    <div className="mt-6 border-t border-[#26313a] pt-6">
      <div className="mb-4">
        <p className="text-sm font-medium text-white">Upload your CV</p>
        <p className="mt-1 text-sm leading-6 text-[#9aa9b9]">
          CVs must be PDF files. Your document is parsed for matching; employers only receive verification claims.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <label className="block text-sm text-[#dfeaf8]" htmlFor="cv-job">
          Job
        </label>
        <select
          id="cv-job"
          value={selectedJobId}
          onChange={(event) => {
            setSelectedJobId(event.target.value);
            setResult(null);
            setMessage("");
            setError("");
          }}
          disabled={jobs === null || Boolean(jobsError) || isUploading}
          className="block w-full rounded-xl border border-[#3a4653] bg-[#0b1118] px-4 py-3 text-sm text-[#dfe9f8] outline-none focus:border-[#31d4c7] disabled:cursor-not-allowed disabled:opacity-60"
        >
          <option value="">Select a job</option>
          {(jobs ?? []).map((job) => (
            <option key={job.job_id} value={job.job_id}>
              {job.company ? `${job.title} — ${job.company}` : job.title}
            </option>
          ))}
        </select>
        {jobs === null && !jobsError ? <p className="text-xs text-[#9aa9b9]">Loading jobs…</p> : null}
        {jobsError ? <p className="text-sm text-[#ff9b9b]">{jobsError}</p> : null}

        <input
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleFileChange}
          className="block w-full rounded-xl border border-dashed border-[#3a4653] bg-[#0b1118] px-4 py-4 text-sm text-[#dfe9f8] file:mr-4 file:rounded-lg file:border-0 file:bg-[#26313a] file:px-3 file:py-2 file:text-sm file:font-medium file:text-white hover:border-[#31d4c7]"
        />
        {file ? <p className="text-xs text-[#9aa9b9]">{file.name}</p> : null}
        <Button type="submit" disabled={!canSubmit} className="disabled:cursor-not-allowed disabled:opacity-60">
          {isUploading ? "Processing PDF…" : "Upload PDF CV"}
        </Button>
      </form>

      {error ? <p className="mt-3 text-sm text-[#ff9b9b]">{error}</p> : null}
      {message ? <p className="mt-3 text-sm text-[#8de2c9]">{message}</p> : null}

      {result && firstMatch && firstProof ? (
        <div className="mt-4 rounded-xl border border-[#26313a] bg-[#0b1118] p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={firstMatch.matches ? "green" : "slate"}>
              {firstMatch.matches ? "Match found" : "Not a match yet"}
            </Badge>
            <Badge tone={verificationIsPositive(firstProof) ? "green" : "slate"}>
              {verificationLabel(firstProof)}
            </Badge>
          </div>
          <p className="mt-3 text-sm text-[#dfe9f8]">
            Matching score: <span className="font-semibold text-white">{firstMatch.score}%</span>
          </p>
          <p className="mt-1 text-xs leading-5 text-[#9aa9b9]">
            {firstProof.proof_data?.message ??
              "The employer-facing result contains only the match and verification status."}
          </p>
        </div>
      ) : null}
    </div>
  );
}
