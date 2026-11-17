/**
 * Which core_backend operations the admin app may use.
 *
 * Shared by openapi-ts.config.ts (what gets a generated SDK function) and
 * scripts/generate-bff-routes.mjs (what the /bff proxy will forward), so the
 * typed client and the BFF allowlist can never drift apart.
 *
 * Format is Hey API's operation filter: "METHOD /path", or a /regex/ string.
 * Excluded below are endpoints meant for external integrations (API-key only)
 * or infrastructure, which the admin UI never calls.
 */
export const EXCLUDED_OPERATIONS = [
  "/^[A-Z]+ \\/data-api\\//", // data export API for partners
  "/^[A-Z]+ \\/voice-/", // voice search/chat (speech integrations)
  "/^[A-Z]+ \\/content-feedback$/", // end-user feedback via chat managers
  "/^[A-Z]+ \\/healthcheck$/", // container health probe
];

/** Turn the filter strings above into RegExp/exact matchers. */
export const isExcluded = (method, path) => {
  const key = `${method.toUpperCase()} ${path}`;
  return EXCLUDED_OPERATIONS.some((filter) =>
    filter.startsWith("/") && filter.endsWith("/")
      ? new RegExp(filter.slice(1, -1)).test(key)
      : filter === key,
  );
};
