/**
 * Read a finalized eligibility Map without another proving transaction.
 *
 * Compact's Map ADT exposes `member` and `lookup`, not `get`
 * (https://docs.midnight.network/compact/reference/ledger-adt).
 * `lookup` is only called after `member` reports the key is present.
 * A missing key is an unconfirmed result, not an ineligible one.
 */

export type EligibilityMap = {
  member(key: Uint8Array): boolean;
  lookup(key: Uint8Array): boolean;
};

export type LedgerEligibility = {
  verification_status: "verified" | "failed";
  eligible: boolean | null;
  message: string;
};

export function readEligibility(map: EligibilityMap, key: Uint8Array): LedgerEligibility {
  if (!map.member(key)) {
    return {
      verification_status: "failed",
      eligible: null,
      message: "The transaction returned but the result key is not in the ledger.",
    };
  }

  const eligible = map.lookup(key);
  if (typeof eligible !== "boolean") {
    return {
      verification_status: "failed",
      eligible: null,
      message: "The ledger result was not a Boolean.",
    };
  }

  return {
    verification_status: "verified",
    eligible,
    message: eligible
      ? "Eligible, verification succeeded."
      : "Not eligible, verification succeeded.",
  };
}
