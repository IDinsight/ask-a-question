import React from "react";
import Grid from "@mui/material/Unstable_Grid2";
import Topics from "./insights/Topics";
import Queries from "./insights/Queries";
import { dataFromBackend } from "./tempData";
import Box from "@mui/material/Box";
import { useState } from "react";
interface InsightProps {
  timePeriod: string;
}
import { QueryData } from "../types";

const Insight: React.FC<InsightProps> = ({ timePeriod }) => {
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null);
  const [topicQueries, setTopicQueries] = useState<QueryData[]>([]);
  const [refreshTimestamp, setRefreshTimestamp] = useState<string>("");
  const [dataFromBackend, setDataFromBackend] = useState({
    data: [],
    refreshTimeStamp: "",
  });

  const runRefresh = async () => {
    const date = new Date();
    await new Promise((f) => setTimeout(f, 1000));
    setRefreshTimestamp(date.toLocaleString());
    console.log("Refreshed!", date.toLocaleString());
  };

  React.useEffect(() => {
    // Call the API to get the data for timePeriod and pass it to setDataFromBackend
    // set selectedTopicId to the first topic_id (or null)
    // Add pagination (if easy)
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
  }, [selectedTopicId, refreshTimestamp, timePeriod]);

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
          md={2}
          sx={{ p: 2, borderRight: 1, borderColor: "grey.300", borderWidth: 2 }}
        >
          <Topics
            data={topics}
            selectedTopicId={selectedTopicId}
            onClick={setSelectedTopicId}
          />
        </Grid>
        <Grid md={10} sx={{ p: 2 }}>
          <Queries
            data={topicQueries}
            onRefresh={runRefresh}
            lastRefreshed={dataFromBackend.refreshTimeStamp}
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
