import React from "react";
import Grid from "@mui/material/Unstable_Grid2";
import Topics from "./insights/Topics";
import Queries from "./insights/Queries";
import Box from "@mui/material/Box";
import { useState } from "react";
import { QueryData, Period, TopicModelingResponse } from "../types";
import { generateNewTopics, fetchTopicsData } from "../api";
import { useAuth } from "@/utils/auth";
import { Paper } from "@mui/material";
import BokehPlot from "./insights/Bokeh";

interface InsightProps {
  timePeriod: Period;
}

const Insight: React.FC<InsightProps> = ({ timePeriod }) => {
  const { token } = useAuth();
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null);
  const [topicQueries, setTopicQueries] = useState<QueryData[]>([]);
  const [refreshTimestamp, setRefreshTimestamp] = useState<string>("");
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [aiSummary, setAiSummary] = useState<string>("");

  const [dataFromBackend, setDataFromBackend] = useState<TopicModelingResponse>({
    data: [],
    refreshTimeStamp: "",
    unclustered_queries: [],
  });

  const runRefresh = () => {
    setRefreshing(true);
    generateNewTopics(timePeriod, token!).then((_) => {
      const date = new Date();
      setRefreshTimestamp(date.toLocaleString());
      setRefreshing(false);
    });
  };

  React.useEffect(() => {
    if (token) {
      fetchTopicsData(timePeriod, token).then((dataFromBackend) => {
        setDataFromBackend(dataFromBackend);
        if (dataFromBackend.data.length > 0) {
          setSelectedTopicId(dataFromBackend.data[0].topic_id);
        }
      });
    } else {
      console.log("No token found");
    }
  }, [token, refreshTimestamp, timePeriod]);

  React.useEffect(() => {
    if (selectedTopicId !== null) {
      const filterQueries = dataFromBackend.data.find(
        (topic) => topic.topic_id === selectedTopicId,
      );

      if (filterQueries) {
        setTopicQueries(filterQueries.topic_samples);
        setAiSummary(filterQueries.topic_summary);
      } else {
        setTopicQueries([]);
        setAiSummary("Not available.");
      }
    } else {
      setTopicQueries([]);
      setAiSummary("Not available.");
    }
  }, [dataFromBackend, selectedTopicId, refreshTimestamp, timePeriod]);

  const topics = dataFromBackend.data.map(
    ({ topic_id, topic_name, topic_popularity }) => ({
      topic_id,
      topic_name,
      topic_popularity,
    }),
  );

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Paper
        elevation={0}
        sx={{
          display: "flex",
          flexDirection: "row",
          height: 500,
          width: "100%",
          border: 0.5,
          borderColor: "lightgrey",
        }}
      >
        <Box
          sx={{
            width: "25%",
            padding: 2,
            borderRight: 1,
            borderColor: "grey.300",
            borderWidth: 2,
          }}
        >
          <Topics
            data={topics}
            selectedTopicId={selectedTopicId}
            onClick={setSelectedTopicId}
            topicsPerPage={7}
          />
        </Box>
        <Box
          sx={{
            padding: 2,
            width: "75%",
          }}
        >
          <Queries
            data={topicQueries}
            onRefreshClick={runRefresh}
            aiSummary={aiSummary}
            lastRefreshed={dataFromBackend.refreshTimeStamp}
            refreshing={refreshing}
          />
        </Box>
      </Paper>
      <BokehPlot timePeriod={timePeriod} token={token} />
    </Box>
  );
};

export default Insight;
