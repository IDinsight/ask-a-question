import { render, screen } from "@testing-library/react";
import { format } from "date-fns";

import HeatMap from "@/components/features/dashboard/components/overview/HeatMap";

// Same conversion as the component: a UTC "HH:mm" block shown in local time.
// Computed here so the test passes in any timezone.
const localTime = (time: string) =>
  new Date(`${format(new Date(), "yyyy-MM-dd")}T${time}:00.000000Z`).toLocaleString(
    undefined,
    { hour: "2-digit", minute: "2-digit", hour12: false },
  );

describe("HeatMap", () => {
  it("renders nothing when there are no time blocks", () => {
    const { container } = render(<HeatMap data={{}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("summarises the busiest cell and titles each cell with its count", () => {
    render(
      <HeatMap
        data={{
          "00:00": { Mon: 1, Tue: 4 },
          "02:00": { Wed: 10 }, // missing days count as 0
          "04:00": { Sun: 2 },
        }}
      />,
    );

    expect(
      screen.getByRole("img", {
        name: `Busiest time: Wed ${localTime("02:00")}, 10 queries`,
      }),
    ).toBeInTheDocument();

    // Singular vs plural, and zero cells for missing days.
    expect(screen.getByTitle(`Mon ${localTime("00:00")}: 1 query`)).toBeInTheDocument();
    expect(screen.getByTitle(`Tue ${localTime("00:00")}: 4 queries`)).toBeInTheDocument();
    const empty = screen.getByTitle(`Mon ${localTime("02:00")}: 0 queries`);
    // jsdom's CSSOM drops var()/color-mix() values, so read the raw style attribute.
    expect(empty.getAttribute("style")).toContain("var(--muted)");

    // Cells are tinted by share of the max, with a 15% floor so 1 query is visible.
    expect(screen.getByTitle(`Wed ${localTime("02:00")}: 10 queries`).getAttribute("style")).toContain(
      "100%",
    );
    expect(screen.getByTitle(`Mon ${localTime("00:00")}: 1 query`).getAttribute("style")).toContain(
      "15%",
    );

    // Only every other row is labelled (rows 0 and 2 here).
    expect(screen.getByText(localTime("00:00"))).toBeInTheDocument();
    expect(screen.getByText(localTime("04:00"))).toBeInTheDocument();
    expect(screen.queryByText(localTime("02:00"))).not.toBeInTheDocument();

    expect(screen.queryByText(/Busy hours and days/)).not.toBeInTheDocument();
  });

  it("shows the empty hint when every cell is zero", () => {
    render(<HeatMap data={{ "00:00": { Mon: 0 }, "02:00": {} }} />);

    expect(screen.getByRole("img", { name: "No queries yet" })).toBeInTheDocument();
    expect(screen.getByText(/Busy hours and days show up here/)).toBeInTheDocument();
  });
});
