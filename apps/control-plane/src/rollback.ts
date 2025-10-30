import axios from "axios";
import { createClient } from "redis";

type RcsFlag = {
  key: string;
  state: "on" | "off";
  metrics_guard?: string;
  updated_by?: string;
};

const redisUrl = process.env.REDIS_URL;
const promUrl = process.env.PROM_URL;

if (!redisUrl) {
  throw new Error("REDIS_URL environment variable must be set");
}
if (!promUrl) {
  throw new Error("PROM_URL environment variable must be set");
}

const redisClient = createClient({ url: redisUrl });

async function connectRedis() {
  if (!redisClient.isOpen) {
    await redisClient.connect();
  }
}

async function breaching(guardExpr: string): Promise<boolean> {
  const promQuery = guardExpr
    .replace(
      /pricing_conversion_drop/g,
      "(1 - sum(rate(pricing_conversion[5m])) by ())"
    )
    .replace(
      /api_p95_ms/g,
      "histogram_quantile(0.95, sum(rate(http_request_duration_ms_bucket[5m])) by (le))"
    );

  const { data } = await axios.get(promUrl, { params: { query: promQuery } });
  const results = (data?.data?.result ?? []) as Array<{ value: [number, string] }>;
  return results.some((row) => Number(row.value[1]) > 1);
}

async function guardScan() {
  await connectRedis();
  const all = await redisClient.hGetAll("rcs");
  await Promise.all(
    Object.entries(all).map(async ([key, raw]) => {
      const flag = JSON.parse(raw) as RcsFlag;
      if (!flag.metrics_guard) {
        return;
      }

      const violating = await breaching(flag.metrics_guard);
      if (violating && flag.state === "on") {
        const next = {
          ...flag,
          state: "off" as const,
          updated_by: "rollbacker",
          ts: Date.now(),
        };
        await redisClient.hSet("rcs", key, JSON.stringify(next));
        await redisClient.xAdd("audit.events", "*", { type: "rollback", key });
      }
    })
  );
}

void (async () => {
  await connectRedis();
  setInterval(() => {
    void guardScan().catch((err) => {
      console.error("guard scan failed", err);
    });
  }, 30_000);
})();
