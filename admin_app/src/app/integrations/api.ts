import { env } from "next-runtime-env";

const NEXT_PUBLIC_BACKEND_URL: string =
  env("NEXT_PUBLIC_BACKEND_URL") || "http://localhost:8000";

const createNewApiKey = async (token: string) => {
  return fetch(`${NEXT_PUBLIC_BACKEND_URL}/user/rotate-key`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  }).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error rotating API key");
    }
  });
};

export { createNewApiKey };
