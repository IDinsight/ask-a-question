import { jwtDecode } from "jwt-decode";
import { useEffect, useState } from "react";

const IsFullAccess = (): boolean => {
  const [hasFullAccess, setHasFullAccess] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const tokenString = localStorage.getItem("token");
      if (tokenString) {
        const token = JSON.parse(tokenString);
        const decodedAccessToken = jwtDecode(token.access_token);
        const isTokenValid = decodedAccessToken.exp
          ? decodedAccessToken.exp * 1000 > Date.now()
          : false;
        if (isTokenValid && token.access_level == "fullaccess") {
          setHasFullAccess(true);
        } else {
          setHasFullAccess(false);
        }
      } else {
        window.location.href = "/login";
      }
    } else {
      return setHasFullAccess(false);
    }
  }, []);

  return hasFullAccess;
};

export default IsFullAccess;
