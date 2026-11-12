import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { SearchBar } from "@/components/features/content/components/SearchBar";

describe("SearchBar", () => {
  it("shows the current search term", () => {
    render(<SearchBar searchTerm="malaria" setSearchTerm={() => {}} />);
    expect(
      screen.getByRole("searchbox", { name: "Search content" }),
    ).toHaveValue("malaria");
  });

  it("reports each change to the parent", async () => {
    const user = userEvent.setup();
    const setSearchTerm = vi.fn();
    render(<SearchBar searchTerm="" setSearchTerm={setSearchTerm} />);

    // The input is controlled by the parent, so each keystroke is reported
    // against the (unchanged) empty value.
    await user.type(screen.getByRole("searchbox"), "ab");
    expect(setSearchTerm).toHaveBeenNthCalledWith(1, "a");
    expect(setSearchTerm).toHaveBeenNthCalledWith(2, "b");
  });
});
