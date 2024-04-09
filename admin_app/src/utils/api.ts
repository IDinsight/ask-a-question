const BACKEND_ROOT_PATH: string =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

interface ContentBody {
  content_title: string;
  content_text: string;
  language_id: number;
  content_metadata: Record<string, unknown>;
}

const getContentList = async (token: string) => {
  return fetch(`${BACKEND_ROOT_PATH}/content/list`, {
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
const getContentListLanding = async (language: string, token: string) => {

  return fetch(`${BACKEND_ROOT_PATH}/content/landing?language=${language}`, {
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

const getContent = async (content_id: number, language: string | null, token: string) => {
  const languageQuery = language ? `?language=${encodeURIComponent(language)}` : '';
  const uri = `${BACKEND_ROOT_PATH}/content/${content_id}${languageQuery}`;

  return fetch(uri, {

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

const deleteContent = async (content_id: number, language_id: number | null, token: string) => {
  const languageQuery = language_id ? `?language_id=${encodeURIComponent(language_id)}` : '';
  const uri = `${BACKEND_ROOT_PATH}/content/${content_id}${languageQuery}`;

  return fetch(uri, {
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
  language_id: number,
  content: ContentBody,
  token: string,
) => {
  return fetch(`${BACKEND_ROOT_PATH}/content/${content_id}?language_id=${language_id}`, {
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

const addContent = async (content: ContentBody, token: string) => {
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
      throw new Error("Error adding content");
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

const getLanguageList = async (token: string) => {
  return fetch(`${BACKEND_ROOT_PATH}/language/`, {
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
const getDefaultLanguage = async (token: string) => {
  return fetch(`${BACKEND_ROOT_PATH}/language/default`, {
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

export const apiCalls = {
  getContentList,
  getContentListLanding,
  getContent,
  deleteContent,
  editContent,
  addContent,
  getLanguageList,
  getDefaultLanguage,
  getLoginToken,
};
