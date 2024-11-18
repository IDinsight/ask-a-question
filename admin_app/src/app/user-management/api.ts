import api from "@/utils/api";
interface UserBody {
  sort(arg0: (a: UserBody, b: UserBody) => number): unknown;
  user_id?: number;
  username: string;
  is_admin: boolean;
  content_quota: number;
  api_daily_quota: number;
}
interface UserBodyPassword extends UserBody {
  password: string;
}

const editUser = async (user_id: number, user: UserBody, token: string) => {
  try {
    const response = await api.put(`/user/${user_id}`, user, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error creating content");
  }
};

const createUser = async (user: UserBodyPassword, token: string) => {
  try {
    const response = await api.post("/user/", user, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error creating content");
  }
};
const getUserList = async (token: string) => {
  try {
    const response = await api.get("/user/", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching content list");
  }
};

const getUser = async (token: string) => {
  try {
    const response = await api.get("/user/current-user", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching user info");
  }
};

const getRegisterOption = async () => {
  try {
    const response = await api.get("/user/require-register");
    return response.data;
  } catch (error) {
    throw new Error("Error fetching register option");
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
  } catch (error) {
    console.error(error);
  }
};
const resetPassword = async (
  username: string,
  recovery_code: string,
  password: string,
  token: string,
) => {
  try {
    const response = await api.put(
      "/user/reset-password",
      { username, password, recovery_code },
      {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      },
    );
    return response.data;
  } catch (error) {
    console.error(error);
  }
};

export {
  createUser,
  editUser,
  getUserList,
  getUser,
  getRegisterOption,
  registerUser,
  resetPassword,
};
export type { UserBody, UserBodyPassword };
