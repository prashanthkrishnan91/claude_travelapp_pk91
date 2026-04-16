/**
 * Catch-all proxy Route Handler.
 *
 * Forwards every /api/<anything> request to the FastAPI backend so that:
 *  - Client components can use a relative /api base URL (works in any browser).
 *  - Server components can call an absolute internal URL (avoids localhost 502s
 *    on Vercel serverless).
 *
 * Required env var (server-only, not NEXT_PUBLIC_):
 *   BACKEND_URL=https://your-railway-backend.up.railway.app
 *
 * Defaults to http://localhost:8000 for local development.
 */

import { type NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

const FORWARDED_HEADERS = ["content-type", "x-user-id", "authorization"];

async function proxy(
  req: NextRequest,
  params: Promise<{ path: string[] }>
): Promise<NextResponse> {
  const { path } = await params;
  const segment = path.join("/");
  const { search } = new URL(req.url);
  const target = `${BACKEND_URL}/${segment}${search}`;

  const headers = new Headers();
  for (const key of FORWARDED_HEADERS) {
    const val = req.headers.get(key);
    if (val) headers.set(key, val);
  }

  const body =
    req.method !== "GET" && req.method !== "HEAD"
      ? await req.text()
      : undefined;

  try {
    const upstream = await fetch(target, {
      method: req.method,
      headers,
      body,
      // Always fetch fresh from the backend
      cache: "no-store",
    });

    const data = await upstream.text();
    return new NextResponse(data, {
      status: upstream.status,
      headers: {
        "Content-Type":
          upstream.headers.get("Content-Type") ?? "application/json",
      },
    });
  } catch {
    return NextResponse.json(
      { detail: "Backend service unreachable" },
      { status: 502 }
    );
  }
}

type RouteContext = { params: Promise<{ path: string[] }> };

export const GET = (req: NextRequest, ctx: RouteContext) =>
  proxy(req, ctx.params);
export const POST = (req: NextRequest, ctx: RouteContext) =>
  proxy(req, ctx.params);
export const PATCH = (req: NextRequest, ctx: RouteContext) =>
  proxy(req, ctx.params);
export const PUT = (req: NextRequest, ctx: RouteContext) =>
  proxy(req, ctx.params);
export const DELETE = (req: NextRequest, ctx: RouteContext) =>
  proxy(req, ctx.params);
