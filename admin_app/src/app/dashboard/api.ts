import api from "../../utils/api";
import { Period } from "./types";

const getOverviewPageData = async (period: Period, token: string) => {
  try {
    const response = await api.get(`/dashboard/overview/${period}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching dashboard overview page data");
  }
};

const fetchTopicsData = async (period: Period, token: string) => {
  try {
    const response = await api.get(`/dashboard/insights/${period}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching Topics data");
  }
};

const getEmbeddingData = async (period: Period, token: string) => {
  try {
    const response = await api.get(`/dashboard/topic_visualization/${period}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching dashboard embedding data");
  }
};

const generateNewTopics = async (period: Period, token: string) => {
  try {
    const response = await api.get(`/dashboard/insights/${period}/refresh`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error generating Topics data");
  }
};

const getPerformancePageData = async (period: Period, token: string) => {
  try {
    const response = await api.get(`/dashboard/performance/${period}`, {
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
) => {
  try {
    const response = await api.get(`/dashboard/performance/${period}/${content_id}`, {
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
) => {
  try {
    const response = await api.get(
      `/dashboard/performance/${period}/${content_id}/ai-summary`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );
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
