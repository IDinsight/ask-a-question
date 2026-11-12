import { render, screen } from "@testing-library/react";

import { ContentEditSkeleton } from "@/components/features/content/edit/components/ContentEditSkeleton";

describe("ContentEditSkeleton", () => {
  it("announces one loading status and hides the placeholder shapes", () => {
    const { container } = render(<ContentEditSkeleton />);
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(status).toHaveTextContent("Loading content editor");
    // Skeleton blocks render, but inside an aria-hidden wrapper.
    expect(
      container.querySelectorAll('[data-slot="skeleton"]').length,
    ).toBeGreaterThan(0);
    expect(container.querySelector('[aria-hidden="true"]')).toBeInTheDocument();
  });
});
