import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a self-contained server bundle so the Docker image ships only the
  // files actually needed at runtime instead of the whole node_modules tree.
  output: "standalone",
};

export default nextConfig;
