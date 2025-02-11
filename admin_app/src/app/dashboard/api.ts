import api from "../../utils/api";
import { Period, CustomDashboardFrequency } from "./types";

function buildURL(
  basePath: string,
  period: Period,
  options: {
    startDate?: string;
    endDate?: string;
    frequency?: CustomDashboardFrequency;
    contentId?: number;
    extraPath?: string;
  } = {},
): string {
  let url = `${basePath}/${period}`;
  if (options.contentId !== undefined) {
    url += `/${options.contentId}`;
  }
  if (options.extraPath) {
    url += `/${options.extraPath}`;
  }
  const params = new URLSearchParams();
  if (period === "custom") {
    if (options.startDate && options.endDate) {
      params.set("start_date", options.startDate);
      params.set("end_date", options.endDate);
    }
    params.set("frequency", options.frequency || "Day");
  } else {
    if (options.frequency) {
      params.set("frequency", options.frequency);
    }
  }
  const queryString = params.toString();
  if (queryString) {
    url += `?${queryString}`;
  }
  return url;
}

async function fetchData(url: string, token: string, errorMessage: string) {
  try {
    const response = await api.get(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error(errorMessage);
  }
}

const getOverviewPageData = async (
  period: Period,
  token: string,
  startDate?: string,
  endDate?: string,
  frequency?: CustomDashboardFrequency,
) => {
  const url = buildURL("/dashboard/overview", period, {
    startDate,
    endDate,
    frequency,
  });
  return fetchData(url, token, "Error fetching dashboard overview page data");
};

const fetchTopicsData = async (
  period: Period,
  token: string,
  startDate?: string,
  endDate?: string,
  frequency?: CustomDashboardFrequency,
) => {
  const url = buildURL("/dashboard/insights", period, {
    startDate,
    endDate,
    frequency,
  });
  return fetchData(url, token, "Error fetching Topics data");
};

const getEmbeddingData = async (
  period: Period,
  token: string,
  startDate?: string,
  endDate?: string,
  frequency?: CustomDashboardFrequency,
) => {
  const url = buildURL("/dashboard/topic_visualization", period, {
    startDate,
    endDate,
    frequency,
  });
  return fetchData(url, token, "Error fetching dashboard embedding data");
};

const generateNewTopics = async (
  period: Period,
  token: string,
  startDate?: string,
  endDate?: string,
  frequency?: CustomDashboardFrequency,
) => {
  const url = buildURL("/dashboard/insights", period, {
    startDate,
    endDate,
    frequency,
    extraPath: "refresh",
  });
  return fetchData(url, token, "Error kicking off new topic generation");
};

const getPerformancePageData = async (
  period: Period,
  token: string,
  startDate?: string,
  endDate?: string,
) => {
  const url = buildURL("/dashboard/performance", period, {
    startDate,
    endDate,
  });
  return fetchData(url, token, "Error fetching dashboard performance page data");
};

const getPerformanceDrawerData = async (
  period: Period,
  contentId: number,
  token: string,
  startDate?: string,
  endDate?: string,
) => {
  const url = buildURL("/dashboard/performance", period, {
    contentId,
    startDate,
    endDate,
  });
  return fetchData(url, token, "Error fetching dashboard performance drawer data");
};

const getPerformanceDrawerAISummary = async (
  period: Period,
  contentId: number,
  token: string,
  startDate?: string,
  endDate?: string,
) => {
  const url = buildURL("/dashboard/performance", period, {
    contentId,
    startDate,
    endDate,
    extraPath: "ai-summary",
  });
  return fetchData(
    url,
    token,
    "Error fetching dashboard performance drawer AI summary",
  );
};

export {
  getOverviewPageData,
  fetchTopicsData,
  getEmbeddingData,
  generateNewTopics,
  getPerformancePageData,
  getPerformanceDrawerData,
  getPerformanceDrawerAISummary,
};
