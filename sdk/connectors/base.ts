/*
 * Connector SDK base definitions and concrete sandbox implementations.
 */

export type AuthorizationResult = {
  /** Access token issued by the integration provider. */
  token: string;
  /** Absolute ISO-8601 timestamp when the token will expire. */
  expiresAt: string;
  /** Provider-specific payload returned from the authorization request. */
  raw: unknown;
};

export type NormalizedRecord = {
  /** Provider record identifier coerced to a string. */
  id: string;
  /** Flat attribute bag extracted from the provider response. */
  attributes: Record<string, unknown>;
};

export type NormalizedResponse = {
  /** Records coerced into the SDK-wide canonical shape. */
  records: NormalizedRecord[];
  /** Original payload for auditing and debugging. */
  raw: unknown;
  /** Metadata about pagination, rate limits, or other contextual signals. */
  meta: Record<string, unknown>;
};

export type OperationResult = {
  success: boolean;
  message?: string;
  raw?: unknown;
};

export type WebhookRegistration = {
  id: string;
  status: "active" | "pending" | "disabled";
  raw?: unknown;
};

export type SyncStatus = {
  status: "idle" | "running" | "error";
  lastSync: string | null;
  details?: string;
};

export interface Connector {
  authorize(): Promise<AuthorizationResult>;
  fetchData(params?: Record<string, unknown>): Promise<NormalizedResponse>;
  pushData(payload: Record<string, unknown>): Promise<OperationResult>;
  registerWebhook(callbackUrl: string): Promise<WebhookRegistration>;
  syncStatus(): Promise<SyncStatus>;
}

export type SandboxCredentialSet = {
  label: string;
  values: Record<string, string>;
};

export abstract class ConnectorBase implements Connector {
  protected constructor(
    protected readonly name: string,
    protected readonly sandboxCredentials: SandboxCredentialSet,
  ) {}

  abstract authorize(): Promise<AuthorizationResult>;

  abstract fetchData(params?: Record<string, unknown>): Promise<NormalizedResponse>;

  abstract pushData(payload: Record<string, unknown>): Promise<OperationResult>;

  abstract registerWebhook(callbackUrl: string): Promise<WebhookRegistration>;

  abstract syncStatus(): Promise<SyncStatus>;

  /**
   * Helper for coercing provider payloads into the canonical SDK response shape.
   */
  protected normalizeRecords(
    source: string,
    records: ReadonlyArray<Record<string, unknown>>,
    idKey: string,
    additionalMeta: Record<string, unknown> = {},
  ): NormalizedResponse {
    const normalizedRecords: NormalizedRecord[] = records.map((record, index) => {
      const resolvedId = record[idKey];
      const id = typeof resolvedId === "string" || typeof resolvedId === "number"
        ? String(resolvedId)
        : `${source}-${index}`;

      const { [idKey]: _, ...attributes } = record;
      return {
        id,
        attributes,
      };
    });

    return {
      records: normalizedRecords,
      raw: records,
      meta: {
        source,
        receivedAt: new Date().toISOString(),
        sandbox: true,
        credentialsUsed: this.sandboxCredentials.label,
        ...additionalMeta,
      },
    };
  }
}

const SQUARE_SANDBOX_CREDENTIALS: SandboxCredentialSet = {
  label: "Square Sandbox",
  values: {
    applicationId: process.env.SQUARE_SANDBOX_APPLICATION_ID ?? "sandbox-sq0idb-application-id",
    accessToken: process.env.SQUARE_SANDBOX_ACCESS_TOKEN ?? "EAAAEDSqSandboxAccessToken",
    locationId: process.env.SQUARE_SANDBOX_LOCATION_ID ?? "L88917J0S0P1N",
  },
};

export class SquareConnector extends ConnectorBase {
  constructor() {
    super("Square", SQUARE_SANDBOX_CREDENTIALS);
  }

  async authorize(): Promise<AuthorizationResult> {
    const token = this.sandboxCredentials.values.accessToken;
    return {
      token,
      expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
      raw: {
        token,
        applicationId: this.sandboxCredentials.values.applicationId,
      },
    };
  }

  async fetchData(params: Record<string, unknown> = {}): Promise<NormalizedResponse> {
    const { limit = 2 } = params;
    const payments = [
      {
        id: "GQTFp1ZlXdpoW4o6eGiZ",
        amount_money: { amount: 2045, currency: "USD" },
        status: "COMPLETED",
        created_at: "2024-09-18T12:45:22Z",
      },
      {
        id: "lGSdNfpZR8m4m1Ib8dNE",
        amount_money: { amount: 1575, currency: "USD" },
        status: "COMPLETED",
        created_at: "2024-09-18T14:02:10Z",
      },
    ].slice(0, Number(limit));

    return this.normalizeRecords("square.payments", payments, "id", {
      endpoint: "https://connect.squareupsandbox.com/v2/payments",
    });
  }

  async pushData(payload: Record<string, unknown>): Promise<OperationResult> {
    return {
      success: true,
      message: "Payment created in Square sandbox.",
      raw: {
        payload,
        endpoint: "https://connect.squareupsandbox.com/v2/payments",
      },
    };
  }

  async registerWebhook(callbackUrl: string): Promise<WebhookRegistration> {
    return {
      id: "sandbox-square-webhook",
      status: "active",
      raw: {
        destination: callbackUrl,
        eventTypes: ["payment.updated", "payment.created"],
        endpoint: "https://connect.squareupsandbox.com/v2/webhooks",
      },
    };
  }

  async syncStatus(): Promise<SyncStatus> {
    return {
      status: "idle",
      lastSync: new Date().toISOString(),
      details: "Square sandbox synchronization completed successfully.",
    };
  }
}

