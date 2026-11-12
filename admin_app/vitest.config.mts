import { defineConfig, type Plugin } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Next turns `import logo from "./x.png"` into a StaticImageData object
// ({ src, width, height }), while plain Vite gives a URL string. Components
// read `.src`, so mirror Next's shape. Dimensions are placeholders.
const nextStaticImages = (): Plugin => ({
  name: "next-static-images",
  enforce: "pre",
  load(id) {
    if (!/\.(png|jpe?g|gif|webp|avif|svg)$/.test(id)) return null;
    const src = `/${path.relative(process.cwd(), id)}`;
    return `export default ${JSON.stringify({ src, width: 24, height: 24 })};`;
  },
});

// Unit tests only. Browser-driven integration tests live in tests/integration
// and run under Playwright (see playwright.config.ts).
export default defineConfig({
  // react() handles the JSX transform.
  plugins: [nextStaticImages(), react()],
  // Built-in replacement for vite-tsconfig-paths: resolves the "@/*" alias.
  resolve: { tsconfigPaths: true },
  test: {
    environment: "jsdom",
    include: ["tests/unit/**/*.test.{ts,tsx}"],
    setupFiles: ["./tests/unit/setup.ts"],
    // Lets tests call describe/it/expect without importing, and lets
    // Testing Library register its automatic cleanup.
    globals: true,
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      reportsDirectory: "./coverage",
      // Scope: the presentational child components of each feature, i.e.
      // anything under a feature's components/ folder. Wrappers, api.ts,
      // queries.ts and store.ts are wiring and belong to integration tests.
      include: ["src/components/features/**/components/**/*.{ts,tsx}"],
      exclude: ["**/assets/**", "**/.impeccable/**"],
      thresholds: {
        lines: 90,
        statements: 90,
        functions: 90,
        branches: 90,
      },
    },
  },
});
