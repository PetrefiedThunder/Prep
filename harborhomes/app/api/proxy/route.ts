import { NextResponse } from "next/server";

type HeadersObject = Record<string, string>;

function getNormalizedBase() {
  const base = process.env.NEXT_PUBLIC_API_BASE;
  if (!base) {
    throw new Error("NEXT_PUBLIC_API_BASE is not configured");
  }
  return base.endsWith("/") ? base.slice(0, -1) : base;
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const city = url.searchParams.get("city");

  if (!city) {
    return NextResponse.json({ error: "Missing required city parameter" }, { status: 400 });
  }

  let normalizedBase: string;
  try {
    normalizedBase = getNormalizedBase();
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unable to resolve compliance API";
    return NextResponse.json({ error: message }, { status: 500 });
  }

  const headers: HeadersObject = { Accept: "application/json" };
  const apiKey = process.env.COMPLIANCE_API_KEY;
  if (apiKey) {
    headers["x-api-key"] = apiKey;
  }

  const upstream = await fetch(`${normalizedBase}/city/${city}/fees`, {
    headers,
    next: { revalidate: 60 * 60 }
  });

  if (!upstream.ok) {
    const fallbackBody = await upstream.text();
    return NextResponse.json(
      { error: `Upstream request failed: ${fallbackBody || upstream.statusText}` },
      { status: upstream.status }
    );
  }

  const payload = await upstream.json();
  const response = NextResponse.json(payload);
  response.headers.set("Cache-Control", "s-maxage=3600, stale-while-revalidate=600");
  return response;
}
