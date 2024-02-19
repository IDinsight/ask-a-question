"use client";
import React from "react";
export type AccessLevel = "fullaccess" | "readonly" | null;
export type AccessToken = string | null;
//create auth context with token and access level

const AuthContext = React.createContext({
  user: null,
  signin: (email: string, password: string) => {},
  signout: () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const auth = useProvideAuth();
  return (
    <AuthContext.Provider
      value={
        auth as {
          user: null;
          signin: (email: string, password: string) => void;
          signout: () => void;
        }
      }
    >
      {children}
    </AuthContext.Provider>
  );
};
export const useAuth = () => React.useContext(AuthContext);

function useProvideAuth() {
  const [user, setUser] = React.useState<{
    email: string;
    password: string;
  } | null>(null);

  // Wrap any local storage methods we want to use making sure to save the user to state.
  const signin = (email: string, password: string) => {
    // replace this with your sign in logic
    const user = { email, password };
    localStorage.setItem("token", JSON.stringify(user));
    setUser(user);
  };

  const signout = () => {
    console.log("signing out");
    localStorage.removeItem("token");
    setUser(null);
  };

  React.useEffect(() => {
    const user = JSON.parse(localStorage.getItem("token") as string);
    if (user) {
      setUser({ email: user.email, password: user.password });
    }
  }, []);

  // Return the user object and auth methods
  return {
    user,
    signin,
    signout,
  };
}

export const getAccessLevel = (): [
  boolean,
  AccessLevel,
  AccessToken | undefined
] => {
  if (typeof window !== "undefined") {
    const tokenString = localStorage.getItem("token");
    if (tokenString) {
      return [true, "fullaccess", tokenString];
    }
    /*
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
    return [false, nußll, null];
  }
  */
  }
  return [false, null, null];
};
