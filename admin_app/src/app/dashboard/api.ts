import { env } from "next-runtime-env";
import { Period } from "./types";

const NEXT_PUBLIC_BACKEND_URL: string =
  env("NEXT_PUBLIC_BACKEND_URL") || "http://localhost:8000";

const getOverviewPageData = async (period: Period, token: string) => {
  return fetch(`${NEXT_PUBLIC_BACKEND_URL}/dashboard/overview/${period}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  }).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error fetching dashboard overview page data");
    }
  });
};

const getPerformancePageData = async (period: Period, token: string) => {
  return fetch(`${NEXT_PUBLIC_BACKEND_URL}/dashboard/performance/${period}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  }).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error fetching dashboard performance page data");
    }
  });
};

const getPerformanceDrawerData = async (
  period: Period,
  content_id: number,
  token: string,
) => {
  return fetch(
    `${NEXT_PUBLIC_BACKEND_URL}/dashboard/performance/${period}/${content_id}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    },
  ).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error fetching dashboard performance drawer data");
    }
  });
};

export { getOverviewPageData, getPerformancePageData, getPerformanceDrawerData };
