import type { CreateClientConfig } from "@/client/client.gen";
import { getFreshAccessToken } from "@/lib/api/session";

/**
 * Initial config for the generated API client (src/client). Hey API calls this
 * once when the client is created (see `runtimeConfigPath` in
 * openapi-ts.config.ts).
 *
 * - baseUrl "/bff": the browser never calls core_backend directly; every call
 *   goes through the Next.js BFF on the same origin (src/app/bff).
 * - auth: the user's access token from ./session.ts, refreshed first when it is
 *   about to expire. Hey API calls this (and attaches the token) only for
 *   operations the spec marks as secured. Both of the backend's schemes (OAuth2
 *   password bearer for users, HTTP bearer on /search, /chat, ...) accept the
 *   user's JWT, so one token covers both.
 * (throwOnError is set in openapi-ts.config.ts, so the generated types know
 * SDK calls throw. Interceptors in ./interceptors.ts shape the error.)
 *
 * Must not import ./interceptors or the generated client (circular import).
 * ./session.ts only imports generated types, which is safe.
 */
export const createClientConfig: CreateClientConfig = (config) => ({
  ...config,
  baseUrl: "/bff",
  auth: () => getFreshAccessToken(),
});
