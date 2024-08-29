import React from "react";
import Grid from "@mui/material/Unstable_Grid2";
import Topics from "./insights/Topics";
import Queries from "./insights/Queries";
import Box from "@mui/material/Box";
import { useState } from "react";
import { QueryData, Period, TopicModelingResponse } from "../types";
import { generateNewTopics, fetchTopicsData } from "../api";
import { useAuth } from "@/utils/auth";

interface InsightProps {
  timePeriod: Period;
}

const Insight: React.FC<InsightProps> = ({ timePeriod }) => {
  const { token } = useAuth();
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null);
  const [topicQueries, setTopicQueries] = useState<QueryData[]>([]);
  const [refreshTimestamp, setRefreshTimestamp] = useState<string>("");
  const [refreshing, setRefreshing] = useState<boolean>(false);
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
  }, [token, timePeriod]);

  React.useEffect(() => {
    if (selectedTopicId !== null) {
      const filterQueries = dataFromBackend.data.find(
        (topic) => topic.topic_id === selectedTopicId,
      );

      if (filterQueries) {
        setTopicQueries(filterQueries.topic_samples);
      }
    } else {
      setTopicQueries([]);
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
    <Grid container sx={{ bgcolor: "grey.100", borderRadius: 2, mx: 0.5 }}>
      <Grid
        container
        md={12}
        columnSpacing={{ xs: 2 }}
        sx={{ bgcolor: "white", borderRadius: 2, mx: 0.5, mt: 2, height: 400 }}
      >
        <Grid
          md={3}
          sx={{ p: 2, borderRight: 1, borderColor: "grey.300", borderWidth: 2 }}
        >
          <Topics
            data={topics}
            selectedTopicId={selectedTopicId}
            onClick={setSelectedTopicId}
          />
        </Grid>
        <Grid md={9} sx={{ p: 2 }}>
          <Queries
            data={topicQueries}
            onRefreshClick={runRefresh}
            lastRefreshed={dataFromBackend.refreshTimeStamp}
            refreshing={refreshing}
          />
        </Grid>
      </Grid>
      <Grid
        md={12}
        height={400}
        sx={{
          bgcolor: "white",
          borderRadius: 2,
          mx: 0.5,
          mt: 2,
          justifyItems: "center",
          justifySelf: "stretch",
        }}
      >
        <Box
          textAlign="center"
          height="100%"
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          -- Chart - Coming Soon! --
        </Box>
      </Grid>
    </Grid>
  );
};

export default Insight;
