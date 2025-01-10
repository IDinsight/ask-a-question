import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "@/utils/auth";
import { Alert, Paper, Slide, SlideProps, Snackbar, Box } from "@mui/material";
import { fetchTopicsData, generateNewTopics } from "../api";
import { Period, QueryData, TopicModelingResponse, Status } from "../types";

import BokehPlot from "./insights/Bokeh";
import Queries from "./insights/Queries";
import Topics from "./insights/Topics";

interface InsightProps {
  timePeriod: Period;
}

// Poll every 3s (don't want to overwhelm back-end)
const POLLING_INTERVAL = 3000;

// Timeout after 90s
const POLLING_TIMEOUT = 90000;

const Insight: React.FC<InsightProps> = ({ timePeriod }) => {
  const { token } = useAuth();
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null);
  const [topicQueries, setTopicQueries] = useState<QueryData[]>([]);
  const [aiSummary, setAiSummary] = useState<string>("");
  // We define all time periods upfront
  const timePeriods: Period[] = ["day", "week", "month", "year"];
  // State to hold fetched data for all timePeriods
  const [dataByTimePeriod, setDataByTimePeriod] = useState<
    Record<string, TopicModelingResponse>
  >({});
  // Track whether each timePeriod is in “refreshing” state
  const [refreshingByTimePeriod, setRefreshingByTimePeriod] = useState<
    Record<string, boolean>
  >({});
  // Track data status (e.g. “not_started”, “completed”) for each timePeriod
  const [dataStatusByTimePeriod, setDataStatusByTimePeriod] = useState<
    Record<string, Status>
  >({});
  // Keep references to polling timers per timePeriod
  const pollingTimerRef = useRef<Record<string, NodeJS.Timeout | null>>({});

  const SnackbarSlideTransition = (props: SlideProps) => {
    return <Slide {...props} direction="up" />;
  };

  const [snackMessage, setSnackMessage] = useState<{

    message: string | null;
    color: "success" | "info" | "warning" | "error" | undefined;
  }>({ message: null, color: undefined });

  /**
   * Start a refresh then poll
   */
  const runRefresh = (period: Period) => {
    const periodKey = period;
    setRefreshingByTimePeriod((prev) => ({ ...prev, [periodKey]: true }));
    setDataStatusByTimePeriod((prev) => ({ ...prev, [periodKey]: "in_progress" }));

    generateNewTopics(period, token!)
      .then((response) => {
        setSnackMessage({
          message: response.detail,
          color: "info",
        });
        pollData(period);
      })
      .catch((error) => {
        setRefreshingByTimePeriod((prev) => ({ ...prev, [periodKey]: false }));
        setDataStatusByTimePeriod((prev) => ({ ...prev, [periodKey]: "error" }));
        setSnackMessage({
          message: error.message || "There was a system error.",
          color: "error",
        });
      });
  };

  /**
   * Poll the back-end
   */
  const pollData = (period: Period) => {
    const periodKey = period;

    // If a timer already exists, don't create another
    if (pollingTimerRef.current[periodKey]) return;

    const startTime = Date.now();

    pollingTimerRef.current[periodKey] = setInterval(async () => {
      try {
        const elapsedTime = Date.now() - startTime;

        // Don't exceed timeout
        if (elapsedTime >= POLLING_TIMEOUT) {
          setRefreshingByTimePeriod((prev) => ({ ...prev, [periodKey]: false }));
          setDataStatusByTimePeriod((prev) => ({ ...prev, [periodKey]: "error" }));

          clearInterval(pollingTimerRef.current[periodKey]!);
          pollingTimerRef.current[periodKey] = null;

          setSnackMessage({
            message:
              "The processing is taking longer than expected. Please try again later.",
            color: "error",
          });
          return;
        }

        const dataFromBackendResponse = await fetchTopicsData(period, token!);

        // Update status
        setDataStatusByTimePeriod((prev) => ({
          ...prev,
          [periodKey]: dataFromBackendResponse.status,
        }));

        // If completed, store the data and stop polling
        if (dataFromBackendResponse.status === "completed") {
          setDataByTimePeriod((prev) => ({
            ...prev,
            [periodKey]: dataFromBackendResponse,
          }));
          setRefreshingByTimePeriod((prev) => ({ ...prev, [periodKey]: false }));

          clearInterval(pollingTimerRef.current[periodKey]!);
          pollingTimerRef.current[periodKey] = null;

          // If it's the current tab, update the UI
          if (period === timePeriod) {
            updateUIForCurrentTimePeriod(dataFromBackendResponse);
          }
        } else if (dataFromBackendResponse.status === "error") {
          setDataByTimePeriod((prev) => ({
            ...prev,
            [periodKey]: dataFromBackendResponse,
          }));
          setRefreshingByTimePeriod((prev) => ({ ...prev, [periodKey]: false }));

          clearInterval(pollingTimerRef.current[periodKey]!);
          pollingTimerRef.current[periodKey] = null;

          setSnackMessage({
            message: `An error occurred: ${dataFromBackendResponse.error_message}`,
            color: "error",
          });
        }
        // If still in_progress, just keep polling
      } catch (error) {
        setRefreshingByTimePeriod((prev) => ({ ...prev, [periodKey]: false }));

        clearInterval(pollingTimerRef.current[periodKey]!);
        pollingTimerRef.current[periodKey] = null;

        setSnackMessage({
          message: "There was a system error.",
          color: "error",
        });
      }
    }, POLLING_INTERVAL);
  };

  /**
   * When first rendering, fetch data for all time periods at once
   * Stops weird flashing when switching between time periods otherwise
   */
  useEffect(() => {
    if (!token) return;

    // Removed periodsFetched and initialDataLoaded logic
    timePeriods.forEach((period) => {
      fetchTopicsData(period, token!).then((dataFromBackendResponse) => {
        setDataStatusByTimePeriod((prev) => ({
          ...prev,
          [period]: dataFromBackendResponse.status,
        }));

        if (dataFromBackendResponse.status === "in_progress") {
          setRefreshingByTimePeriod((prev) => ({ ...prev, [period]: true }));
          pollData(period);
        } else if (dataFromBackendResponse.status === "completed") {
          setDataByTimePeriod((prev) => ({
            ...prev,
            [period]: dataFromBackendResponse,
          }));
          setRefreshingByTimePeriod((prev) => ({ ...prev, [period]: false }));
        } else if (dataFromBackendResponse.status === "not_started") {
          setRefreshingByTimePeriod((prev) => ({ ...prev, [period]: false }));
        } else if (dataFromBackendResponse.status === "error") {
          setRefreshingByTimePeriod((prev) => ({ ...prev, [period]: false }));
          setDataByTimePeriod((prev) => ({
            ...prev,
            [period]: dataFromBackendResponse,
          }));
          
  const runRefresh = () => {
    setRefreshing(true);
    generateNewTopics(timePeriod, token!)
      .then((dataFromBackend) => {
        const date = new Date();
        setRefreshTimestamp(date.toLocaleString());
        if (dataFromBackend.status === "error") {
          setSnackMessage({
            message: dataFromBackend.error_message,
            color: "error",
          });
        }
        setRefreshing(false);
      })
      .catch((error) => {
        setSnackMessage({
          message: "There was a system error.",
          color: "error",
        });
        setRefreshing(false);
      });
  };

  React.useEffect(() => {
    if (token) {
      fetchTopicsData(timePeriod, token).then((dataFromBackend) => {
        setDataFromBackend(dataFromBackend);
        if (dataFromBackend.status === "in_progress") {
          setRefreshing(true);
        }
        if (dataFromBackend.status === "not_started") {
          setSnackMessage({
            message: "No topics yet. Please run discovery.",
            color: "warning",
          });
          setRefreshing(false);
        }
        if (dataFromBackend.status === "error") {
          setRefreshing(false);
        }
        if (dataFromBackend.status === "completed" && dataFromBackend.data.length > 0) {
          setSelectedTopicId(dataFromBackend.data[0].topic_id);
        }
      });
    });

    // Cleanup polling timers
    return () => {
      Object.values(pollingTimerRef.current).forEach((timer) => {
        if (timer) clearInterval(timer);
      });
      pollingTimerRef.current = {};
    };
  }, [token]);

  /**
   * Whenever the user switches timePeriod update UI
   */
  useEffect(() => {
    const periodKey = timePeriod;

    if (dataByTimePeriod[periodKey]) {
      updateUIForCurrentTimePeriod(dataByTimePeriod[periodKey]);

      // If data is in_progress but polling hasn’t started, start it
      if (
        dataStatusByTimePeriod[periodKey] === "in_progress" &&
        !pollingTimerRef.current[periodKey]
      ) {
        pollData(timePeriod);
      }
    }
  }, [timePeriod, dataByTimePeriod, dataStatusByTimePeriod]);

  /**
   * Update local states (selectedTopicId, topicQueries, aiSummary) when
   * the newly selected timePeriod has data
   */
  const updateUIForCurrentTimePeriod = (dataResponse: TopicModelingResponse) => {
    if (dataResponse.data.length > 0) {
      setSelectedTopicId(dataResponse.data[0].topic_id);
    } else {
      setSelectedTopicId(null);
      setTopicQueries([]);
      setAiSummary("Not available.");
    }
  };

  /**
   * When data changes or the user changes topic, refresh topic-specific data
   */
  useEffect(() => {
    const currentData = dataByTimePeriod[timePeriod] || {
      status: "not_started",
      refreshTimeStamp: "",
      data: [],
      unclustered_queries: [],
    };

    if (selectedTopicId !== null) {
      const selectedTopic = currentData.data.find(
        (topic) => topic.topic_id === selectedTopicId,
      );

      if (selectedTopic) {
        setTopicQueries(selectedTopic.topic_samples);
        setAiSummary(selectedTopic.topic_summary);
      } else {
        setTopicQueries([]);
        setAiSummary("Not available.");
      }
    } else {
      setTopicQueries([]);
      setAiSummary("Not available.");
    }
  }, [dataByTimePeriod, selectedTopicId, timePeriod]);

  // Current data, refreshing status, etc.
  const currentData = dataByTimePeriod[timePeriod] || {
    status: "not_started",
    refreshTimeStamp: "",
    data: [],
    unclustered_queries: [],
    error_message: "",
    failure_step: "",
  };
  const currentRefreshing = refreshingByTimePeriod[timePeriod] || false;
  const topics = currentData.data.map(({ topic_id, topic_name, topic_popularity }) => ({
    topic_id,
    topic_name,
    topic_popularity,
  }));

  return (
    <Box sx={{ display: "flex", flexDirection: "column" }}>
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
        <Box sx={{ padding: 2, width: "75%" }}>
          <Queries
            data={topicQueries}
            onRefreshClick={() => runRefresh(timePeriod)}
            aiSummary={aiSummary}
            lastRefreshed={currentData.refreshTimeStamp}
            refreshing={currentRefreshing}
          />
        </Box>
      </Paper>

      <BokehPlot timePeriod={timePeriod} token={token} />

      <Snackbar
        open={snackMessage.message !== null}
        autoHideDuration={5000}
        onClose={() => setSnackMessage({ message: null, color: undefined })}
        TransitionComponent={SnackbarSlideTransition}
      >
        <Alert
          variant="filled"
          severity={snackMessage.color}
          onClose={() => setSnackMessage({ message: null, color: undefined })}

          sx={{ width: "100%" }}
        >
          {snackMessage.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Insight;
