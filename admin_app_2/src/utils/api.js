// Temp read bearer token from file. Will be removed when auth is implemented.
const json = require("../../temp_secrets.json");
const ACCESS_TOKEN = json.ACCESS_TOKEN;
const BACKEND_ROOT_PATH = "http://localhost:8000";

const getContentList = async () => {
  return fetch(`${BACKEND_ROOT_PATH}/content/list`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${ACCESS_TOKEN}`,
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

const getContent = async (content_id) => {
  return fetch(`${BACKEND_ROOT_PATH}/content/${content_id}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${ACCESS_TOKEN}`,
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

const deleteContent = async (content_id) => {
  return fetch(`${BACKEND_ROOT_PATH}/content/${content_id}/delete`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${ACCESS_TOKEN}`,
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

const createContent = async (content) => {
  return fetch(`${BACKEND_ROOT_PATH}/content/create`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${ACCESS_TOKEN}`,
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

const editContent = async (content_id, content) => {
  return fetch(`${BACKEND_ROOT_PATH}/content/${content_id}/edit`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${ACCESS_TOKEN}`,
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

export const apiCalls = {
  getContentList,
  getContent,
  deleteContent,
  createContent,
  editContent,
};
