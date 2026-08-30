"use client";

import { ChangeEvent, FormEvent, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { CVUploadResult } from "@/lib/verihire-data";

const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export function CvUploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState<CVUploadResult | null>(null);
  const [isUploading, setIsUploading] = useState(false);

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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
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
      body.append("job_id", "job-001");

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
        <input
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleFileChange}
          className="block w-full rounded-xl border border-dashed border-[#3a4653] bg-[#0b1118] px-4 py-4 text-sm text-[#dfe9f8] file:mr-4 file:rounded-lg file:border-0 file:bg-[#26313a] file:px-3 file:py-2 file:text-sm file:font-medium file:text-white hover:border-[#31d4c7]"
        />
        {file ? <p className="text-xs text-[#9aa9b9]">{file.name}</p> : null}
        <Button type="submit" disabled={isUploading} className="disabled:cursor-not-allowed disabled:opacity-60">
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
            <Badge tone={firstProof.applicant_verified ? "green" : "slate"}>
              {firstProof.applicant_verified ? "Midnight verified" : "Verification pending"}
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