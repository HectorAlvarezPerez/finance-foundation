import path from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

const currentDir = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  output: "standalone",
  transpilePackages: ["@finance-foundation/shared"],
  turbopack: {
    root: path.join(currentDir, "../.."),
  },
};

export default nextConfig;
