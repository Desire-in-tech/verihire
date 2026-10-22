import assert from "node:assert/strict";
import test from "node:test";
import { assertWalletReady } from "../src/wallet-ready.ts";

test("a synchronized wallet may proceed to balancing", async () => {
  let waited = false;
  await assertWalletReady(async () => {
    waited = true;
    return { isSynced: true };
  });
  assert.equal(waited, true);
});

test("a readiness wait that fails is not treated as synchronized", async () => {
  await assert.rejects(
    () =>
      assertWalletReady(async () => {
        throw new Error("sync stream failed");
      }),
    /sync stream failed/,
  );
});

test("a resolved wallet that is not strictly synced cannot balance", async () => {
  await assert.rejects(
    () => assertWalletReady(async () => ({ isSynced: false })),
    /wallet synchronization did not complete before DUST balancing/,
  );
});
