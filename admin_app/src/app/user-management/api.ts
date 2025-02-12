import { Workspace } from "@/components/WorkspaceMenu";
import api from "@/utils/api";
import axios from "axios";
interface UserBody {
  sort(arg0: (a: UserBody, b: UserBody) => number): unknown;
  user_id?: number;
  username: string;
  user_workspaces?: Workspace[];
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
    throw new Error("Error editing user");
  }
};

const createUser = async (user: UserBodyPassword, token: string) => {
  try {
    const response = await api.post("/user/", user, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error creating user");
  }
};
const getUserList = async (token: string) => {
  try {
    const response = await api.get("/user/", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching user list");
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

const createWorkspace = async (workspace: Workspace, token: string) => {
  try {
    const response = await api.post("/workspace/", workspace, {
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    console.error(error);
  }
};

const getCurrentWorkspace = async (token: string) => {
  try {
    const response = await api.get("/workspace/current-workspace", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching user info");
  }
};

export const checkIfUsernameExists = async (
  username: string,
  token: string,
): Promise<boolean> => {
  try {
    const response = await api.head(`/user/${username}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    return response.status === 200;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      if (error.response?.status === 404) {
        return false;
      }
      throw new Error(
        `Error checking username: ${error.response?.statusText || "Unknown error"}`,
      );
    }
    throw new Error("Error checking username");
  }
};
const getWorkspaceList = async (token: string) => {
  try {
    const response = await api.get("/workspace/", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data as Workspace[];
  } catch (error) {
    throw new Error("Error fetching content list");
  }
};
const getLoginWorkspace = async (workspace_name: string, token: string | null) => {
  const data = { workspace_name };
  console.log("data", data);
  try {
    const response = await api.post("/workspace/switch-workspace", data, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    console.log(error);
    throw new Error("Error fetching workspace login token");
  }
};
const editWorkspace = async (
  workspace_id: number,
  workspace: Workspace,
  token: string,
) => {
  try {
    const response = await api.put(`/workspace/${workspace_id}`, workspace, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error editing workspace");
  }
};

const addUserToWorkspace = async (
  username: string,
  workspace_name: string,
  token: string,
) => {
  try {
    const response = await api.post(
      "/user/add-existing-user-to-workspace",
      { username, workspace_name },
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return response.data;
  } catch (error) {
    throw new Error("Error adding user to workspace");
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
  checkIfUsernameExists,
  createWorkspace,
  getWorkspaceList,
  getLoginWorkspace,
  editWorkspace,
  getCurrentWorkspace,
  addUserToWorkspace,
};
export type { UserBody, UserBodyPassword };
