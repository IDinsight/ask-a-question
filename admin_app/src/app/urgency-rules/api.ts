import api, { CustomError } from "@/utils/api";
import axios from "axios";
import api, { CustomError } from "@/utils/api";
import axios from "axios";

const getUrgencyRuleList = async (token: string) => {
  try {
    const response = await api.get("/urgency-rules/", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    const customError = error as CustomError;
    let errorMessage = "Error fetching urgency rule list";
    if (customError.message) {
      errorMessage = customError.message;
    }

    throw new Error("Error fetching urgency rule list");
  }
};

const addUrgencyRule = async (rule_text: string, token: string) => {
  try {
    const response = await api.post(
      "/urgency-rules/",
      { urgency_rule_text: rule_text },
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  } catch (customError) {
    if (
      axios.isAxiosError(customError) &&
      customError.response &&
      customError.response.status != 500
    ) {
      throw {
        status: customError.response.status,
        message: customError.response.data?.detail,
      } as CustomError;
    } else {
      throw new Error("Error adding urgency rule");
    }
  }
};

const updateUrgencyRule = async (
  rule_id: number,
  rule_text: string,
  token: string
) => {
  try {
    const response = await api.put(
      `/urgency-rules/${rule_id}`,
      { urgency_rule_text: rule_text },
      {
        headers: { Authorization: `Bearer ${token}` },
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
      throw new Error("Error updating urgency rule");
    }
  }
};

const deleteUrgencyRule = async (rule_id: number, token: string) => {
  try {
    const response = await api.delete(`/urgency-rules/${rule_id}`, {
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
      throw new Error("Error deleting urgency rule");
    }
  }
};
export {
  addUrgencyRule,
  getUrgencyRuleList,
  updateUrgencyRule,
  deleteUrgencyRule,
};
