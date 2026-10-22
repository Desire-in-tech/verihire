import express, { type Express } from "express";
import {
  requireExplicitLocalProofConfig,
  type LocalNetworkConfig,
} from "./local-network.js";

export type ProveProviders = {
  awaitWalletReady: () => Promise<void>;
};

export type ProveOutcome = {
  verification_status: string;
  eligible: boolean | null;
  message: string;
};

export type ProveRouteDependencies = {
  env: Record<string, string | undefined>;
  connect: (network: LocalNetworkConfig) => Promise<ProveProviders>;
  joinContract: (providers: ProveProviders) => Promise<{
    callTx: {
      proveEligibility: (
        resultKey: Uint8Array,
        pythonYears: bigint,
        hasPostgresql: boolean,
        hasAwsCert: boolean,
        hasBachelorsOrEquivalent: boolean,
        requiredPythonYears: bigint,
        requirePostgresql: boolean,
        requireAwsCert: boolean,
        requireBachelors: boolean,
      ) => Promise<{ public: { txId?: string | null; blockHeight?: number | null } }>;
    };
  }>;
  readOutcome: (providers: ProveProviders, resultKey: Uint8Array) => Promise<ProveOutcome>;
};

type ProveRequestBody = {
  result_key: string;
  python_years: number;
  has_postgresql: boolean;
  has_aws_cert: boolean;
  has_bachelors_or_equivalent: boolean;
  required_python_years: number;
  require_postgresql: boolean;
  require_aws_cert: boolean;
  require_bachelors: boolean;
};

function sameNetwork(left: LocalNetworkConfig, right: LocalNetworkConfig): boolean {
  return (
    left.networkId === right.networkId &&
    left.nodeUrl === right.nodeUrl &&
    left.indexerUrl === right.indexerUrl &&
    left.indexerWsUrl === right.indexerWsUrl &&
    left.proofServerUrl === right.proofServerUrl
  );
}

function requestIsValid(body: ProveRequestBody | undefined): body is ProveRequestBody {
  return Boolean(
    body &&
      /^[0-9a-fA-F]{64}$/.test(body.result_key) &&
      Number.isInteger(body.python_years) &&
      body.python_years >= 0 &&
      Number.isInteger(body.required_python_years) &&
      body.required_python_years >= 0 &&
      typeof body.has_postgresql === "boolean" &&
      typeof body.has_aws_cert === "boolean" &&
      typeof body.has_bachelors_or_equivalent === "boolean" &&
      typeof body.require_postgresql === "boolean" &&
      typeof body.require_aws_cert === "boolean" &&
      typeof body.require_bachelors === "boolean",
  );
}

/**
 * POST /prove. Network configuration is checked before any connection.
 * Wallet readiness is awaited before the contract is joined or the
 * eligibility transaction is built and submitted. There is no second attempt.
 */
export function registerProveRoute(app: Express, deps: ProveRouteDependencies): void {
  let pinnedNetwork: LocalNetworkConfig | null = null;

  app.post("/prove", async (req, res) => {
    const body = req.body as ProveRequestBody | undefined;

    try {
      if (!requestIsValid(body)) {
        return res.status(400).json({
          verification_status: "failed",
          eligible: null,
          unsupported_criteria: [],
          proof_id: null,
          block_height: null,
          message: "Invalid proof request",
        });
      }

      const network = requireExplicitLocalProofConfig(deps.env);
      if (pinnedNetwork && !sameNetwork(pinnedNetwork, network)) {
        throw new Error("refusing to change the proof network");
      }
      const contractAddress = deps.env.CONTRACT_ADDRESS?.trim() ?? "";
      if (!contractAddress) {
        throw new Error(
          "CONTRACT_ADDRESS is not set - deploy the contract first with `npm run deploy-contract`.",
        );
      }
      pinnedNetwork = network;

      const providers = await deps.connect(network);
      await providers.awaitWalletReady();
      const contract = await deps.joinContract(providers);
      const resultKeyBytes = Uint8Array.from(Buffer.from(body.result_key, "hex"));
      const txData = await contract.callTx.proveEligibility(
        resultKeyBytes,
        BigInt(body.python_years),
        body.has_postgresql,
        body.has_aws_cert,
        body.has_bachelors_or_equivalent,
        BigInt(body.required_python_years),
        body.require_postgresql,
        body.require_aws_cert,
        body.require_bachelors,
      );
      const outcome = await deps.readOutcome(providers, resultKeyBytes);

      res.json({
        verification_status: outcome.verification_status,
        eligible: outcome.eligible,
        unsupported_criteria: [],
        proof_id: txData.public.txId ?? null,
        block_height: txData.public.blockHeight ?? null,
        message: outcome.message,
      });
    } catch (err) {
      console.error("proveEligibility call failed:", err);
      res.status(502).json({
        verification_status: "failed",
        eligible: null,
        unsupported_criteria: [],
        proof_id: null,
        block_height: null,
        message: String(err),
      });
    }
  });
}

export function createProveApp(deps: ProveRouteDependencies): Express {
  const app = express();
  app.use(express.json());
  registerProveRoute(app, deps);
  return app;
}
