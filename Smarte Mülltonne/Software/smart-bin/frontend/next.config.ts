import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  experimental: {
    webpackBuildWorker: false,
  },
};

export default nextConfig;
