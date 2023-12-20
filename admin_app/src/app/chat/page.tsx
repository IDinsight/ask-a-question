"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  SubmitMessage,
  ChatMessage,
  Message,
} from "../../components/ChatComponents";
import { getAccessLevel, AccessLevel, AccessToken } from "../../utils/auth";

export default function ChatPage() {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const [isAuthenticated, access_level, access_token]: [
      boolean | null,
      AccessLevel,
      AccessToken,
    ] = getAccessLevel();

    if (!isAuthenticated) {
      router.push("/login?fromPage=" + encodeURIComponent(pathname));
    }
  }, [router, pathname]);

  const [messages, setMessages] = useState<Message[]>([]);
  const endOfMessagesRef = useRef<null | HTMLDivElement>(null);

  useEffect(() => {
    if (endOfMessagesRef.current) {
      endOfMessagesRef.current.scrollIntoView({
        behavior: "auto",
        block: "end",
      });
    }
  }, [messages]);

  // The following is for testing. I'll remove it in the next PR

  // useEffect(() => {
  //   setMessages([
  //     { type: "human", content: "This is the first row of content" },
  //     { type: "ai", content: "This is the second row of content" },
  //     {
  //       type: "human",
  //       content:
  //         "This is the third row of content. " +
  //         "This is a lot more content that may be " +
  //         "wrapped across multiple lines",
  //     },
  //     { type: "ai", content: "This is the fourth row of content" },
  //     { type: "human", content: "This is the fifth row of content" },
  //     { type: "ai", content: "This is the sixth row of content" },
  //     { type: "human", content: "This is the seventh row of content" },
  //     { type: "ai", content: "This is the eighth row of content" },
  //     { type: "human", content: "This is the ninth row of content" },
  //     { type: "ai", content: "This is the tenth row of content" },
  //     { type: "human", content: "This is the eleventh row of content" },
  //     { type: "ai", content: "This is the twelfth row of content" },
  //     { type: "human", content: "This is the thirteenth row of content" },
  //   ]);
  // }, []);

  return (
    <>
      <main className="flex flex-grow justify-center h-full py-4 border-neutral-800 rounded-md">
        <div className="flex flex-col w-full h-full max-w-screen-lg">
          <div className="flex-1 mb-20 relative w-full overflow-y-auto">
            <div className="flex-1 min-w-full">
              {messages.map((message, idx) => (
                <ChatMessage key={idx} message={message} />
              ))}
              <div ref={endOfMessagesRef} />
            </div>
          </div>
          <div className="flex relative w-full px-2">
            <SubmitMessage setMessages={setMessages} messages={messages} />
          </div>
        </div>
      </main>
    </>
  );
}
