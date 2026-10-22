import type { LabeledProof, VerificationStatusName } from "./verification-label";

const statuses = new Set<VerificationStatusName>([
  "verified",
  "failed",
  "unavailable",
  "not_configured",
  "unknown",
  null,
]);

export type EmployerResultRow = {
  uploadId: string;
  jobId: string;
  jobTitle: string;
  company: string;
  matchScore: number | null;
  matches: boolean | null;
  proof: LabeledProof;
};

function publicProof(value: unknown): LabeledProof {
  const record = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  const rawStatus = record.verification_status;
  const status = statuses.has(rawStatus as VerificationStatusName)
    ? (rawStatus as VerificationStatusName)
    : "unavailable";
  const eligible = record.eligible;
  const proofId = typeof record.proof_id === "string" && record.proof_id ? record.proof_id : null;
  const proof: LabeledProof = {
    applicant_verified: false,
    proof_data: {
      verification_status: status === "unknown" && !proofId ? "unavailable" : status,
      eligible: status === "verified" && (eligible === true || eligible === false) ? eligible : null,
      unsupported_criteria: Array.isArray(record.unsupported_criteria)
        ? record.unsupported_criteria.filter((item): item is string => typeof item === "string")
        : [],
      proof_id: proofId,
      block_height: typeof record.block_height === "number" ? record.block_height : null,
      message: typeof record.message === "string" ? record.message : "",
    },
  };
  proof.applicant_verified =
    proof.proof_data?.verification_status === "verified" && proof.proof_data?.eligible === true;
  return proof;
}

export function parseEmployerResults(payload: unknown): EmployerResultRow[] {
  if (!payload || typeof payload !== "object" || !Array.isArray((payload as { results?: unknown }).results)) {
    throw new Error("Employer results response did not include a results array.");
  }

  return (payload as { results: unknown[] }).results.flatMap((row) => {
    if (!row || typeof row !== "object") {
      return [];
    }
    const record = row as Record<string, unknown>;
    if (typeof record.upload_id !== "string" || !record.upload_id.trim()) {
      return [];
    }
    if (typeof record.job_id !== "string" || !record.job_id.trim()) {
      return [];
    }
    const score = record.match_score;
    const proof = publicProof(record.proof_data);
    return [
      {
        uploadId: record.upload_id,
        jobId: record.job_id,
        jobTitle: typeof record.job_title === "string" && record.job_title.trim() ? record.job_title : record.job_id,
        company: typeof record.company === "string" ? record.company : "",
        matchScore: typeof score === "number" && Number.isFinite(score) ? score : null,
        matches: typeof record.matches === "boolean" ? record.matches : null,
        proof,
      },
    ];
  });
}

export function countVerifiedEligible(rows: EmployerResultRow[]): number {
  return rows.filter((row) => row.proof.applicant_verified).length;
}
