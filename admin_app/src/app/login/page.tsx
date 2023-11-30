"use client";

import React, { useState } from "react";

const backendUrl: string =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export default function Login() {
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [incorrectLogin, setIncorrectLogin] = useState(false);

  const onLogin = async () => {
    const formData = new FormData();
    formData.append("username", loginForm.username);
    formData.append("password", loginForm.password);
    const response = await fetch(`${backendUrl}/login`, {
      method: "POST",
      body: formData,
    });

    if (response.status === 200) {
      const data = await response.json();
      localStorage.setItem("token", JSON.stringify(data));
      window.location.href = "/";
    } else {
      console.log("Login failed");
      setIncorrectLogin(true);
    }
  };

  return (
    <div className="bg-gray-200 dark:bg-gray-800 h-screen overflow-hidden flex items-center justify-center">
      <div className="bg-white lg:w-6/12 md:7/12 w-8/12 shadow-3xl rounded-xl">
        <div className="bg-blue-600 dark:bg-gray-800 shadow shadow-gray-200 absolute left-1/2 transform -translate-x-1/2 -translate-y-1/2 rounded-full p-4 md:p-8">
          <svg
            fill="none"
            stroke="white"
            width="32"
            height="32"
            strokeWidth="1.5"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
            ></path>
          </svg>
        </div>
        <form className="p-12 md:p-24">
          <div className="flex items-bottom text-red-500 mb-6 md:mb-8">
            <p className="absolute ">
              {incorrectLogin ? "Incorrect username or password" : null}
            </p>
          </div>
          <div className="flex items-center text-lg mb-6 md:mb-8">
            <svg className="absolute ml-3" width="24" viewBox="0 0 24 24">
              <path d="M20.822 18.096c-3.439-.794-6.64-1.49-5.09-4.418 4.72-8.912 1.251-13.678-3.732-13.678-5.082 0-8.464 4.949-3.732 13.678 1.597 2.945-1.725 3.641-5.09 4.418-3.073.71-3.188 2.236-3.178 4.904l.004 1h23.99l.004-.969c.012-2.688-.092-4.222-3.176-4.935z" />
            </svg>
            <input
              type="text"
              id="username"
              className="bg-gray-200 rounded pl-12 py-2 md:py-4 focus:outline-none w-full text-black"
              placeholder="Username"
              onChange={(e) =>
                setLoginForm({ ...loginForm, username: e.target.value })
              }
            />
          </div>
          <div className="flex items-center text-lg mb-6 md:mb-8">
            <svg className="absolute ml-3" viewBox="0 0 24 24" width="24">
              <path d="m18.75 9h-.75v-3c0-3.309-2.691-6-6-6s-6 2.691-6 6v3h-.75c-1.24 0-2.25 1.009-2.25 2.25v10.5c0 1.241 1.01 2.25 2.25 2.25h13.5c1.24 0 2.25-1.009 2.25-2.25v-10.5c0-1.241-1.01-2.25-2.25-2.25zm-10.75-3c0-2.206 1.794-4 4-4s4 1.794 4 4v3h-8zm5 10.722v2.278c0 .552-.447 1-1 1s-1-.448-1-1v-2.278c-.595-.347-1-.985-1-1.722 0-1.103.897-2 2-2s2 .897 2 2c0 .737-.405 1.375-1 1.722z" />
            </svg>
            <input
              type="password"
              id="password"
              className="bg-gray-200 rounded pl-12 py-2 md:py-4 focus:outline-none w-full text-black"
              placeholder="Password"
              onChange={(e) =>
                setLoginForm({ ...loginForm, password: e.target.value })
              }
            />
          </div>
          <button
            type="button"
            className="bg-gradient-to-b from-blue-500 to-blue-700 dark:from-gray-700 dark:to-gray-900 font-medium p-2 md:p-4 text-white uppercase w-full rounded"
            onClick={onLogin}
          >
            Login
          </button>
        </form>
      </div>
    </div>
  );
}
