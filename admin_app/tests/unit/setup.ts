// Types for the describe/it/expect globals enabled in vitest.config.mts.
/// <reference types="vitest/globals" />

// Adds DOM matchers (toBeInTheDocument, toHaveTextContent, ...) to Vitest's expect.
import "@testing-library/jest-dom/vitest";

// ---------------------------------------------------------------------------
// jsdom gaps. jsdom doesn't implement layout or a few browser APIs that
// Base UI, recharts and our components touch. These are inert stand-ins:
// tests that care about the behaviour should spy on or override them.
// ---------------------------------------------------------------------------

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??=
  ResizeObserverStub as unknown as typeof ResizeObserver;

class IntersectionObserverStub {
  root = null;
  rootMargin = "";
  thresholds = [];
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return [];
  }
}
globalThis.IntersectionObserver ??=
  IntersectionObserverStub as unknown as typeof IntersectionObserver;

// Server-side tests (`// @vitest-environment node`, e.g. the BFF proxy) have no
// DOM, so the browser stand-ins below only apply under jsdom.
const isBrowser = typeof window !== "undefined";

if (isBrowser && !window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList;
}

if (isBrowser) {
  // Used by scroll-into-view behaviour in menus/lists.
  Element.prototype.scrollIntoView ??= () => {};

  // Pointer capture is used by Base UI sliders/menus.
  Element.prototype.hasPointerCapture ??= () => false;
  Element.prototype.setPointerCapture ??= () => {};
  Element.prototype.releasePointerCapture ??= () => {};
}

// Used by file downloads (DownloadModal). Tests can spy on these.
URL.createObjectURL ??= () => "blob:mock";
URL.revokeObjectURL ??= () => {};
