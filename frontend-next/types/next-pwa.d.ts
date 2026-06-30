declare module "next-pwa" {
  import type { NextConfig } from "next";

  export interface NextPWAOptions {
    dest?: string;
    register?: boolean;
    skipWaiting?: boolean;
    disable?: boolean;
    runtimeCaching?: unknown[];
    [key: string]: unknown;
  }

  export default function withPWA(options?: NextPWAOptions): (
    nextConfig: NextConfig
  ) => NextConfig;
}
