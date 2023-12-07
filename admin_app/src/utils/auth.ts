import { jwtDecode } from "jwt-decode";

export type AccessLevel = "fullaccess" | "readonly" | null;
export type AccessToken = string | null;

export const getAccessLevel = (): [boolean, AccessLevel, AccessToken] => {
  if (typeof window !== "undefined") {
    const tokenString = localStorage.getItem("token");
    if (tokenString) {
      const token = JSON.parse(tokenString);
      const decodedAccessToken = jwtDecode(token.access_token);
      const isTokenValid = decodedAccessToken.exp
        ? decodedAccessToken.exp * 1000 > Date.now()
        : false;
      if (isTokenValid) {
        return [true, token.access_level, token.access_token];
      } else {
        return [false, null, null];
      }
    } else {
      return [false, null, null];
    }
  } else {
    console.log("window is undefined");
    return [false, null, null];
  }
};
