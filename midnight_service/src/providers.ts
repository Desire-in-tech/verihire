import { WebSocket } from "ws";
import { levelPrivateStateProvider } from "@midnight-ntwrk/midnight-js-level-private-state-provider";
import { indexerPublicDataProvider } from "@midnight-ntwrk/midnight-js-indexer-public-data-provider";
import { NodeZkConfigProvider } from "@midnight-ntwrk/midnight-js-node-zk-config-provider";
import { httpClientProofProvider } from "@midnight-ntwrk/midnight-js-http-client-proof-provider";
import { setNetworkId } from "@midnight-ntwrk/midnight-js-network-id";
import type {
  MidnightProvider,
  UnboundTransaction,
  WalletProvider,
} from "@midnight-ntwrk/midnight-js-types";
import * as ledger from "@midnight-ntwrk/midnight-js-protocol/ledger";
import type { FinalizedTransaction } from "@midnight-ntwrk/midnight-js-protocol/ledger";
import {
  HDWallet,
  Roles,
  WalletFacade,
  ShieldedWallet,
  DustWallet,
  UnshieldedWallet,
  createKeystore,
  InMemoryTransactionHistoryStorage,
  WalletEntrySchema,
  PublicKey as UnshieldedPublicKey,
  type UnshieldedKeystore,
} from "@midnight-ntwrk/wallet-sdk";

// Apollo's indexer client reads WebSocket from the global scope in Node.
// This is the official Node setup used by Midnight's current examples.
(globalThis as any).WebSocket = WebSocket;

export type VerihireCircuitId = "proveEligibility" | "checkResult";

export type MidnightEnvironment = {
  indexerUrl: string;
  indexerWsUrl: string;
  nodeUrl: string;
  proofServerUrl: string;
  compiledContractDir: string;
  walletAddress: string;
  networkId: "preprod" | "undeployed";
  walletSeed: Uint8Array;
  storagePassword: string;
};

export type WalletContext = {
  wallet: WalletFacade;
  shieldedSecretKeys: ledger.ZswapSecretKeys;
  dustSecretKey: ledger.DustSecretKey;
  unshieldedKeystore: UnshieldedKeystore;
};

export function readWalletSeed(value = process.env.WALLET_SEED): Uint8Array {
  const seed = value?.trim();
  if (!seed || !/^[0-9a-fA-F]+$/.test(seed) || ![64, 128].includes(seed.length)) {
    throw new Error("WALLET_SEED must be a 32-byte or 64-byte hexadecimal seed");
  }
  return Uint8Array.from(Buffer.from(seed, "hex"));
}

async function createWallet(env: MidnightEnvironment): Promise<WalletContext> {
  const hdWallet = HDWallet.fromSeed(env.walletSeed);
  if (hdWallet.type !== "seedOk") {
    throw new Error("WALLET_SEED could not initialize an HD wallet");
  }

  const derivationResult = hdWallet.hdWallet
    .selectAccount(0)
    .selectRoles([Roles.Zswap, Roles.NightExternal, Roles.Dust])
    .deriveKeysAt(0);
  if (derivationResult.type !== "keysDerived") {
    throw new Error("WALLET_SEED could not derive wallet keys");
  }
  hdWallet.hdWallet.clear();

  const shieldedSecretKeys = ledger.ZswapSecretKeys.fromSeed(derivationResult.keys[Roles.Zswap]);
  const dustSecretKey = ledger.DustSecretKey.fromSeed(derivationResult.keys[Roles.Dust]);
  const unshieldedKeystore = createKeystore(
    derivationResult.keys[Roles.NightExternal],
    env.networkId,
  );

  const relayURL = new URL(env.nodeUrl.replace(/^http/, "ws"));
  const history = () => new InMemoryTransactionHistoryStorage(WalletEntrySchema);
  const shared = {
    networkId: env.networkId,
    indexerClientConnection: {
      indexerHttpUrl: env.indexerUrl,
      indexerWsUrl: env.indexerWsUrl,
    },
  };
  const shieldedConfig = {
    ...shared,
    provingServerUrl: new URL(env.proofServerUrl),
    relayURL,
    txHistoryStorage: history(),
  };
  const unshieldedConfig = { ...shared, txHistoryStorage: history() };
  const dustConfig = {
    ...shared,
    costParameters: {
      additionalFeeOverhead: 300_000_000_000_000n,
      feeBlocksMargin: 5,
    },
    provingServerUrl: new URL(env.proofServerUrl),
    relayURL,
    txHistoryStorage: history(),
  };

  const wallet = await WalletFacade.init({
    configuration: { ...shieldedConfig, ...unshieldedConfig, ...dustConfig },
    shielded: () => ShieldedWallet(shieldedConfig).startWithSecretKeys(shieldedSecretKeys),
    unshielded: () =>
      UnshieldedWallet(unshieldedConfig).startWithPublicKey(
        UnshieldedPublicKey.fromKeyStore(unshieldedKeystore),
      ),
    dust: () =>
      DustWallet(dustConfig).startWithSecretKey(
        dustSecretKey,
        ledger.LedgerParameters.initialParameters().dust,
      ),
  });
  await wallet.start(shieldedSecretKeys, dustSecretKey);
  return { wallet, shieldedSecretKeys, dustSecretKey, unshieldedKeystore };
}

function createWalletProviders(context: WalletContext): WalletProvider & MidnightProvider {
  return {
    getCoinPublicKey: () => context.shieldedSecretKeys.coinPublicKey,
    getEncryptionPublicKey: () => context.shieldedSecretKeys.encryptionPublicKey,
    async balanceTx(tx: UnboundTransaction, ttl?: Date): Promise<FinalizedTransaction> {
      const recipe = await context.wallet.balanceUnboundTransaction(
        tx,
        {
          shieldedSecretKeys: context.shieldedSecretKeys,
          dustSecretKey: context.dustSecretKey,
        },
        { ttl: ttl ?? new Date(Date.now() + 30 * 60 * 1000) },
      );
      return context.wallet.finalizeRecipe(recipe);
    },
    submitTx: (tx) => context.wallet.submitTransaction(tx),
  };
}

export async function buildProviders(env: MidnightEnvironment) {
  if (!env.indexerUrl || !env.indexerWsUrl || !env.nodeUrl) {
    throw new Error("INDEXER_URL, INDEXER_WS_URL, and NODE_URL are required");
  }
  if (!env.storagePassword || env.storagePassword.length < 16) {
    throw new Error("MIDNIGHT_STORAGE_PASSWORD must be at least 16 characters");
  }

  setNetworkId(env.networkId);
  const walletContext = await createWallet(env);
  const privateStateProvider = levelPrivateStateProvider({
    privateStateStoreName: "verihire-private-state",
    signingKeyStoreName: "verihire-signing-keys",
    privateStoragePasswordProvider: () => env.storagePassword,
    accountId: env.walletAddress || walletContext.unshieldedKeystore.getBech32Address().asString(),
  });
  const publicDataProvider = indexerPublicDataProvider(
    env.indexerUrl,
    env.indexerWsUrl,
  );
  const zkConfigProvider = new NodeZkConfigProvider<VerihireCircuitId>(
    env.compiledContractDir,
  );
  const proofProvider = httpClientProofProvider(
    env.proofServerUrl,
    zkConfigProvider,
  );
  const walletAndMidnightProvider = createWalletProviders(walletContext);

  return {
    privateStateProvider,
    publicDataProvider,
    zkConfigProvider,
    proofProvider,
    walletProvider: walletAndMidnightProvider,
    midnightProvider: walletAndMidnightProvider,
  };
}