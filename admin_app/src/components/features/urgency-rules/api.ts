import api, { handleApiError } from "@/utils/api";

const getUrgencyRuleList = async (token: string) => {
  try {
    const response = await api.get("/urgency-rules/", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (customError) {
    let error_message = "Error fetching urgency rule list";
    handleApiError(customError, error_message);
  }
};

const addUrgencyRule = async (rule_text: string, token: string) => {
  try {
    const response = await api.post(
      "/urgency-rules/",
      { urgency_rule_text: rule_text },
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return response.data;
  } catch (customError) {
    let error_message = "Error adding urgency rule";
    handleApiError(customError, error_message);
  }
};

const updateUrgencyRule = async (rule_id: number, rule_text: string, token: string) => {
  try {
    const response = await api.put(
      `/urgency-rules/${rule_id}`,
      { urgency_rule_text: rule_text },
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return response.data;
  } catch (customError) {
    let error_message = "Error updating urgency rule";
    handleApiError(customError, error_message);
  }
};

const deleteUrgencyRule = async (rule_id: number, token: string) => {
  try {
    const response = await api.delete(`/urgency-rules/${rule_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (customError) {
    let error_message = "Error deleting urgency rule";
    handleApiError(customError, error_message);
  }
};
export { addUrgencyRule, getUrgencyRuleList, updateUrgencyRule, deleteUrgencyRule };

/* Test sidebar: classify a message (moved from utils/api.ts). */
const getUrgencyDetection = async (search: string, token: string) => {
  try {
    const response = await api.post(
      "/urgency-detect",
      { message_text: search },
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return response.data;
  } catch (error: any) {
    handleApiError(error, "Error fetching urgency detection");
    console.error("Error fetching urgency detection", error.message);
  }
};

export { getUrgencyDetection };
