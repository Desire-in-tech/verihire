import assert from "node:assert/strict";
import test from "node:test";
import { readEligibility } from "../src/eligibility.ts";

function recordingMap(present: boolean, value?: boolean) {
  const calls: string[] = [];
  return {
    calls,
    member(key: Uint8Array) {
      calls.push(`member:${key.length}`);
      return present;
    },
    lookup(key: Uint8Array) {
      calls.push(`lookup:${key.length}`);
      return value as boolean;
    },
  };
}

test("member is checked before lookup and a missing key is not ineligible", () => {
  const key = new Uint8Array(32);
  const map = recordingMap(false, false);
  const outcome = readEligibility(map, key);
  assert.deepEqual(map.calls, ["member:32"]);
  assert.equal(outcome.verification_status, "failed");
  assert.equal(outcome.eligible, null);
});

test("a present true ledger value is verified eligibility", () => {
  const key = new Uint8Array(32);
  const map = recordingMap(true, true);
  const outcome = readEligibility(map, key);
  assert.deepEqual(map.calls, ["member:32", "lookup:32"]);
  assert.equal(outcome.verification_status, "verified");
  assert.equal(outcome.eligible, true);
});

test("a present false ledger value is verified ineligibility", () => {
  const outcome = readEligibility(recordingMap(true, false), new Uint8Array(32));
  assert.equal(outcome.verification_status, "verified");
  assert.equal(outcome.eligible, false);
});

test("a non-boolean lookup is not treated as ineligible", () => {
  const outcome = readEligibility(recordingMap(true, undefined), new Uint8Array(32));
  assert.equal(outcome.verification_status, "failed");
  assert.equal(outcome.eligible, null);
});
