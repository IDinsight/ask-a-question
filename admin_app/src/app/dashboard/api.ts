const NEXT_PUBLIC_BACKEND_URL: string =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

type Period = "day" | "week" | "month" | "year";

const getStatsCardData = async (period: Period, token: string) => {
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
      throw new Error("Error fetching dashboard stats card data");
    }
  });
};

export { getStatsCardData };
