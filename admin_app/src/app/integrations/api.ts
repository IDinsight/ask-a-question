import api from "../../utils/api";

const createNewApiKey = async (token: string) => {
  try {
    const response = await api.put(
      "/user/rotate-key",
      {},
      {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      },
    );
    return response.data;
  } catch (error) {
    throw new Error("Error rotating API key");
  }
};

export { createNewApiKey };
