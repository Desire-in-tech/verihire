/**
 * The facade resolves this wait when shielded, dust, and unshielded sync
 * progress are strictly complete. Callers must not balance before it resolves.
 */
export async function assertWalletReady(
  waitForSyncedState: () => Promise<{ isSynced: boolean }>,
): Promise<void> {
  const state = await waitForSyncedState();
  if (!state.isSynced) {
    throw new Error("wallet synchronization did not complete before DUST balancing");
  }
}
