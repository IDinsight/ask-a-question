/**
 * BFF entry point: every /bff/* request from the browser lands here and is
 * forwarded to core_backend by proxyToBackend (allowlist, logging, request IDs,
 * timeouts). See src/lib/bff/server.ts.
 */
import { proxyToBackend } from "@/lib/bff/server";

const handler = (request: Request) => proxyToBackend(request);

export { handler as GET, handler as POST, handler as PUT, handler as PATCH };
export { handler as DELETE, handler as HEAD };
