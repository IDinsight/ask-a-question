import { env } from "next-runtime-env";
import axios from "axios";

const NEXT_PUBLIC_BACKEND_URL: string =
  env("NEXT_PUBLIC_BACKEND_URL") || "http://localhost:8000";

const api = axios.create({
  baseURL: NEXT_PUBLIC_BACKEND_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

import { AxiosResponse, AxiosError } from 'axios';

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    if (error.response && error.response.status === 401) {
      console.log("Unauthorized request");
      const currentPath = window.location.pathname;
      const sourcePage = encodeURIComponent(currentPath);
      localStorage.removeItem("token");
      window.location.href = `/login?sourcePage=${sourcePage}`;
    }
    return Promise.reject(error);
  },
);

interface ContentBody {
  content_title: string;
  content_text: string;
  content_metadata: Record<string, unknown>;
}

const getUser = async (token: string) => {
  try {
    const response = await api.get("/user/", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching user info");
  }
};

const getContentList = async ({
  token,
  skip = 0,
  limit = 200,
}: {
  token: string;
  skip?: number;
  limit?: number;
}) => {
  try {
    const response = await api.get(`/content/?skip=${skip}&limit=${limit}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching content list");
  }
};

const getContent = async (content_id: number, token: string) => {
  try {
    const response = await api.get(`/content/${content_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching content");
  }
};

const archiveContent = async (content_id: number, token: string) => {
  try {
    const response = await api.patch(
      `/content/${content_id}`,
      {},
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return response.data;
  } catch (error) {
    throw new Error("Error archiving content");
  }
};

const deleteContent = async (content_id: number, token: string) => {
  try {
    const response = await api.delete(`/content/${content_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error deleting content");
  }
};

const editContent = async (content_id: number, content: ContentBody, token: string) => {
  try {
    const response = await api.put(`/content/${content_id}`, content, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error editing content");
  }
};

const createContent = async (content: ContentBody, token: string) => {
  try {
    const response = await api.post("/content/", content, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error creating content");
  }
};

const bulkUploadContents = async (file: File, token: string) => {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await api.post("/content/csv-upload", formData, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "multipart/form-data",
      },
    });

    return { status: response.status, data: response.data };
  } catch (error: any) {
    if (error.response) {
      const errorResponse = error.response.data;
      const detail = errorResponse.detail || "An unknown error occurred";
      return { status: error.response.status, detail: detail };
    } else {
      throw new Error("An unexpected error occurred during the bulk upload.");
    }
  }
};

const getUrgencyRuleList = async (token: string) => {
  try {
    const response = await api.get("/urgency-rules/", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching urgency rule list");
  }
};

const addUrgencyRule = async (rule_text: string, token: string) => {
  try {
    const response = await api.post(
      "/urgency-rules/",
      { urgency_rule_text: rule_text },
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return response.data;
  } catch (error) {
    throw new Error("Error adding urgency rule");
  }
};

const updateUrgencyRule = async (rule_id: number, rule_text: string, token: string) => {
  try {
    const response = await api.put(
      `/urgency-rules/${rule_id}`,
      { urgency_rule_text: rule_text },
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return response.data;
  } catch (error) {
    throw new Error("Error updating urgency rule");
  }
};

const deleteUrgencyRule = async (rule_id: number, token: string) => {
  try {
    const response = await api.delete(`/urgency-rules/${rule_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error deleting urgency rule");
  }
};

const getLoginToken = async (username: string, password: string) => {
  const formData = new FormData();
  formData.append("username", username);
  formData.append("password", password);

  try {
    const response = await api.post("/login", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  } catch (error) {
    console.log(error);
    throw new Error("Error fetching login token");
  }
};

const getGoogleLoginToken = async (idToken: {
  client_id: string;
  credential: string;
}) => {
  try {
    const response = await api.post("/login-google", idToken, {
      headers: { "Content-Type": "application/json" },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching Google login token");
  }
};

// Perform search
const getSearch = async (
  question: string,
  generate_llm_response: boolean,
  token: string,
) => {
  try {
    const response = await api.post(
      "/search",
      {
        query_text: question,
        generate_llm_response,
      },
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return { status: response.status, ...response.data };
  } catch (error) {
    throw new Error("Error performing search");
  }
};

// Post response feedback
const postResponseFeedback = async (
  query_id: number,
  feedback_sentiment: string,
  feedback_secret_key: string,
  token: string,
) => {
  try {
    const response = await api.post(
      "/response-feedback",
      {
        query_id,
        feedback_sentiment,
        feedback_secret_key,
      },
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return response.data;
  } catch (error) {
    throw new Error("Error sending response feedback");
  }
};

// Get question stats
const getQuestionStats = async (token: string) => {
  try {
    const response = await api.get("/dashboard/question_stats", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching question stats");
  }
};

// Get urgency detection
const getUrgencyDetection = async (search: string, token: string) => {
  try {
    const response = await api.post(
      "/urgency-detect",
      { message_text: search },
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return response.data;
  } catch (error: any) {
    throw new Error(`Error fetching urgency detection: ${error.message}`);
  }
};

// Create new tag
const createTag = async (tag: string, token: string) => {
  try {
    const response = await api.post(
      "/tag/",
      { tag_name: tag },
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return response.data;
  } catch (error) {
    throw new Error("Error creating tag");
  }
};

// Get tag list
const getTagList = async (token: string) => {
  try {
    const response = await api.get("/tag/", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching tag list");
  }
};

// Delete tag
const deleteTag = async (tag_id: number, token: string) => {
  try {
    const response = await api.delete(`/tag/${tag_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error deleting tag");
  }
};
export const apiCalls = {
  getUser,
  getContentList,
  getContent,
  archiveContent,
  deleteContent,
  editContent,
  createContent,
  bulkUploadContents,
  getUrgencyRuleList,
  addUrgencyRule,
  updateUrgencyRule,
  deleteUrgencyRule,
  getLoginToken,
  getGoogleLoginToken,
  getSearch,
  postResponseFeedback,
  getQuestionStats,
  getUrgencyDetection,
  createTag,
  getTagList,
  deleteTag,
};
export default api;
