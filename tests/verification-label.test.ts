import assert from "node:assert/strict";
import test from "node:test";
import { verificationIsPositive, verificationLabel } from "../frontend/lib/verification-label.ts";

const base = { applicant_verified: false };

test("labels a verified eligible result and allows a positive badge", () => {
  const proof = {
    applicant_verified: true,
    proof_data: {
      verification_status: "verified" as const,
      eligible: true,
      unsupported_criteria: [],
      proof_id: "tx",
    },
  };
  assert.equal(verificationLabel(proof), "Eligible, verification succeeded");
  assert.equal(verificationIsPositive(proof), true);
});

test("labels verified ineligibility without a positive badge", () => {
  const proof = {
    ...base,
    proof_data: {
      verification_status: "verified" as const,
      eligible: false,
      proof_id: "tx",
    },
  };
  assert.equal(verificationLabel(proof), "Not eligible, verification succeeded");
  assert.equal(verificationIsPositive(proof), false);
});

test("labels failed, unavailable, and not configured distinctly", () => {
  assert.equal(
    verificationLabel({ ...base, proof_data: { verification_status: "failed", eligible: null } }),
    "Verification failed",
  );
  assert.equal(
    verificationLabel({ ...base, proof_data: { verification_status: "unavailable", eligible: null } }),
    "Verification unavailable",
  );
  assert.equal(
    verificationLabel({
      ...base,
      proof_data: { verification_status: "not_configured", eligible: null, proof_id: null },
    }),
    "Midnight is not configured",
  );
  assert.equal(verificationIsPositive(base), false);
});

test("labels a refusal with every unsupported field", () => {
  const proof = {
    ...base,
    proof_data: {
      verification_status: null,
      eligible: null,
      unsupported_criteria: ["skill fastapi: 3 years", "language: English"],
      proof_id: null,
    },
  };
  assert.equal(
    verificationLabel(proof),
    "Not sent to Midnight: skill fastapi: 3 years; language: English",
  );
  assert.equal(verificationIsPositive(proof), false);
});

test("labels an unknown submitted outcome without a positive badge", () => {
  const proof = {
    ...base,
    proof_data: {
      verification_status: "unknown" as const,
      eligible: null,
      proof_id: "tx-submitted",
    },
  };
  assert.equal(verificationLabel(proof), "Outcome unknown after submission. Do not resubmit.");
  assert.equal(verificationIsPositive(proof), false);
});

test("an applicant_verified flag alone is not a positive badge", () => {
  const proof = { applicant_verified: true, proof_data: { verification_status: "failed" as const, eligible: null } };
  assert.equal(verificationIsPositive(proof), false);
  assert.equal(verificationLabel(proof), "Verification failed");
});
