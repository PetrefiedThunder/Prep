import express from "express";
import { z } from "zod";
import { createClient } from "redis";

const app = express();
app.use(express.json());

const redisUrl = process.env.REDIS_URL;
if (!redisUrl) {
  throw new Error("REDIS_URL environment variable must be set");
}

const redisClient = createClient({ url: redisUrl });

void (async () => {
  await redisClient.connect();
})();

const Flag = z.object({
  key: z.string(),
  state: z.enum(["on", "off"]),
  targeting: z.unknown().optional(),
  rollout: z
    .object({
      strategy: z.enum(["canary", "all", "none"]),
      percent: z.number().min(0).max(100),
    })
    .optional(),
  metrics_guard: z.string().optional(),
  ttl_sec: z.number().optional(),
  updated_by: z.string(),
});

app.get("/rcs/:key", async (req, res) => {
  const value = await redisClient.hGet("rcs", req.params.key);
  if (!value) {
    res.status(404).end();
    return;
  }

  res.json(JSON.parse(value));
});

app.post("/rcs", async (req, res) => {
  const flag = Flag.parse(req.body);
  const payload = JSON.stringify({ ...flag, ts: Date.now() });
  await redisClient.hSet("rcs", flag.key, payload);
  res.status(201).json({ ok: true });
});

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

const port = Number.parseInt(process.env.PORT ?? "8080", 10);
app.listen(port, () => {
  console.log(`control-plane up on ${port}`);
});
