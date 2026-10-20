export type VerificationStatusName =
  | "verified"
  | "failed"
  | "unavailable"
  | "not_configured"
  | null;

export type ProofData = {
  message?: string;
  verification_status?: VerificationStatusName;
  eligible?: boolean | null;
  unsupported_criteria?: string[];
  proof_id?: string | null;
  block_height?: number | null;
};

export type LabeledProof = {
  applicant_verified: boolean;
  proof_data?: ProofData;
};

export function verificationIsPositive(proof: LabeledProof): boolean {
  return (
    proof.proof_data?.verification_status === "verified" &&
    proof.proof_data?.eligible === true
  );
}

export function verificationLabel(proof: LabeledProof): string {
  const unsupported = proof.proof_data?.unsupported_criteria ?? [];
  if (unsupported.length > 0) {
    return `Not sent to Midnight: ${unsupported.join("; ")}`;
  }

  const status = proof.proof_data?.verification_status ?? null;
  const eligible = proof.proof_data?.eligible;

  if (status === "verified" && eligible === true) {
    return "Eligible, verification succeeded";
  }
  if (status === "verified" && eligible === false) {
    return "Not eligible, verification succeeded";
  }
  if (status === "failed") {
    return "Verification failed";
  }
  if (status === "not_configured") {
    return "Midnight is not configured";
  }
  return "Verification unavailable";
}
