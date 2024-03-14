// temp read from file
const json = require("./temp_secrets.json");
const backendURL = json.backendURL;
const accessToken = json.accessToken;

const getContentList = async () => {
  return fetch(`${backendURL}/content/list`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
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
  return fetch(`${backendURL}/content/${content_id}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
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

export const apiCalls = { getContentList, getContent };
