/** API calls for the reset-password page. */
import axios from "axios";

import api, { CustomError } from "@/utils/api";

const resetPassword = async (
  username: string,
  recovery_code: string,
  password: string,
) => {
  try {
    const response = await api.put(
      "/user/reset-password",
      { username, password, recovery_code },
      {
        headers: {
          "Content-Type": "application/json",
        },
      },
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
      throw new Error("Error resetting password");
    }
  }
};

export { resetPassword };
