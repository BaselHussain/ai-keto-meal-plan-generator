// This file configures the initialization of Sentry on the client.
// Sentry is skipped in development to avoid Windows Turbopack symlink issues
// (import-in-the-middle requires symlink creation, needs Developer Mode on Windows).

if (process.env.NODE_ENV !== "development") {
  import("@sentry/nextjs").then((Sentry) => {
    Sentry.init({
      dsn: "https://1d5f171d32d79bffc4d746e5b1b43e83@o4510639566749696.ingest.de.sentry.io/4510639621472336",
      integrations: [Sentry.replayIntegration()],
      tracesSampleRate: 1,
      enableLogs: true,
      replaysSessionSampleRate: 0.1,
      replaysOnErrorSampleRate: 1.0,
      sendDefaultPii: true,
    });
  });
}

export async function onRouterTransitionStart(...args: unknown[]) {
  if (process.env.NODE_ENV === "development") return;
  const Sentry = await import("@sentry/nextjs");
  // @ts-expect-error - dynamic import typing
  return Sentry.captureRouterTransitionStart(...args);
}
