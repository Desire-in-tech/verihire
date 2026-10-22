/** Bound for one wallet-sync wait. There is no second attempt. */
export const WALLET_SYNC_TIMEOUT_MS = 120_000;

/**
 * The facade resolves this wait when shielded, dust, and unshielded sync
 * progress are strictly complete. Callers must not balance or submit before
 * it resolves. A hang fails once, before any transaction is submitted.
 */
export async function assertWalletReady(
  waitForSyncedState: () => Promise<{ isSynced: boolean }>,
  timeoutMs: number = WALLET_SYNC_TIMEOUT_MS,
): Promise<void> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_resolve, reject) => {
    timer = setTimeout(() => {
      reject(new Error("wallet synchronization timed out before transaction submission"));
    }, timeoutMs);
  });
  try {
    const state = await Promise.race([waitForSyncedState(), timeout]);
    if (!state.isSynced) {
      throw new Error("wallet synchronization did not complete before DUST balancing");
    }
  } finally {
    if (timer !== undefined) {
      clearTimeout(timer);
    }
  }
}
