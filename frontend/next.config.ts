import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* Proxy API calls to FastAPI backend during development */
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination:
          process.env.NEXT_PUBLIC_API_URL
            ? `${process.env.NEXT_PUBLIC_API_URL}/:path*`
            : "http://localhost:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
