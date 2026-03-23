import { withSentryConfig } from "@sentry/nextjs";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Prevent Turbopack from bundling these packages — they use native symlinks
  // which require Windows Developer Mode. Marking as external avoids the issue.
  serverExternalPackages: [
    "require-in-the-middle",
    "import-in-the-middle",
    "@opentelemetry/instrumentation",
    "@sentry/nextjs",
    "@sentry/node",
  ],
};

const sentryConfig = {
  org: "baselhussain",
  project: "keto-meal-plan-ai-product",
  silent: !process.env.CI,
  widenClientFileUpload: true,
  webpack: {
    automaticVercelMonitors: true,
    treeshake: { removeDebugLogging: true },
  },
};

// Skip Sentry wrapping in development to avoid Windows symlink permission issues.
// Sentry instrumentation is guarded in instrumentation.ts as well.
export default process.env.NODE_ENV === "production"
  ? withSentryConfig(nextConfig, sentryConfig)
  : nextConfig;
