import api from "../../utils/api";
import { Period } from "./types";

function formatDate(date: Date): string {
  return date.toISOString().split("T")[0];
}

const getOverviewPageData = async (
  period: Period,
  token: string,
  startDate?: Date,
  endDate?: Date,
) => {
  try {
    let url = `/dashboard/overview?period=${period}`;
    if (period === "custom" && startDate && endDate) {
      url += `&start_date=${formatDate(startDate)}&end_date=${formatDate(endDate)}`;
    }
    const response = await api.get(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching dashboard overview page data");
  }
};

const fetchTopicsData = async (
  period: Period,
  token: string,
  startDate?: Date,
  endDate?: Date,
) => {
  try {
    let url = `/dashboard/insights?period=${period}`;
    if (period === "custom" && startDate && endDate) {
      url += `&start_date=${formatDate(startDate)}&end_date=${formatDate(endDate)}`;
    }
    const response = await api.get(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching Topics data");
  }
};

const getEmbeddingData = async (
  period: Period,
  token: string,
  startDate?: Date,
  endDate?: Date,
) => {
  try {
    let url = `/dashboard/topic_visualization?period=${period}`;
    if (period === "custom" && startDate && endDate) {
      url += `&start_date=${formatDate(startDate)}&end_date=${formatDate(endDate)}`;
    }
    const response = await api.get(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching dashboard embedding data");
  }
};

const generateNewTopics = async (
  period: Period,
  token: string,
  startDate?: Date,
  endDate?: Date,
) => {
  try {
    let url = `/dashboard/insights/refresh?period=${period}`;
    if (period === "custom" && startDate && endDate) {
      url += `&start_date=${formatDate(startDate)}&end_date=${formatDate(endDate)}`;
    }
    const response = await api.get(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error kicking off new topic generation");
  }
};

const getPerformancePageData = async (
  period: Period,
  token: string,
  startDate?: Date,
  endDate?: Date,
) => {
  try {
    let url = `/dashboard/performance?period=${period}`;
    if (period === "custom" && startDate && endDate) {
      url += `&start_date=${formatDate(startDate)}&end_date=${formatDate(endDate)}`;
    }
    const response = await api.get(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching dashboard performance page data");
  }
};

const getPerformanceDrawerData = async (
  period: Period,
  content_id: number,
  token: string,
  startDate?: Date,
  endDate?: Date,
) => {
  try {
    let url = `/dashboard/performance/content?period=${period}&content_id=${content_id}`;
    if (period === "custom" && startDate && endDate) {
      url += `&start_date=${formatDate(startDate)}&end_date=${formatDate(endDate)}`;
    }
    const response = await api.get(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching dashboard performance drawer data");
  }
};

const getPerformanceDrawerAISummary = async (
  period: Period,
  content_id: number,
  token: string,
  startDate?: Date,
  endDate?: Date,
) => {
  try {
    let url = `/dashboard/performance/content/ai-summary?period=${period}&content_id=${content_id}`;
    if (period === "custom" && startDate && endDate) {
      url += `&start_date=${formatDate(startDate)}&end_date=${formatDate(endDate)}`;
    }
    const response = await api.get(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching dashboard performance drawer AI summary");
  }
};

export {
  getOverviewPageData,
  getPerformancePageData,
  getPerformanceDrawerData,
  getPerformanceDrawerAISummary,
  fetchTopicsData,
  generateNewTopics,
  getEmbeddingData,
};
