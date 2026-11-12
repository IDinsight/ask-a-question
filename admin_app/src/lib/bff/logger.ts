import "server-only";

/**
 * Minimal structured logger for the BFF (server side only).
 *
 * Writes one JSON object per line to stdout/stderr, which Docker's json-file
 * driver (and any log shipper reading it) can parse without extra config.
 *
 * Data-handling rule: callers must never pass tokens, request/response bodies,
 * or user identifiers (usernames, emails) as fields. Log route templates such
 * as "/user/[user]", not concrete paths.
 */

type Level = "debug" | "info" | "warn" | "error";

const LEVEL_ORDER: Record<Level, number> = { debug: 10, info: 20, warn: 30, error: 40 };

/** Minimum level to emit; set LOG_LEVEL=debug|info|warn|error. Defaults to info. */
const minLevel = (): number => {
  const configured = (process.env.LOG_LEVEL ?? "info").toLowerCase() as Level;
  return LEVEL_ORDER[configured] ?? LEVEL_ORDER.info;
};

const write = (level: Level, event: string, fields: Record<string, unknown>) => {
  if (LEVEL_ORDER[level] < minLevel()) return;
  const line = JSON.stringify({
    ts: new Date().toISOString(),
    level,
    service: "admin_app.bff",
    event,
    ...fields,
  });
  // warn/error go to stderr so they can be filtered or alerted on separately.
  if (level === "error" || level === "warn") console.error(line);
  else console.log(line);
};

export const logger = {
  debug: (event: string, fields: Record<string, unknown> = {}) =>
    write("debug", event, fields),
  info: (event: string, fields: Record<string, unknown> = {}) =>
    write("info", event, fields),
  warn: (event: string, fields: Record<string, unknown> = {}) =>
    write("warn", event, fields),
  error: (event: string, fields: Record<string, unknown> = {}) =>
    write("error", event, fields),
};
