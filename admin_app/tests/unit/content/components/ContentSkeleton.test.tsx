import { render, screen } from "@testing-library/react";

import { ContentSkeleton } from "@/components/features/content/components/ContentSkeleton";

describe("ContentSkeleton", () => {
  it("announces one loading status and hides the placeholder shapes", () => {
    const { container } = render(<ContentSkeleton />);
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(status).toHaveTextContent("Loading content");
    // Skeleton blocks render, but inside an aria-hidden wrapper.
    expect(
      container.querySelectorAll('[data-slot="skeleton"]').length,
    ).toBeGreaterThan(0);
    expect(container.querySelector('[aria-hidden="true"]')).toBeInTheDocument();
  });
});
