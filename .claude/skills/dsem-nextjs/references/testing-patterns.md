# Next.js Testing Patterns

Use these patterns for the Next.js App Router structure described in the skill.

## Tooling Split

Choose the right tool for each test target:

| What to test | Tool |
|---|---|
| Synchronous Server Components | Vitest + React Testing Library |
| Client Components | Vitest + React Testing Library |
| `lib/api/client.ts` functions | Vitest (mock `fetch`) |
| Server Action business logic (isolated) | Vitest |
| Async Server Components | **Playwright E2E only** |
| Full route rendering with real server data | **Playwright E2E only** |
| Critical mutations end-to-end | **Playwright E2E only** |
| `proxy.ts` matcher logic | `unstable_doesProxyMatch` (experimental, v15.1+) |

**Key constraint from Next.js docs:** Vitest and Jest do not support `async` Server Components. Use Playwright for any route that fetches data server-side.

## Setup Assumptions

- Use Vitest + React Testing Library for component and unit tests.
- Use Playwright for E2E and async Server Component tests.
- Mock `@/lib/api/client` (or `@/lib/api`) in feature wrapper tests.
- Mock `@/lib/actions` (Server Actions) in form component tests.
- Mock `fetch` only in `lib/api/client.ts` tests.

## Child Component Tests

Child components in `components/[feature]/` should be presentational.

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HouseholdsTable } from "@/components/households/households-table";

describe("HouseholdsTable", () => {
  it("renders households and calls the selected handler", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();

    render(
      <HouseholdsTable
        households={[{ id: "hh_1", name: "Amina Household" }]}
        onSelect={onSelect}
      />,
    );

    await user.click(screen.getByRole("button", { name: /amina household/i }));

    expect(onSelect).toHaveBeenCalledWith("hh_1");
  });
});
```

## Feature Wrapper Tests

Feature wrappers own state and call API functions or Server Actions.

### Fetching data

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { HouseholdsPage } from "@/components/households/households-page";
import * as api from "@/lib/api/client";

vi.mock("@/lib/api/client");

describe("HouseholdsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads and renders households", async () => {
    vi.mocked(api.listHouseholds).mockResolvedValue([
      { id: "hh_1", name: "Amina Household" },
    ]);

    render(<HouseholdsPage />);

    await waitFor(() => {
      expect(screen.getByText("Amina Household")).toBeInTheDocument();
    });

    expect(api.listHouseholds).toHaveBeenCalledTimes(1);
  });
});
```

### Form mutation with a Server Action

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HouseholdForm } from "@/components/households/household-form";
import { createHousehold } from "@/lib/actions";

vi.mock("@/lib/actions");

describe("HouseholdForm", () => {
  it("calls createHousehold on submit", async () => {
    const user = userEvent.setup();
    vi.mocked(createHousehold).mockResolvedValue(undefined);

    render(<HouseholdForm />);
    await user.type(screen.getByLabelText(/name/i), "Test Household");
    await user.click(screen.getByRole("button", { name: /create/i }));

    expect(createHousehold).toHaveBeenCalledTimes(1);
  });
});
```

## API Client Tests

`lib/api/client.ts` tests mock `fetch` directly. Assert URL construction, auth headers, response parsing, and error handling.

```ts
import { listHouseholds } from "@/lib/api/client";

describe("listHouseholds", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns households from the API response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          items: [{ id: "hh_1", name: "Amina Household" }],
        }),
      }),
    );

    await expect(listHouseholds()).resolves.toEqual([
      { id: "hh_1", name: "Amina Household" },
    ]);
  });

  it("throws on non-ok responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
      }),
    );

    await expect(listHouseholds()).rejects.toThrow("Failed to load households");
  });
});
```

## Playwright E2E Tests

Use Playwright for routes that fetch data server-side and for critical mutation flows.

```ts
// tests/households.spec.ts
import { test, expect } from "@playwright/test";

test("households page renders server-fetched data", async ({ page }) => {
  await page.goto("/households");
  // Data rendered by an async Server Component — no client hydration delay needed
  await expect(page.getByRole("heading", { name: /households/i })).toBeVisible();
  await expect(page.getByRole("table")).toBeVisible();
});

test("creating a household updates the list", async ({ page }) => {
  await page.goto("/households");
  await page.getByRole("button", { name: /add household/i }).click();
  await page.getByLabel(/name/i).fill("New Household");
  await page.getByRole("button", { name: /create/i }).click();
  await expect(page.getByText("New Household")).toBeVisible();
});

test("not-found state renders for unknown household", async ({ page }) => {
  await page.goto("/households/nonexistent-id");
  await expect(page.getByRole("heading", { name: /not found/i })).toBeVisible();
});
```

Run against the production build for accuracy:

```bash
next build && next start &
npx playwright test
```

Or configure `webServer` in `playwright.config.ts` to automate build-and-start.

## Anti-Patterns

- Do not put tests under `app/[feature]/` just because the route lives there.
- Do not mock `fetch` in feature wrapper tests — mock `@/lib/api/client` instead.
- Do not test shadcn primitives in `components/ui/`.
- Do not move `lib/api/server.ts` into a route folder for test convenience.
- Do not write Vitest tests for `async` Server Components — they do not run against a real server environment and will fail or silently produce incorrect results.
- Do not test Server Actions by calling them directly from Vitest with live database state — use Playwright against a test environment or a dedicated integration test setup with a test database.
- Do not mock `next/navigation` (`redirect`, `notFound`, `forbidden`) unless the test is specifically about routing behavior — prefer Playwright for navigation assertions.
- Do not write `proxy.ts` matcher tests with manual URL string comparisons — use `unstable_doesProxyMatch` from `next/experimental/testing/server` (experimental, v15.1+).

---

## Authoritative References

- [Next.js — Testing with Vitest](https://nextjs.org/docs/app/guides/testing/vitest) — documents that Vitest does not support async Server Components
- [Next.js — Testing with Playwright](https://nextjs.org/docs/app/guides/testing/playwright)
- [Next.js — Testing overview](https://nextjs.org/docs/app/guides/testing)
- [Vitest documentation](https://vitest.dev/)
- [Playwright documentation](https://playwright.dev/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [`@testing-library/user-event`](https://testing-library.com/docs/user-event/intro/)
