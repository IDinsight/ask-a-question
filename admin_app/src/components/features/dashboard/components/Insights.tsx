import React from "react";

import { TopicModelingResponse } from "../types";
import BokehPlot, { BokehPlotProps } from "./insights/Bokeh";
import Queries from "./insights/Queries";
import Topics from "./insights/Topics";

/**
 * Presentational: DashboardWrapper runs topic discovery (fetch, refresh,
 * polling) and the Bokeh fetch, and passes the results in here.
 */
interface InsightProps {
  /** Topic-modelling result for the selected period. */
  data: TopicModelingResponse;
  selectedTopicId: number | null;
  onSelectTopic: (topicId: number | null) => void;
  /** True while a discovery job is starting or running. */
  refreshing: boolean;
  onRefresh: () => void;
  plot: BokehPlotProps;
}

const Insight: React.FC<InsightProps> = ({
  data,
  selectedTopicId,
  onSelectTopic,
  refreshing,
  onRefresh,
  plot,
}) => {
  const topics = data.data.map(({ topic_id, topic_name, topic_popularity }) => ({
    topic_id,
    topic_name,
    topic_popularity,
  }));
  const selectedTopic = data.data.find((topic) => topic.topic_id === selectedTopicId);

  return (
    <div className="flex flex-col gap-6">
      <section
        aria-label="Topics and example queries"
        className="flex min-h-105 flex-wrap overflow-hidden border bg-card shadow-xs"
      >
        {/* Topics column; stacks above the queries on narrow screens */}
        <div className="flex flex-[1_1_260px] flex-col border-b p-5 md:max-w-85 md:border-r md:border-b-0">
          <Topics
            data={topics}
            selectedTopicId={selectedTopicId}
            onClick={onSelectTopic}
            topicsPerPage={7}
          />
        </div>
        <div className="flex max-h-150 min-w-0 flex-[3_1_420px] flex-col p-5">
          <Queries
            data={selectedTopic?.topic_samples ?? []}
            onRefreshClick={onRefresh}
            aiSummary={selectedTopic?.topic_summary ?? "Not available."}
            lastRefreshed={data.refreshTimeStamp}
            refreshing={refreshing}
          />
        </div>
      </section>

      <BokehPlot {...plot} />
    </div>
  );
};

export default Insight;
