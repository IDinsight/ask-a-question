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
export const apiCalls = {
  getLoginToken,
  getGoogleLoginToken,
};
export default api;
