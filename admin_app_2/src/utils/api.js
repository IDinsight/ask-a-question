// temp read from file
const json = require("./temp_secrets.json");
const backendURL = json.backendURL;
const accessToken = json.accessToken;

const getContentList = async () => {
  console.log("listContent");
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

export const apiCalls = { getContentList };
