import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_DEMO: process.env.NEXT_PUBLIC_DEMO ?? "1",
  },
};

export default nextConfig;
