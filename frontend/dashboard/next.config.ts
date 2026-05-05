import type { NextConfig } from "next";

const configuredApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
const proxyTarget =
  process.env.PARKRESERVE_API_PROXY_TARGET ??
  (configuredApiBaseUrl?.startsWith("http") ? configuredApiBaseUrl : undefined) ??
  "https://parkreserve-ai-production.up.railway.app";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${proxyTarget}/:path*`,
      },
    ];
  },
};

export default nextConfig;
