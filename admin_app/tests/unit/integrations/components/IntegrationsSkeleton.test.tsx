import { render, screen } from "@testing-library/react";

import { IntegrationsSkeleton } from "@/components/features/integrations/components/IntegrationsSkeleton";

describe("IntegrationsSkeleton", () => {
  it("announces one loading status and hides the placeholder shapes", () => {
    const { container } = render(<IntegrationsSkeleton />);
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(status).toHaveTextContent("Loading integrations");
    // Skeleton blocks render, but inside an aria-hidden wrapper.
    expect(
      container.querySelectorAll('[data-slot="skeleton"]').length,
    ).toBeGreaterThan(0);
    expect(container.querySelector('[aria-hidden="true"]')).toBeInTheDocument();
  });
});
