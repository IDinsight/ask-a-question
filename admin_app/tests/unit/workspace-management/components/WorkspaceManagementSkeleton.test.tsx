import { render, screen } from "@testing-library/react";

import { WorkspaceManagementSkeleton } from "@/components/features/workspace-management/components/WorkspaceManagementSkeleton";

describe("WorkspaceManagementSkeleton", () => {
  it("announces one loading status and hides the placeholder shapes", () => {
    const { container } = render(<WorkspaceManagementSkeleton />);
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(status).toHaveTextContent("Loading workspace");
    // Skeleton blocks render, but inside an aria-hidden wrapper.
    expect(
      container.querySelectorAll('[data-slot="skeleton"]').length,
    ).toBeGreaterThan(0);
    expect(container.querySelector('[aria-hidden="true"]')).toBeInTheDocument();
  });
});
