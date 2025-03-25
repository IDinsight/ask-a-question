import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "@/utils/auth";
import { Alert, Paper, Slide, SlideProps, Snackbar, Box } from "@mui/material";
import { fetchTopicsData, generateNewTopics } from "../api";
import {
  Period,
  QueryData,
  TopicModelingResponse,
  Status,
  CustomDateParams,
} from "../types";

import BokehPlot from "./insights/Bokeh";
import Queries from "./insights/Queries";
import Topics from "./insights/Topics";

interface InsightProps {
  timePeriod: Period;
  customDateParams?: CustomDateParams;
}

const POLLING_INTERVAL = 3 * 1000;
const POLLING_TIMEOUT = 3 * 60 * 1000;

const Insight: React.FC<InsightProps> = ({ timePeriod, customDateParams }) => {
  const { token } = useAuth();
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null);
  const [topicQueries, setTopicQueries] = useState<QueryData[]>([]);
  const [aiSummary, setAiSummary] = useState<string>("");
  const [dataByTimePeriod, setDataByTimePeriod] = useState<
    Record<string, TopicModelingResponse>
  >({});
  const [refreshingByTimePeriod, setRefreshingByTimePeriod] = useState<
    Record<string, boolean>
  >({});
  const [dataStatusByTimePeriod, setDataStatusByTimePeriod] = useState<
    Record<string, Status>
  >({});
  const pollingTimerRef = useRef<Record<string, NodeJS.Timeout | null>>({});
  const [snackMessage, setSnackMessage] = useState<{
    message: string | null;
    color: "success" | "info" | "warning" | "error" | undefined;
  }>({ message: null, color: undefined });

  const SnackbarSlideTransition = (props: SlideProps) => {
    return <Slide {...props} direction="up" />;
  };

  const timePeriods: Period[] = ["day", "week", "month", "year", "custom"];

  const runRefresh = (period: Period) => {
    const periodKey = period;
    setRefreshingByTimePeriod((prev) => ({ ...prev, [periodKey]: true }));
    setDataStatusByTimePeriod((prev) => ({
      ...prev,
      [periodKey]: "in_progress",
    }));

    if (
      period === "custom" &&
      customDateParams?.startDate &&
      customDateParams.endDate
    ) {
      generateNewTopics(
        "custom",
        token!,
        customDateParams.startDate,
        customDateParams.endDate,
      )
        .then((response) => {
          setSnackMessage({ message: response.detail, color: "info" });
          pollData(period);
        })
        .catch((error) => {
          setRefreshingByTimePeriod((prev) => ({
            ...prev,
            [periodKey]: false,
          }));
          setDataStatusByTimePeriod((prev) => ({
            ...prev,
            [periodKey]: "error",
          }));
          setSnackMessage({
            message: error.message || "There was a system error.",
            color: "error",
          });
        });
    } else {
      generateNewTopics(period, token!)
        .then((response) => {
          setSnackMessage({ message: response.detail, color: "info" });
          pollData(period);
        })
        .catch((error) => {
          setRefreshingByTimePeriod((prev) => ({
            ...prev,
            [periodKey]: false,
          }));
          setDataStatusByTimePeriod((prev) => ({
            ...prev,
            [periodKey]: "error",
          }));
          setSnackMessage({
            message: error.message || "There was a system error.",
            color: "error",
          });
        });
    }
  };

  const pollData = (period: Period) => {
    const periodKey = period;
    if (pollingTimerRef.current[periodKey]) return;
    const startTime = Date.now();

    pollingTimerRef.current[periodKey] = setInterval(async () => {
      try {
        const elapsedTime = Date.now() - startTime;
        if (elapsedTime >= POLLING_TIMEOUT) {
          setRefreshingByTimePeriod((prev) => ({
            ...prev,
            [periodKey]: false,
          }));
          setDataStatusByTimePeriod((prev) => ({
            ...prev,
            [periodKey]: "error",
          }));
          clearInterval(pollingTimerRef.current[periodKey]!);
          pollingTimerRef.current[periodKey] = null;
          setSnackMessage({
            message:
              "The processing is taking longer than expected. Please try again later.",
            color: "error",
          });
          return;
        }

        let dataFromBackendResponse: TopicModelingResponse;
        if (
          period === "custom" &&
          customDateParams?.startDate &&
          customDateParams.endDate
        ) {
          dataFromBackendResponse = await fetchTopicsData(
            "custom",
            token!,
            customDateParams.startDate,
            customDateParams.endDate,
          );
        } else {
          dataFromBackendResponse = await fetchTopicsData(period, token!);
        }

        setDataStatusByTimePeriod((prev) => ({
          ...prev,
          [periodKey]: dataFromBackendResponse.status,
        }));

        if (dataFromBackendResponse.status === "completed") {
          setDataByTimePeriod((prev) => ({
            ...prev,
            [periodKey]: dataFromBackendResponse,
          }));
          setRefreshingByTimePeriod((prev) => ({
            ...prev,
            [periodKey]: false,
          }));
          clearInterval(pollingTimerRef.current[periodKey]!);
          pollingTimerRef.current[periodKey] = null;
          setSnackMessage({
            message: "Topic analysis successful for period: " + period,
            color: "success",
          });
          if (period === timePeriod) {
            updateUIForCurrentTimePeriod(dataFromBackendResponse);
          }
        } else if (dataFromBackendResponse.status === "error") {
          setDataByTimePeriod((prev) => ({
            ...prev,
            [periodKey]: dataFromBackendResponse,
          }));
          setRefreshingByTimePeriod((prev) => ({
            ...prev,
            [periodKey]: false,
          }));
          clearInterval(pollingTimerRef.current[periodKey]!);
          pollingTimerRef.current[periodKey] = null;
          setSnackMessage({
            message: `An error occurred: ${dataFromBackendResponse.error_message}`,
            color: "error",
          });
        }
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

  useEffect(() => {
    if (!token) return;
    timePeriods.forEach((period) => {
      if (
        period === "custom" &&
        (!customDateParams?.startDate || !customDateParams.endDate)
      )
        return;
      if (period === "custom") {
        fetchTopicsData(
          "custom",
          token!,
          customDateParams!.startDate!,
          customDateParams!.endDate!,
        ).then((dataFromBackendResponse) => {
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
      } else {
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
          }
        });
      }
    });
    return () => {
      Object.values(pollingTimerRef.current).forEach((timer) => {
        if (timer) clearInterval(timer);
      });
      pollingTimerRef.current = {};
    };
  }, [token, customDateParams]);

  useEffect(() => {
    const periodKey = timePeriod;
    if (dataByTimePeriod[periodKey]) {
      updateUIForCurrentTimePeriod(dataByTimePeriod[periodKey]);
      if (
        dataStatusByTimePeriod[periodKey] === "in_progress" &&
        !pollingTimerRef.current[periodKey]
      ) {
        pollData(timePeriod);
      }
    }
  }, [timePeriod, dataByTimePeriod, dataStatusByTimePeriod]);

  const updateUIForCurrentTimePeriod = (dataResponse: TopicModelingResponse) => {
    if (dataResponse.data.length > 0) {
      setSelectedTopicId(dataResponse.data[0].topic_id);
    } else {
      setSelectedTopicId(null);
      setTopicQueries([]);
      setAiSummary("Not available.");
    }
  };
  useEffect(() => {
    const periodKey = timePeriod;
    if (dataByTimePeriod[periodKey]) {
      updateUIForCurrentTimePeriod(dataByTimePeriod[periodKey]);
      if (
        dataStatusByTimePeriod[periodKey] === "in_progress" &&
        !pollingTimerRef.current[periodKey]
      ) {
        pollData(timePeriod);
      }
    }
  }, [timePeriod, dataByTimePeriod, dataStatusByTimePeriod]);

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
