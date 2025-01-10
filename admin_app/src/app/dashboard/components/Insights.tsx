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

  // Which topic is selected in the UI
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null);

  // Queries associated with the selected topic
  const [topicQueries, setTopicQueries] = useState<QueryData[]>([]);

  // AI summary for the selected topic
  const [aiSummary, setAiSummary] = useState<string>("");

  // We define all time periods upfront
  const timePeriods: Period[] = ["day", "week", "month", "year"];

  // Data for each timePeriod
  const [dataByTimePeriod, setDataByTimePeriod] = useState<
    Record<string, TopicModelingResponse>
  >({});

  // Whether each timePeriod is currently “refreshing”
  const [refreshingByTimePeriod, setRefreshingByTimePeriod] = useState<
    Record<string, boolean>
  >({});

  // Track the status (e.g. "not_started", "in_progress", "completed", "error") per timePeriod
  const [dataStatusByTimePeriod, setDataStatusByTimePeriod] = useState<
    Record<string, Status>
  >({});

  // Keep references to polling timers per timePeriod
  const pollingTimerRef = useRef<Record<string, NodeJS.Timeout | null>>({});

  // Snackbar state
  const [snackMessage, setSnackMessage] = useState<{
    message: string | null;
    color: "success" | "info" | "warning" | "error" | undefined;
  }>({ message: null, color: undefined });

  // Slide transition for Snackbar
  const SnackbarSlideTransition = (props: SlideProps) => {
    return <Slide {...props} direction="up" />;
  };

  /**
   * Triggers a refresh for a given period and then starts polling to see when it's done
   */
  const runRefresh = (period: Period) => {
    const periodKey = period;

    setRefreshingByTimePeriod((prev) => ({ ...prev, [periodKey]: true }));
    setDataStatusByTimePeriod((prev) => ({ ...prev, [periodKey]: "in_progress" }));

    generateNewTopics(period, token!)
      .then((response) => {
        // Show user feedback via Snackbar
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
   * Poll the backend for updated data until status is "completed" or "error"
   */
  const pollData = (period: Period) => {
    const periodKey = period;

    // If a timer already exists for this period, skip
    if (pollingTimerRef.current[periodKey]) return;

    const startTime = Date.now();

    pollingTimerRef.current[periodKey] = setInterval(async () => {
      try {
        const elapsedTime = Date.now() - startTime;

        // If we've exceeded the polling timeout, stop polling and show an error
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

        // Fetch updated data for this period
        const dataFromBackendResponse = await fetchTopicsData(period, token!);

        // Update status
        setDataStatusByTimePeriod((prev) => ({
          ...prev,
          [periodKey]: dataFromBackendResponse.status,
        }));

        // If completed, store the data, stop polling, and update UI if current tab
        if (dataFromBackendResponse.status === "completed") {
          setDataByTimePeriod((prev) => ({
            ...prev,
            [periodKey]: dataFromBackendResponse,
          }));
          setRefreshingByTimePeriod((prev) => ({ ...prev, [periodKey]: false }));

          clearInterval(pollingTimerRef.current[periodKey]!);
          pollingTimerRef.current[periodKey] = null;

          if (period === timePeriod) {
            updateUIForCurrentTimePeriod(dataFromBackendResponse);
          }
        } else if (dataFromBackendResponse.status === "error") {
          // If error, store the error data, stop polling, and inform the user
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
        // If still in_progress, we do nothing more here; keep polling
      } catch (error) {
        // On any exception, stop polling and show an error
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
   * On mount, attempt to fetch data for all timePeriods.
   * If a period is "in_progress", start polling it.
   */
  useEffect(() => {
    if (!token) return;

    timePeriods.forEach((period) => {
      fetchTopicsData(period, token!).then((dataFromBackendResponse) => {
        // Update the status
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
        }
      });
    });

    // Cleanup polling timers on unmount
    return () => {
      Object.values(pollingTimerRef.current).forEach((timer) => {
        if (timer) clearInterval(timer);
      });
      pollingTimerRef.current = {};
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  /**
   * Whenever the user changes the selected timePeriod (e.g. day -> week),
   * update the UI (topic list, queries, etc.) if there's already data.
   * If that timePeriod was "in_progress" but not polling, start polling.
   */
  useEffect(() => {
    const periodKey = timePeriod;

    if (dataByTimePeriod[periodKey]) {
      updateUIForCurrentTimePeriod(dataByTimePeriod[periodKey]);

      // If "in_progress" but no active timer, start polling
      if (
        dataStatusByTimePeriod[periodKey] === "in_progress" &&
        !pollingTimerRef.current[periodKey]
      ) {
        pollData(timePeriod);
      }
    }
  }, [timePeriod, dataByTimePeriod, dataStatusByTimePeriod]);

  /**
   * Update local states (selectedTopicId, topicQueries, aiSummary) for the newly
   * selected timePeriod. This gets called when data for that period is loaded
   * or when the user changes timePeriod.
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
   * Whenever the data changes or the selectedTopicId changes, refresh
   * the queries/AI summary to show the correct topic details.
   */
  useEffect(() => {
    const currentData = dataByTimePeriod[timePeriod] || {
      status: "not_started",
      refreshTimeStamp: "",
      data: [],
      unclustered_queries: [],
      error_message: "",
      failure_step: "",
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

  // Grab current data for the chosen timePeriod
  const currentData = dataByTimePeriod[timePeriod] || {
    status: "not_started",
    refreshTimeStamp: "",
    data: [],
    unclustered_queries: [],
    error_message: "",
    failure_step: "",
  };

  // Are we refreshing the current timePeriod?
  const currentRefreshing = refreshingByTimePeriod[timePeriod] || false;

  // Topics for the left-side Topics list
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
        {/* Left panel: list of topics */}
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

        {/* Right panel: queries table, AI summary, etc. */}
        <Box sx={{ padding: 2, width: "75%" }}>
          <Queries
            data={topicQueries}
            onRefreshClick={() => runRefresh(timePeriod)} // Refresh button triggers new generation
            aiSummary={aiSummary}
            lastRefreshed={currentData.refreshTimeStamp}
            refreshing={currentRefreshing}
          />
        </Box>
      </Paper>

      {/* Bokeh scatter plot below */}
      <BokehPlot timePeriod={timePeriod} token={token} />

      {/* Snackbars for success/warning/error messages */}
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
