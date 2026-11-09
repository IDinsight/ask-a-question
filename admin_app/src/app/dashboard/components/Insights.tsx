import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "@/utils/auth";
import { toast } from "@/components/ui/toast";
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
  // Same { message, color } shape the old Snackbar used; shown by the Toaster in dashboard/layout.tsx.
  const setSnackMessage = ({
    message,
    color,
  }: {
    message: string | null;
    color: "success" | "info" | "warning" | "error" | undefined;
  }) => {
    if (message) toast.add({ title: message, type: color });
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
            onClick={setSelectedTopicId}
            topicsPerPage={7}
          />
        </div>
        <div className="flex max-h-150 min-w-0 flex-[3_1_420px] flex-col p-5">
          <Queries
            data={topicQueries}
            onRefreshClick={() => runRefresh(timePeriod)}
            aiSummary={aiSummary}
            lastRefreshed={currentData.refreshTimeStamp}
            refreshing={currentRefreshing}
          />
        </div>
      </section>

      <BokehPlot timePeriod={timePeriod} token={token} />
    </div>
  );
};

export default Insight;
