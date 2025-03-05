import api, { CustomError } from "../../utils/api";
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
      }
      }
    );
    return response.data;
  } catch (customError) {
    if (
      axios.isAxiosError(customError) &&
      customError.response &&
      customError.response.status !== 500
    ) {
      throw {
        status: customError.response.status,
        message: customError.response.data?.detail,
      } as CustomError;
    } else {
      throw new Error("Error rotating API key");
    }
  }
};

export { createNewApiKey };
