/**
 * Hey API codegen config: turns core_backend's OpenAPI spec (openapi.json,
 * refreshed with `pnpm api:spec`) into a typed client under src/client/.
 *
 * Run `pnpm api:generate` after changing the spec. Never edit src/client/ by
 * hand: it is overwritten on every run. It is committed so API changes show up
 * in code review.
 */
import { defineConfig } from "@hey-api/openapi-ts";

import { EXCLUDED_OPERATIONS } from "./scripts/api-scope.mjs";

export default defineConfig({
  input: "./openapi.json",
  output: "src/client",
  parser: {
    // Only generate what the admin app uses; the BFF allowlist uses the same list.
    filters: { operations: { exclude: EXCLUDED_OPERATIONS } },
  },
  plugins: [
    {
      name: "@hey-api/client-fetch",
      // Sets baseUrl "/bff" and the auth/error interceptors at startup.
      runtimeConfigPath: "./src/lib/api/client-config",
      // SDK calls throw on failure (and their types say so: `data` is never
      // undefined). TanStack Query expects thrown errors.
      throwOnError: true,
    },
    "@hey-api/typescript",
    "@hey-api/sdk",
    "@tanstack/react-query",
  ],
});
