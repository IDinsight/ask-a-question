import api, { CustomError, handleApiError } from "../../utils/api";
import axios from "axios";

const createNewApiKey = async (token: string) => {
  try {
    const response = await api.put(
      "/workspace/rotate-key",
      {},
      {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      },
    );
    return response.data;
  } catch (customError) {
    let error_message = "Error rotating API key";
    handleApiError(customError, error_message);
  }
};

export { createNewApiKey };
