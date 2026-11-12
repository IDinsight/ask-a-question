import { NextRequest } from "next/server";
import {
  getRedirectUrl,
  unstable_doesMiddlewareMatch,
} from "next/experimental/testing/server";

import { config, proxy } from "@/proxy";
import { SESSION_COOKIE } from "@/utils/sessionCookie";

// unstable_doesMiddlewareMatch is the installed name of the helper the Next 16
// docs call unstable_doesProxyMatch; it checks the matcher only.
const matches = (url: string) => unstable_doesMiddlewareMatch({ config, url });

describe("proxy matcher", () => {
  it.each([
    "/",
    "/content",
    "/content/edit",
    "/dashboard",
    "/workspace-management",
    "/nope",
  ])("runs on page %s", (url) => expect(matches(url)).toBe(true));

  it.each([
    "/login",
    "/reset-password",
    "/bff/content/",
    "/_next/static/chunk.js",
    "/_next/image",
    "/favicon.ico",
    "/logo.png",
  ])("skips %s", (url) => expect(matches(url)).toBe(false));
});

describe("proxy", () => {
  it("redirects a signed-out request to /login with the source page", () => {
    const response = proxy(
      new NextRequest("http://localhost:3000/content/edit?content_id=5"),
    );
    const redirect = new URL(getRedirectUrl(response)!);
    expect(redirect.pathname).toBe("/login");
    expect(redirect.searchParams.get("sourcePage")).toBe(
      "/content/edit?content_id=5",
    );
  });

  it("lets a request with the signed-in marker through", () => {
    const request = new NextRequest("http://localhost:3000/content", {
      headers: { cookie: `${SESSION_COOKIE}=1` },
    });
    expect(getRedirectUrl(proxy(request))).toBeNull();
  });
});
