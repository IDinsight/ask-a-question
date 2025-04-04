import { Workspace } from "@/components/WorkspaceMenu";
import api, { CustomError } from "@/utils/api";
import axios from "axios";
interface UserBody {
  user_id?: number;
  username: string;
  role: "admin" | "read_only";
  is_default_workspace?: boolean[];
  user_workspaces?: Workspace[];
}
interface UserBodyPassword extends UserBody {
  password: string;
}
interface UserBodyUpdate extends Omit<UserBody, "is_default_workspace"> {
  is_default_workspace?: boolean;
  workspace_name: string;
}

const editUser = async (user_id: number, user: UserBodyUpdate, token: string) => {
  try {
    const response = await api.put(`/user/${user_id}`, user, {
      headers: { Authorization: `Bearer ${token}` },
    });
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
      throw new Error("Error editing workspace");
    }
  }
};

const createUser = async (user: UserBodyPassword, token: string) => {
  try {
    const response = await api.post("/user/", user, {
      headers: { Authorization: `Bearer ${token}` },
    });
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
      throw new Error("Error creating user");
    }
  }
};
const createNewUser = async (
  username: string,
  password: string,
  workspace_name: string,
  role: string,
  token: string,
) => {
  try {
    const user = { username: username, password, role, workspace_name };
    const response = await api.post("/user/", user, {
      headers: { Authorization: `Bearer ${token}` },
    });
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
    }
    throw new Error("Error creating user");
  }
};
const getUserList = async (token: string) => {
  try {
    const response = await api.get("/user/", {
      headers: { Authorization: `Bearer ${token}` },
    });
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
      throw new Error("Error fetching user list");
    }
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
      throw new Error("Error fetching user info");
    }
  }
};

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

const checkIfUsernameExists = async (
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
  try {
    const response = await api.post("/workspace/switch-workspace", data, {
      headers: { Authorization: `Bearer ${token}` },
    });
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
      throw new Error("Error fetching workspace login token");
    }
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
      throw new Error("Error creating workspace");
    }
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
      throw new Error("Error editing workspace");
    }
  }
};
const addUserToWorkspace = async (
  username: string,
  workspace_name: string,
  role: string,
  token: string,
) => {
  try {
    const response = await api.post(
      "/user/add-existing-user-to-workspace",
      {
        username,
        role,
        workspace_name,
        is_default_workspace: true,
      },
      {
        headers: { Authorization: `Bearer ${token}` },
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
      throw new Error("Error adding user to workspace");
    }
  }
};
const removeUserFromWorkspace = async (
  user_id: number,
  workspace_name: string,
  token: string,
) => {
  try {
    const response = await api.delete(
      `/user/${user_id}?remove_from_workspace_name=${workspace_name}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return response.data;
  } catch (customError) {
    if (
      axios.isAxiosError(customError) &&
      customError.response &&
      customError.response.status === 403
    ) {
      throw {
        status: 403,
        message: "You cannot remove the last admin from the workspace.",
      } as CustomError;
    } else if (
      axios.isAxiosError(customError) &&
      customError.response &&
      customError.response.status !== 500
    ) {
      throw {
        status: 404,
        message: customError.response.data?.detail,
      } as CustomError;
    }
    throw new Error("Error removing user from workspace");
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
  createNewUser,
  removeUserFromWorkspace,
};
export type { UserBody, UserBodyPassword, UserBodyUpdate };
