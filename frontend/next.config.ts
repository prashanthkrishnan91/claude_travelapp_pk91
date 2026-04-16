import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // API calls go through the catch-all Route Handler at
  // src/app/api/[...path]/route.ts which proxies to the FastAPI backend.
  // No rewrites needed — the Route Handler is the proxy.
};

export default nextConfig;
