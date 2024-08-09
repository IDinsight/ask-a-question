import { env } from "next-runtime-env";

const NEXT_PUBLIC_BACKEND_URL: string =
  env("NEXT_PUBLIC_BACKEND_URL") || "http://localhost:8000";

interface ContentBody {
  content_title: string;
  content_text: string;
  content_metadata: Record<string, unknown>;
}

const getUser = async (token: string) => {
  try {
    const response = await fetch(`${NEXT_PUBLIC_BACKEND_URL}/user/`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error("Error fetching user info");
    }

    return await response.json();
  } catch (error) {
    throw error;
  }
};

const getContentList = async ({
  token,
  skip = 0,
  limit = 200,
}: {
  token: string;
  skip?: number;
  limit?: number;
}) => {
  return fetch(
    `${NEXT_PUBLIC_BACKEND_URL}/content/?skip=${skip}&limit=${limit}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    },
  ).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error fetching content list");
    }
  });
};

const getContent = async (content_id: number, token: string) => {
  return fetch(`${NEXT_PUBLIC_BACKEND_URL}/content/${content_id}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  }).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error fetching content");
    }
  });
};

const archiveContent = async (content_id: number, token: string) => {
  return fetch(`${NEXT_PUBLIC_BACKEND_URL}/content/${content_id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  }).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error deleting content");
    }
  });
};

const deleteContent = async (content_id: number, token: string) => {
  return fetch(`${NEXT_PUBLIC_BACKEND_URL}/content/${content_id}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  }).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error deleting content");
    }
  });
};

const editContent = async (
  content_id: number,
  content: ContentBody,
  token: string,
) => {
  return fetch(`${NEXT_PUBLIC_BACKEND_URL}/content/${content_id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(content),
  }).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error editing content");
    }
  });
};

const createContent = async (content: ContentBody, token: string) => {
  try {
    const response = await fetch(`${NEXT_PUBLIC_BACKEND_URL}/content/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(content),
    });

    if (!response.ok) {
      throw response;
    }

    return await response.json();
  } catch (error) {
    throw error;
  }
};

const bulkUploadContents = async (file: File, token: string) => {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(
      `${NEXT_PUBLIC_BACKEND_URL}/content/csv-upload`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      },
    );

    if (response.ok) {
      const data = await response.json();
      return { status: response.status, data };
    } else {
      const errorResponse = await response.json();
      const detail = errorResponse.detail || "An unknown error occurred";
      return { status: response.status, detail: detail };
    }
  } catch (error) {
    throw error;
  }
};

const getUrgencyRuleList = async (token: string) => {
  return fetch(`${NEXT_PUBLIC_BACKEND_URL}/urgency-rules/`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  }).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error fetching urgency rule list");
    }
  });
};

const addUrgencyRule = async (rule_text: string, token: string) => {
  return fetch(`${NEXT_PUBLIC_BACKEND_URL}/urgency-rules/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ urgency_rule_text: rule_text }),
  }).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error adding urgency rule");
    }
  });
};

const updateUrgencyRule = async (
  rule_id: number,
  rule_text: string,
  token: string,
) => {
  return fetch(`${NEXT_PUBLIC_BACKEND_URL}/urgency-rules/${rule_id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ urgency_rule_text: rule_text }),
  }).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error updating urgency rule");
    }
  });
};

