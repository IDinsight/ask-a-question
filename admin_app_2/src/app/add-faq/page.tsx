import React from "react";
const chats = [
  {
    sender: "user",
    message: "Hello, how can I help you?",
  },
  {
    sender: "bot",
    message: "I am a bot",
  },
  {
    sender: "user",
    message: "I need help with my account",
  },
  {
    sender: "bot",
    message: "I can help you with that",
  },
];
const ChatBox = () => {
  return (
    <div className="chat-box">
      {chats.map((chat, index) => (
        <div key={index} className="chat">
          <div className="chat-sender">{chat.sender}</div>
          <div className="chat-message">{chat.message}</div>
        </div>
      ))}
    </div>
  );
};

export default ChatBox;
