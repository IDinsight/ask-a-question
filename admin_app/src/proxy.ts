import { NextResponse, type NextRequest } from "next/server";

import { SESSION_COOKIE } from "@/utils/sessionCookie";

/**
 * Send signed-out users to /login before a protected page renders.
 *
 * Signed-in state comes from the marker cookie that AuthProvider keeps in sync
 * with the token in localStorage (see src/utils/sessionCookie.ts). This is a
 * UX redirect, not the security boundary: the backend checks the bearer token
 * on every /bff call, and ProtectedComponent still guards on the client.
 *
 * The original path (and query) goes along as `sourcePage`, the same
 * parameter ProtectedComponent uses, so login returns the user where they were.
 */
export function proxy(request: NextRequest) {
  if (request.cookies.has(SESSION_COOKIE)) return NextResponse.next();

  const { pathname, search } = request.nextUrl;
  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("sourcePage", `${pathname}${search}`);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: [
    // Every page except the public auth pages, the BFF (the backend answers
    // 401 itself), Next.js internals and any file with an extension
    // (favicon, images and other public/ assets).
    "/((?!login|reset-password|bff|_next/static|_next/image|.*\\..*).*)",
  ],
};
