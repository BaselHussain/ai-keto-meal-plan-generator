export async function register() {
  // Skip Sentry in development (Windows symlink permission issue with Turbopack)
  if (process.env.NODE_ENV === "development") return;

  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./sentry.server.config");
  }

  if (process.env.NEXT_RUNTIME === "edge") {
    await import("./sentry.edge.config");
  }
}

export async function onRequestError(...args: unknown[]) {
  if (process.env.NODE_ENV === "development") return;
  const { captureRequestError } = await import("@sentry/nextjs");
  // @ts-expect-error - dynamic import typing
  return captureRequestError(...args);
}
