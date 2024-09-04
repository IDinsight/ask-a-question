import { env } from "next-runtime-env";
import api from "../../utils/api";
import { Period } from "./types";

// Get Overview Page Data
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

// Fetch Topics Data
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

// Generate New Topics
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

// Get Performance Page Data
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

// Get Performance Drawer Data
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

// Get Performance Drawer AI Summary
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
};
