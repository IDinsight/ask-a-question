import React, { useState } from "react";
import Markdown from "react-markdown";
import TextAreaAutosize from "react-textarea-autosize";
import { backendUrl } from "../components/Config";

export type Message = {
  type: "human" | "ai";
  content: string;
};

interface SubmitMessageProps {
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  messages: Message[];
}
export const SubmitMessage: React.FC<SubmitMessageProps> = ({
  setMessages,
  messages,
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const formData = new FormData(form);

    const formJson = Object.fromEntries(formData.entries());
    console.log(formJson.query_text.toString());

    const queryMessage: Message = {
      type: "human",
      content: formJson.query_text.toString(),
    };

    setMessages([...messages, queryMessage]);

    // pop-up to get token if no token present
    let token: string | null = localStorage.getItem("apiToken");
    if (token === null) {
      token = prompt("Please enter your API token");
      localStorage.setItem("apiToken", token || "");
    }
    const headers = {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    };

    // Send message to server
    setIsLoading(true);
    fetch(`${backendUrl}/embeddings-search`, {
      method: form.method,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(formJson),
    })
      .then((response) => {
        if (response.ok) {
          return response.json();
        } else {
          throw new Error("Could not access API");
        }
      })
      .then((data) => {
        console.log(data);
        setMessages([
          ...messages,
          queryMessage,
          {
            type: "ai",
            content: "```\n" + JSON.stringify(data, null, 2) + "\n```",
          },
        ]);
      })
      .finally(() => setIsLoading(false));
  };

  return (
    <form
      className="flex absolute bottom-0 left-0 w-full px-2 space-x-2"
      method="post"
      onSubmit={handleSubmit}
    >
      <TextAreaAutosize
        className="bg-gray-200 dark:bg-gray-800 p-2 flex-1 rounded-md border border-neutral-200"
        name="query_text"
        minRows={1}
      />
      <button
        className="bg-blue-500 text-white rounded-md px-2 py-1 flex justify-center items-center"
        type="submit"
      >
        {isLoading ? (
          <svg
            className="animate-spin h-5 w-5 text-white"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
        ) : (
          "Send"
        )}
      </button>
    </form>
  );
};

interface ChatProps {
  message: Message;
}
export const ChatMessage: React.FC<ChatProps> = ({ message }) => {
  return (
    <div
      className={`flex-1 flex-col flex-grow ${
        message.type === "human" ? "justify-end" : "justify-start"
      }`}
    >
      <div
        className={`flex text-ellipsis flex-col  ${
          message.type === "human"
            ? "bg-blue-500 text-white dark:bg-gray-800 dark:text-gray-400"
            : "text-cyan-900 dark:text-cyan-200"
        } rounded-md p-2 m-2`}
      >
        <Markdown>
          {message.type === "human"
            ? "**YOU:** " + message.content
            : "**> AAQ:** \n" + message.content}
        </Markdown>
      </div>
    </div>
  );
};