const DOORDASH_DRIVE_SANDBOX_CREDENTIALS: SandboxCredentialSet = {
  label: "DoorDash Drive Sandbox",
  values: {
    developerId: process.env.DOORDASH_DRIVE_SANDBOX_DEVELOPER_ID ?? "SANDBOX-DEVELOPER-ID",
    keyId: process.env.DOORDASH_DRIVE_SANDBOX_KEY_ID ?? "SANDBOX-KEY-ID",
    signingSecret: process.env.DOORDASH_DRIVE_SANDBOX_SIGNING_SECRET ?? "SANDBOX-SIGNING-SECRET",
  },
};

export class DoorDashDriveConnector extends ConnectorBase {
  constructor() {
    super("DoorDash Drive", DOORDASH_DRIVE_SANDBOX_CREDENTIALS);
  }

  async authorize(): Promise<AuthorizationResult> {
    const token = Buffer.from(
      `${this.sandboxCredentials.values.developerId}:${this.sandboxCredentials.values.keyId}`,
    ).toString("base64");

    return {
      token,
      expiresAt: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
      raw: {
        token,
        developerId: this.sandboxCredentials.values.developerId,
      },
    };
  }

  async fetchData(params: Record<string, unknown> = {}): Promise<NormalizedResponse> {
    const { limit = 2 } = params;
    const deliveries = [
      {
        external_delivery_id: "dd-delivery-1001",
        status: "delivered",
        pickup_address: "123 Sandbox Way, San Francisco, CA",
        dropoff_address: "901 Market St, San Francisco, CA",
      },
      {
        external_delivery_id: "dd-delivery-1002",
        status: "picked_up",
        pickup_address: "501 Test Blvd, San Jose, CA",
        dropoff_address: "77 Geary St, San Francisco, CA",
      },
    ].slice(0, Number(limit));

    return this.normalizeRecords("doordash.drive.deliveries", deliveries, "external_delivery_id", {
      endpoint: "https://openapi.doordash.com/drive/v2/deliveries",
    });
  }

  async pushData(payload: Record<string, unknown>): Promise<OperationResult> {
    return {
      success: true,
      message: "Delivery created in DoorDash Drive sandbox.",
      raw: {
        payload,
        endpoint: "https://openapi.doordash.com/drive/v2/deliveries",
      },
    };
  }

  async registerWebhook(callbackUrl: string): Promise<WebhookRegistration> {
    return {
      id: "sandbox-doordash-drive-webhook",
      status: "active",
      raw: {
        destination: callbackUrl,
        eventTypes: ["delivery.update"],
        endpoint: "https://openapi.doordash.com/drive/v2/webhooks",
      },
    };
  }

  async syncStatus(): Promise<SyncStatus> {
    return {
      status: "idle",
      lastSync: new Date().toISOString(),
      details: "DoorDash Drive sandbox synchronization complete.",
    };
  }
}

const MARKETMAN_SANDBOX_CREDENTIALS: SandboxCredentialSet = {
  label: "MarketMan Sandbox",
  values: {
    username: process.env.MARKETMAN_SANDBOX_USERNAME ?? "sandbox-user",
    password: process.env.MARKETMAN_SANDBOX_PASSWORD ?? "sandbox-password",
    accountName: process.env.MARKETMAN_SANDBOX_ACCOUNT ?? "sandbox-account",
  },
};

export class MarketManConnector extends ConnectorBase {
  constructor() {
    super("MarketMan", MARKETMAN_SANDBOX_CREDENTIALS);
  }

  async authorize(): Promise<AuthorizationResult> {
    const token = Buffer.from(
      `${this.sandboxCredentials.values.username}:${this.sandboxCredentials.values.password}`,
    ).toString("base64");

    return {
      token,
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      raw: {
        accountName: this.sandboxCredentials.values.accountName,
        token,
      },
    };
  }

  async fetchData(params: Record<string, unknown> = {}): Promise<NormalizedResponse> {
    const { limit = 2 } = params;
    const purchaseOrders = [
      {
        DocumentNumber: "PO-2001",
        SupplierName: "Sandbox Farms",
        Status: "Approved",
        Total: 452.75,
      },
      {
        DocumentNumber: "PO-2002",
        SupplierName: "Demo Distributors",
        Status: "Pending",
        Total: 128.4,
      },
    ].slice(0, Number(limit));

    return this.normalizeRecords("marketman.purchase_orders", purchaseOrders, "DocumentNumber", {
      endpoint: "https://api.marketman.com/v3/rest/PurchaseOrders",
    });
  }

  async pushData(payload: Record<string, unknown>): Promise<OperationResult> {
    return {
      success: true,
      message: "Purchase order submitted to MarketMan sandbox.",
      raw: {
        payload,
        endpoint: "https://api.marketman.com/v3/rest/PurchaseOrders",
      },
    };
  }

  async registerWebhook(callbackUrl: string): Promise<WebhookRegistration> {
    return {
      id: "sandbox-marketman-webhook",
      status: "pending",
      raw: {
        destination: callbackUrl,
        eventTypes: ["purchaseOrder.updated"],
        endpoint: "https://api.marketman.com/v3/rest/Webhooks",
      },
    };
  }

  async syncStatus(): Promise<SyncStatus> {
    return {
      status: "running",
      lastSync: new Date().toISOString(),
      details: "MarketMan sandbox inventory sync is running in test mode.",
    };
  }
}

export const sandboxConnectors = {
  square: new SquareConnector(),
  doordashDrive: new DoorDashDriveConnector(),
  marketman: new MarketManConnector(),
};
