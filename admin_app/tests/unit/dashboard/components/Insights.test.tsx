import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import Insight from "@/components/features/dashboard/components/Insights";
import type { TopicModelingResponse } from "@/components/features/dashboard/types";

// The Bokeh child dynamically imports bokehjs; it isn't needed here.
vi.mock("@bokeh/bokehjs", () => ({ embed: { embed_item: vi.fn() } }));

const response: TopicModelingResponse = {
  status: "completed",
  refreshTimeStamp: "",
  unclustered_queries: [],
  data: [
    {
      topic_id: 1,
      topic_name: "Clinic hours",
      topic_popularity: 12,
      topic_summary: "Questions about opening times.",
      topic_samples: [
        {
          query_text: "Open on Sunday?",
          query_datetime_utc: "2026-02-01T08:00:00Z",
        },
      ],
    },
    {
      topic_id: 2,
      topic_name: "Vaccines",
      topic_popularity: 4,
      topic_summary: "Vaccine schedules.",
      topic_samples: [],
    },
  ],
};

const plot = {
  open: false,
  onOpenChange: () => {},
  plotSpec: undefined,
  loading: false,
  error: false,
};

describe("Insight", () => {
  it("lists topics and shows the empty queries panel when none is selected", () => {
    render(
      <Insight
        data={response}
        selectedTopicId={null}
        onSelectTopic={() => {}}
        refreshing={false}
        onRefresh={() => {}}
        plot={plot}
      />,
    );

    expect(
      screen.getByRole("button", { name: /Clinic hours/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Vaccines/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Discover what people ask about"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Topic visualization" }),
    ).toBeInTheDocument();
  });

  it("shows the selected topic's summary and samples, and forwards clicks", async () => {
    const user = userEvent.setup();
    const onSelectTopic = vi.fn();
    const onRefresh = vi.fn();
    render(
      <Insight
        data={response}
        selectedTopicId={1}
        onSelectTopic={onSelectTopic}
        refreshing={false}
        onRefresh={onRefresh}
        plot={plot}
      />,
    );

    expect(
      screen.getByText("Questions about opening times."),
    ).toBeInTheDocument();
    expect(screen.getByText("Open on Sunday?")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Vaccines/ }));
    expect(onSelectTopic).toHaveBeenCalledWith(2);

    await user.click(screen.getByRole("button", { name: "Rerun discovery" }));
    expect(onRefresh).toHaveBeenCalledOnce();
  });
});
