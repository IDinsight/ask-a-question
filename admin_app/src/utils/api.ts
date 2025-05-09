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

import { AxiosResponse, AxiosError } from "axios";

export type CustomError = {
  status: number;
  message: string;
};
export const handleApiError = (customError: any, errorMessage: string) => {
  if (
    axios.isAxiosError(customError) &&
    customError.response &&
    customError.response.status !== 500
  ) {
    throw {
      status: customError.response.status,
      message:
        (customError.response.data as any)?.detail ||
        (customError.response.data as any)?.message ||
        (customError.response.data as any)?.error_message ||
        errorMessage,
    } as CustomError;
  } else {
    throw new Error(errorMessage);
  }
};
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    if (error.response && error.response.status === 401) {
      console.log("Unauthorized request");
      const currentPath = window.location.pathname;
      const sourcePage = encodeURIComponent(currentPath);
      const token = localStorage.getItem("token");
      if (token) {
        localStorage.removeItem("token");
        window.location.href = `/login?sourcePage=${sourcePage}`;
      }
    }
    return Promise.reject(error);
  },
);

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
  } catch (customError) {
    let error_message = "Error fetching login token";
    handleApiError(customError, error_message);
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
    handleApiError(error, "Error fetching Google login token");
    console.error("Error fetching Google login token", error);
  }
};
const getSearch = async (
  question: string,
  generate_llm_response: boolean,
  token: string,
): Promise<{ status: number; data?: any; error?: any } | undefined> => {
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
  } catch (err) {
    const error = err as AxiosError;
    if (error.response) {
      return { status: error.response.status, error: error.response.data };
    } else {
      handleApiError(error, "Error performing search");
      console.error("Error performing search", error.message);
    }
  }
};

const getChat = async (
  question: string,
  generate_llm_response: boolean,
  token: string,
  session_id?: number,
): Promise<{ status: number; data?: any; error?: any } | undefined> => {
  try {
    const response = await api.post(
      "/chat",
      {
        query_text: question,
        generate_llm_response,
        session_id,
      },
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return { status: response.status, ...response.data };
  } catch (err) {
    const error = err as AxiosError;
    handleApiError(error, "Error returning chat response");
    console.error("Error returning chat response", error.message);
  }
};
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
    handleApiError(error, "Error sending response feedback");
    console.error("Error sending response feedback", error);
  }
};

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
    handleApiError(error, "Error fetching urgency detection");
    console.error("Error fetching urgency detection", error.message);
  }
};

export const apiCalls = {
  getLoginToken,
  getGoogleLoginToken,
  getSearch,
  getChat,
  postResponseFeedback,
  getUrgencyDetection,
};
export default api;
