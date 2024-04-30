const BACKEND_ROOT_PATH: string =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

interface ContentBody {
  content_title: string;
  content_text: string;
  content_language: string;
  content_metadata: Record<string, unknown>;
}

const getContentList = async (token: string) => {
  return fetch(`${BACKEND_ROOT_PATH}/content/`, {
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
      throw new Error("Error fetching content list");
    }
  });
};

const getContent = async (content_id: number, token: string) => {
  return fetch(`${BACKEND_ROOT_PATH}/content/${content_id}`, {
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

const deleteContent = async (content_id: number, token: string) => {
  return fetch(`${BACKEND_ROOT_PATH}/content/${content_id}`, {
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
  return fetch(`${BACKEND_ROOT_PATH}/content/${content_id}`, {
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
  return fetch(`${BACKEND_ROOT_PATH}/content/`, {
    method: "POST",
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
      throw new Error("Error creating content");
    }
  });
};

const getUrgencyRuleList = async (token: string) => {
  return fetch(`${BACKEND_ROOT_PATH}/urgency-rule/`, {
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

const getLoginToken = async (username: string, password: string) => {
  const formData = new FormData();
  formData.append("username", username);
  formData.append("password", password);
  return fetch(`${BACKEND_ROOT_PATH}/login`, {
    method: "POST",
    body: formData,
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
  const embeddingUrl = `${BACKEND_ROOT_PATH}/embeddings-search`;
  return fetch(embeddingUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ query_text: search }),
  })
    .then((response) => {
      if (response.ok) {
        let resp = response.json();
        return resp;
      } else {
        return response.json().then((errData) => {
          throw new Error(
            `Error fetching embeddings response: ${errData.message} Status: ${response.status}`,
          );
        });
      }
    })
    .catch((error) => {
      throw new Error(
        `Error POSTING to embedding search URL at ${embeddingUrl}. ` +
          error.message,
      );
    });
};

const getLLMResponse = async (search: string, token: string) => {
  const llmResponseUrl = `${BACKEND_ROOT_PATH}/llm-response`;
  return fetch(llmResponseUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ query_text: search }),
  })
    .then((response) => {
      if (response.ok) {
        let resp = response.json();
        return resp;
      } else {
        return response.json().then((errData) => {
          throw new Error(
            `Error fetching llm response: ${errData.message} Status: ${response.status}`,
          );
        });
      }
    })
    .catch((error) => {
      throw new Error(
        `Error POSTING to LLM search URL at ${llmResponseUrl}. ` +
          error.message,
      );
    });
};

export const apiCalls = {
  getContentList,
  getContent,
  deleteContent,
  editContent,
  createContent,
  getUrgencyRuleList,
  getLoginToken,
  getEmbeddingsSearch,
  getLLMResponse,
};
