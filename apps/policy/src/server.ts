import express from "express";
import axios from "axios";

const app = express();
app.use(express.json());

const opaUrl = process.env.OPA_URL;
if (!opaUrl) {
  throw new Error("OPA_URL environment variable must be set");
}

app.post("/policy/evaluate", async (req, res) => {
  const { data } = await axios.post(`${opaUrl}/v1/data/prep/policy`, req.body);
  res.json(data.result);
});

const port = Number.parseInt(process.env.PORT ?? "8081", 10);
app.listen(port, () => {
  console.log(`policy api listening on ${port}`);
});
