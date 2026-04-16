/**
 * Proxy removed — frontend calls FastAPI backend directly via NEXT_PUBLIC_API_URL.
 * This file is intentionally left as a stub so Next.js doesn't error on import.
 */
import { NextResponse } from "next/server";

export function GET() {
  return NextResponse.json({ detail: "Proxy disabled. Call the backend directly." }, { status: 410 });
}
