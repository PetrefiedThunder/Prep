import { NextRequest } from "next/server";
const API = process.env.NEXT_PUBLIC_API_BASE!;
const KEY = process.env.PREP_API_KEY || "";
export async function GET(req: NextRequest, { params }: { params: { path: string[] } }) {
  const url = `${API}/${params.path.join("/")}${req.nextUrl.search}`;
  const r = await fetch(url, { headers: KEY ? { "X-API-Key": KEY } : {}, cache: "no-store" });
  return new Response(await r.text(), { status: r.status, headers: { "content-type": r.headers.get("content-type") || "application/json" } });
}