const deleteUrgencyRule = async (rule_id: number, token: string) => {
  return fetch(`${NEXT_PUBLIC_BACKEND_URL}/urgency-rules/${rule_id}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  }).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error deleting urgency rule");
    }
  });
};

const getLoginToken = async (username: string, password: string) => {
  const formData = new FormData();
  formData.append("username", username);
  formData.append("password", password);
  const response = await fetch(`${NEXT_PUBLIC_BACKEND_URL}/login`, {
    method: "POST",
    body: formData,
  });

  if (response.ok) {
    let response_json = await response.json();
    return response_json;
  } else {
    console.log("Error fetching login token", response);
    throw response;
  }
};

const getGoogleLoginToken = async (idToken: {
  client_id: string;
  credential: string;
}) => {
  return fetch(`${NEXT_PUBLIC_BACKEND_URL}/login-google`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(idToken),
  }).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error fetching login token");
    }
  });
};

const getEmbeddingsSearch = async (search: string, token: string) => {
  const embeddingUrl = `${NEXT_PUBLIC_BACKEND_URL}/search`;
  return fetch(embeddingUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ query_text: search, generate_llm_response: false }),
  })
    .then((response) => {
      return response.json().then((data) => {
        const responseWithStatus = { status: response.status, ...data };
        return responseWithStatus;
      });
    })
    .catch((error) => {
      console.error("Error:", error);
      throw error;
    });
};

const getLLMResponse = async (search: string, token: string) => {
  const llmResponseUrl = `${NEXT_PUBLIC_BACKEND_URL}/search`;
  return fetch(llmResponseUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ query_text: search, generate_llm_response: true }),
  })
    .then((response) => {
      return response.json().then((data) => {
        const responseWithStatus = { status: response.status, ...data };
        return responseWithStatus;
      });
    })
    .catch((error) => {
      console.error("Error:", error);
      throw error;
    });
};

const postResponseFeedback = async (
  query_id: number,
  feedback_sentiment: string,
  feedback_secret_key: string,
  token: string,
) => {
  const feedbackUrl = `${NEXT_PUBLIC_BACKEND_URL}/response-feedback`;
  return fetch(feedbackUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      query_id: query_id,
      feedback_sentiment: feedback_sentiment,
      feedback_secret_key: feedback_secret_key,
    }),
  }).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error sending response feedback");
    }
  });
};

const getQuestionStats = async (token: string) => {
  return fetch(`${NEXT_PUBLIC_BACKEND_URL}/dashboard/question_stats`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  }).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error fetching questions statistics");
    }
  });
};

const getUrgencyDetection = async (search: string, token: string) => {
  const urgencyDetectionUrl = `${NEXT_PUBLIC_BACKEND_URL}/urgency-detect`;
  return fetch(urgencyDetectionUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message_text: search }),
  })
    .then((response) => {
      if (response.ok) {
        let resp = response.json();
        return resp;
      } else {
        return response.json().then((errData) => {
          throw new Error(
            `Error fetching urgency detection response: ${errData.message} Status: ${response.status}`,
          );
        });
      }
    })
    .catch((error) => {
      throw new Error(
        `Error POSTING to urgency detection URL at ${urgencyDetectionUrl}. ` +
          error.message,
      );
    });
};

const createTag = async (tag: string, token: string) => {
  return fetch(`${NEXT_PUBLIC_BACKEND_URL}/tag/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ tag_name: tag }),
  }).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error creating tag");
    }
  });
};

const getTagList = async (token: string) => {
  return fetch(`${NEXT_PUBLIC_BACKEND_URL}/tag/`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  }).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error fetching tag list");
    }
  });
};

const deleteTag = async (tag_id: number, token: string) => {
  return fetch(`${NEXT_PUBLIC_BACKEND_URL}/tag/${tag_id}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  }).then((response) => {
    if (response.ok) {
      let resp = response.json();
      return resp;
    } else {
      throw new Error("Error deleting tag");
    }
  });
};
export const apiCalls = {
  getUser,
  getContentList,
  getContent,
  archiveContent,
  deleteContent,
  editContent,
  createContent,
  bulkUploadContents,
  getUrgencyRuleList,
  addUrgencyRule,
  updateUrgencyRule,
  deleteUrgencyRule,
  getLoginToken,
  getGoogleLoginToken,
  getEmbeddingsSearch,
  getLLMResponse,
  postResponseFeedback,
  getQuestionStats,
  getUrgencyDetection,
  createTag,
  getTagList,
  deleteTag,
};
