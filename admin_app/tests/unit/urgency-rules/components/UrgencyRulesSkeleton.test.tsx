import { render, screen } from "@testing-library/react";

import { UrgencyRulesSkeleton } from "@/components/features/urgency-rules/components/UrgencyRulesSkeleton";

describe("UrgencyRulesSkeleton", () => {
  it("announces one loading status and hides the placeholder shapes", () => {
    const { container } = render(<UrgencyRulesSkeleton />);
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(status).toHaveTextContent("Loading urgency rules");
    // Skeleton blocks render, but inside an aria-hidden wrapper.
    expect(
      container.querySelectorAll('[data-slot="skeleton"]').length,
    ).toBeGreaterThan(0);
    expect(container.querySelector('[aria-hidden="true"]')).toBeInTheDocument();
  });
});
