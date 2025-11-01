import { NextResponse } from "next/server";

import { buildComplianceHeaders, resolveComplianceBase } from "@/lib/compliance";

interface RouteContext {
  params: {
    path?: string[];
  };
}

export async function GET(request: Request, context: RouteContext) {
  const pathSegments = context.params.path?.filter(Boolean) ?? [];
  if (pathSegments.length === 0) {
    return NextResponse.json({ error: "Missing upstream path" }, { status: 400 });
  }

  let normalizedBase: string;
  try {
    normalizedBase = resolveComplianceBase();
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unable to resolve compliance API";
    return NextResponse.json({ error: message }, { status: 500 });
  }

  const url = new URL(request.url);
  const upstreamUrl = `${normalizedBase}/${pathSegments.join("/")}${url.search}`;

  const headers = buildComplianceHeaders();
  const upstream = await fetch(upstreamUrl, {
    method: "GET",
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
