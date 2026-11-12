/** API calls for the login page (first-user registration). */
import axios from "axios";

import api, { CustomError } from "@/utils/api";

const getRegisterOption = async () => {
  try {
    const response = await api.get("/user/require-register");
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
      throw new Error("Error fetching register option");
    }
  }
};

const registerUser = async (username: string, password: string) => {
  try {
    const response = await api.post(
      "/user/register-first-user",
      { username, password, is_admin: true },
      {
        headers: { "Content-Type": "application/json" },
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
      throw new Error("Error registering user");
    }
  }
};

export { getRegisterOption, registerUser };
