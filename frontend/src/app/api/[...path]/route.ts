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

/** Proxy request timeout in milliseconds (30 s). */
const PROXY_TIMEOUT_MS = 30_000;

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

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), PROXY_TIMEOUT_MS);

  try {
    const upstream = await fetch(target, {
      method: req.method,
      headers,
      body,
      // Always fetch fresh from the backend
      cache: "no-store",
      signal: controller.signal,
    });

    clearTimeout(timer);

    // 204 No Content must not have a body — return immediately to avoid
    // "Response constructor: Invalid response status code 204" from NextResponse.
    if (upstream.status === 204) {
      return new NextResponse(null, { status: 204 });
    }

    const data = await upstream.text();

    // Ensure the response body is valid JSON when Content-Type is application/json
    // (some FastAPI error responses return plain text with wrong content-type)
    const contentType = upstream.headers.get("Content-Type") ?? "application/json";
    let finalData = data;
    if (contentType.includes("application/json") || contentType.includes("text/plain")) {
      // Wrap plain-text error bodies in JSON so apiFetch can parse them
      try {
        JSON.parse(data); // check if already valid JSON
      } catch {
        finalData = JSON.stringify({ detail: data.trim() || `HTTP ${upstream.status}` });
      }
    }

    return new NextResponse(finalData, {
      status: upstream.status,
      headers: {
        "Content-Type": "application/json",
      },
    });
  } catch (err: unknown) {
    clearTimeout(timer);

    const isTimeout =
      err instanceof Error &&
      (err.name === "AbortError" || err.message.includes("abort"));

    if (isTimeout) {
      return NextResponse.json(
        { detail: "Backend request timed out after 30 seconds" },
        { status: 504 }
      );
    }

    const message =
      err instanceof Error ? err.message : "Unknown connection error";

    console.error(`[proxy] Failed to reach backend at ${target}: ${message}`);

    return NextResponse.json(
      {
        detail: "Backend service unreachable",
        hint: `Could not connect to ${BACKEND_URL}. Ensure BACKEND_URL is set and the backend is running.`,
      },
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
