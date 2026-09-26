import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";

// When set, /api/* is proxied to the FastAPI service so the browser sees the
// API as same-origin. Session cookies then stay first-party, which Safari and
// other third-party-cookie-blocking browsers require. Pair it with
// NEXT_PUBLIC_API_URL=/api.
const apiProxyTarget = process.env.API_PROXY_TARGET?.replace(/\/$/, "");

const nextConfig = (phase: string): NextConfig => ({
  // Keep production builds from overwriting a running dev server's chunks.
  distDir: phase === PHASE_DEVELOPMENT_SERVER ? ".next-dev" : ".next",
  output: "standalone",
  async rewrites() {
    return apiProxyTarget
      ? [{ source: "/api/:path*", destination: `${apiProxyTarget}/:path*` }]
      : [];
  },
});

export default nextConfig;
