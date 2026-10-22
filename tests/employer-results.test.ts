import assert from "node:assert/strict";
import test from "node:test";
import { countVerifiedEligible, parseEmployerResults } from "../frontend/lib/employer-results.ts";
import { verificationIsPositive, verificationLabel } from "../frontend/lib/verification-label.ts";

test("a stored verified flag does not create a positive employer badge", () => {
  const rows = parseEmployerResults({
    results: [
      {
        upload_id: "upload-1",
        job_id: "job-004",
        job_title: "Python Backend Developer",
        company: "Example",
        match_score: 40,
        matches: false,
        applicant_verified: true,
        proof_data: {
          verification_status: "failed",
          eligible: true,
          proof_id: "tx-failed",
        },
      },
    ],
  });
  assert.equal(rows.length, 1);
  assert.equal(verificationIsPositive(rows[0].proof), false);
  assert.equal(verificationLabel(rows[0].proof), "Verification failed");
  assert.equal(countVerifiedEligible(rows), 0);
  assert.equal(rows[0].proof.proof_data?.proof_id, "tx-failed");
  assert.equal(rows[0].proof.proof_data?.eligible, null);
});

test("counts only a verified eligible Midnight result", () => {
  const rows = parseEmployerResults({
    results: [
      {
        upload_id: "upload-2",
        job_id: "job-004",
        job_title: "Python Backend Developer",
        match_score: 90,
        matches: true,
        applicant_verified: false,
        proof_data: {
          verification_status: "verified",
          eligible: true,
          proof_id: "tx-ok",
        },
      },
      {
        upload_id: "upload-3",
        job_id: "job-004",
        job_title: "Python Backend Developer",
        applicant_verified: true,
        proof_data: {
          verification_status: "unknown",
          eligible: true,
          proof_id: "tx-pending",
          message: "Do not resubmit it automatically.",
        },
      },
    ],
  });
  assert.equal(countVerifiedEligible(rows), 1);
  assert.equal(verificationLabel(rows[1].proof), "Outcome unknown after submission. Do not resubmit.");
  assert.equal(rows[1].proof.proof_data?.proof_id, "tx-pending");
  assert.equal(rows[1].proof.proof_data?.eligible, null);
});

test("an empty results array stays empty", () => {
  assert.deepEqual(parseEmployerResults({ results: [] }), []);
});
