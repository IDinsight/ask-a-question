import api from "@/utils/api";

const getUrgencyRuleList = async (token: string) => {
  try {
    const response = await api.get("/urgency-rules/", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
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
      },
    );
    return response.data;
  } catch (error) {
    throw new Error("Error adding urgency rule");
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
  } catch (error) {
    throw new Error("Error updating urgency rule");
  }
};

const deleteUrgencyRule = async (rule_id: number, token: string) => {
  try {
    const response = await api.delete(`/urgency-rules/${rule_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error deleting urgency rule");
  }
};
export { addUrgencyRule, getUrgencyRuleList, updateUrgencyRule, deleteUrgencyRule };
