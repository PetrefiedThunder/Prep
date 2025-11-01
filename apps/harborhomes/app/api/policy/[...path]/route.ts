import type { NextRequest } from 'next/server';

const API_BASE = process.env.PREP_API_BASE ?? process.env.NEXT_PUBLIC_API_BASE;
const API_KEY = process.env.PREP_API_KEY;

const sanitizeBase = (value: string) => value.replace(/\/+$/, '');

const buildTargetUrl = (segments: string[] | undefined, search: string) => {
  const path = (segments ?? []).join('/');
  const base = sanitizeBase(API_BASE!);
  const url = new URL(path, `${base}/`);
  if (search) {
    url.search = search;
  }
  return url.toString();
};

const createHeaders = (request: NextRequest) => {
  const headers = new Headers(request.headers);
  headers.set('Accept', 'application/json');
  headers.set('User-Agent', 'HarborHomesPolicyProxy/1.0');
  headers.delete('host');
  headers.delete('content-length');
  if (API_KEY) {
    headers.set('Authorization', `Bearer ${API_KEY}`);
  }
  return headers;
};

const proxy = async (request: NextRequest, segments: string[] | undefined) => {
  if (!API_BASE) {
    return Response.json(
      { error: 'API base URL is not configured. Set PREP_API_BASE or NEXT_PUBLIC_API_BASE.' },
      { status: 500 }
    );
  }

  const target = buildTargetUrl(segments, request.nextUrl.search);
  const headers = createHeaders(request);
  const method = request.method.toUpperCase();
  const body = method === 'GET' || method === 'HEAD' ? undefined : await request.arrayBuffer();

  try {
    const upstream = await fetch(target, {
      method,
      headers,
      body,
      cache: 'no-store',
    });

    const responseHeaders = new Headers(upstream.headers);
    responseHeaders.set('Access-Control-Allow-Origin', '*');
    responseHeaders.delete('content-encoding');
    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error('Policy proxy request failed', error);
    return Response.json(
      { error: 'Upstream request failed', detail: error instanceof Error ? error.message : String(error) },
      { status: 502 }
    );
  }
};

export const GET = (request: NextRequest, { params }: { params: { path?: string[] } }) => proxy(request, params.path);
export const POST = (request: NextRequest, { params }: { params: { path?: string[] } }) => proxy(request, params.path);
export const PUT = (request: NextRequest, { params }: { params: { path?: string[] } }) => proxy(request, params.path);
export const PATCH = (request: NextRequest, { params }: { params: { path?: string[] } }) => proxy(request, params.path);
export const DELETE = (request: NextRequest, { params }: { params: { path?: string[] } }) => proxy(request, params.path);
