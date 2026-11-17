import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { SortableTableHeader } from "@/components/features/dashboard/components/performance/SortableTableHeader";

type Col = "a" | "b";

// TableHead renders a <th>, which needs a table row around it.
const renderHeader = (props: {
  sortColumn: Col;
  sortOrder: "ascending" | "descending";
  onSort?: (c: Col) => void;
}) =>
  render(
    <table>
      <thead>
        <tr>
          <SortableTableHeader<Col>
            label="Upvotes"
            columnKey="a"
            onSort={props.onSort ?? (() => {})}
            sortColumn={props.sortColumn}
            sortOrder={props.sortOrder}
          />
        </tr>
      </thead>
    </table>,
  );

describe("SortableTableHeader", () => {
  it("marks an inactive column as unsorted", () => {
    renderHeader({ sortColumn: "b", sortOrder: "ascending" });
    expect(screen.getByRole("columnheader")).toHaveAttribute(
      "aria-sort",
      "none",
    );
  });

  it.each(["ascending", "descending"] as const)(
    "reports %s on the active column",
    (order) => {
      renderHeader({ sortColumn: "a", sortOrder: order });
      expect(screen.getByRole("columnheader")).toHaveAttribute(
        "aria-sort",
        order,
      );
    },
  );

  it("asks to sort by its column when clicked", async () => {
    const user = userEvent.setup();
    const onSort = vi.fn();
    renderHeader({ sortColumn: "b", sortOrder: "descending", onSort });

    await user.click(screen.getByRole("button", { name: "Upvotes" }));
    expect(onSort).toHaveBeenCalledWith("a");
  });
});
