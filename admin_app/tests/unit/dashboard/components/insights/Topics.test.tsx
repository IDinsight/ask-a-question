import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import Topics from "@/components/features/dashboard/components/insights/Topics";
import type { TopicData } from "@/components/features/dashboard/types";

const topics = (n: number): TopicData[] =>
  Array.from({ length: n }, (_, i) => ({
    topic_id: i + 1,
    topic_name: `Topic ${i + 1}`,
    topic_popularity: (i + 1) * 3,
  }));

const topicButtons = () =>
  screen.getAllByRole("button").filter((b) => b.hasAttribute("aria-pressed"));

describe("Topics", () => {
  it("shows a placeholder when there are no topics (data defaults to empty)", () => {
    render(<Topics selectedTopicId={null} onClick={() => {}} topicsPerPage={3} />);

    expect(screen.getByText("No topics yet.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });

  it("lists topics with their counts and marks the selected one", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <Topics data={topics(2)} selectedTopicId={2} onClick={onClick} topicsPerPage={3} />,
    );

    expect(screen.getByRole("button", { name: /Topic 1/ })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.getByRole("button", { name: /Topic 2/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByLabelText("6 queries")).toHaveTextContent("6");
    // Fits on one page, so no pager.
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Topic 1/ }));
    expect(onClick).toHaveBeenCalledWith(1);
  });

  it("pages through topics", async () => {
    const user = userEvent.setup();
    render(
      <Topics data={topics(5)} selectedTopicId={null} onClick={() => {}} topicsPerPage={3} />,
    );
    const prev = screen.getByRole("button", { name: "Previous topics" });
    const next = screen.getByRole("button", { name: "Next topics" });

    expect(screen.getByText("1 / 2")).toBeInTheDocument();
    expect(topicButtons().map((b) => b.textContent)).toEqual(["Topic 13", "Topic 26", "Topic 39"]);
    expect(prev).toBeDisabled();

    await user.click(next);
    expect(screen.getByText("2 / 2")).toBeInTheDocument();
    expect(topicButtons()).toHaveLength(2);
    expect(next).toBeDisabled();

    await user.click(prev);
    expect(screen.getByText("1 / 2")).toBeInTheDocument();
  });

  it("moves back to the last page when new data has fewer pages", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <Topics data={topics(7)} selectedTopicId={null} onClick={() => {}} topicsPerPage={3} />,
    );
    await user.click(screen.getByRole("button", { name: "Next topics" }));
    await user.click(screen.getByRole("button", { name: "Next topics" }));
    expect(screen.getByText("3 / 3")).toBeInTheDocument();

    rerender(
      <Topics data={topics(4)} selectedTopicId={null} onClick={() => {}} topicsPerPage={3} />,
    );
    expect(screen.getByText("2 / 2")).toBeInTheDocument();
    expect(topicButtons().map((b) => b.textContent)).toEqual(["Topic 412"]);
  });
});
