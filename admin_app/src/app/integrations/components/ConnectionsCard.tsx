import { Card, CardContent } from "@mui/material";
import React from "react";

interface ConnectionCardInfo {
  logo_src: string;
  name: string;
}

const ConnectionCard: React.FC<ConnectionCardInfo> = ({ logo_src, name }) => (
  <Card
    style={{
      justifyContent: "center",
      alignItems: "center",
      display: "flex",
      cursor: "pointer",
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

export default ConnectionCard;
