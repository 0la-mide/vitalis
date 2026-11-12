import type { NextConfig } from "next";

const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  // No floating "N" dev button.
  devIndicators: false,
  // Dev only: let phones on the same Wi-Fi open the dev server by LAN IP (e.g. http://192.168.x.x:3000).
  allowedDevOrigins: ["192.168.*.*", "10.*.*.*", "172.*.*.*", "*.local"],
  poweredByHeader: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  // Same-origin API: in production nginx routes /api to the backend; in dev Next proxies it.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` }];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Permissions-Policy", value: "geolocation=(self), camera=(self), microphone=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
