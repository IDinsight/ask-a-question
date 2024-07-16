import { Card, CardContent } from "@mui/material";
import React from "react";

interface ChatManagerCardInfo {
  logo_src: string;
  name: string;
}

const ChatManagerCard: React.FC<ChatManagerCardInfo> = ({ logo_src, name }) => (
  <Card
    style={{
      justifyContent: "center",
      alignItems: "center",
      display: "flex",
    }}
  >
    <CardContent
      style={{
        height: "200px",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <img
        src={logo_src}
        alt={name}
        style={{ height: "50%", padding: 15, display: "block" }}
      />
    </CardContent>
  </Card>
);

export default ChatManagerCard;
