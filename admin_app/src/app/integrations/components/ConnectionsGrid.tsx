import React, { useState } from "react";

import { Grid } from "@mui/material";

import { sizes } from "@/utils";
import glificLogo from "../images/glific_logo.png";
import turnLogo from "../images/turn_logo.png";
import typebotLogo from "../images/typebot_logo.svg";
import api_logo from "../images/api_logo.png";
import ConnectionCard from "./ConnectionsCard";
import ChatManagerModal from "./ConnectionModal";
import {
  TypebotModalContent,
  TurnModalContent,
  GlificModalContent,
  RestApiContent,
} from "./ConnectionModalContents";

interface ConnectionInfo {
  logo_src: string;
  name: string;
  ModalContent: React.FC;
}

const ConnectionsGrid = () => {
  const Connections: ConnectionInfo[] = [
    {
      logo_src: typebotLogo.src,
      name: "Typebot",
      ModalContent: TypebotModalContent,
    },
    {
      logo_src: turnLogo.src,
      name: "Turn",
      ModalContent: TurnModalContent,
    },
    {
      logo_src: glificLogo.src,
      name: "Glific",
      ModalContent: GlificModalContent,
    },
    {
      logo_src: api_logo.src,
      name: "REST API",
      ModalContent: RestApiContent,
    },
  ];

  const [modalItem, setModalItem] = useState<ConnectionInfo | null>(null);
  const handleItemClick = (item: ConnectionInfo) => {
    setModalItem(item);
  };

  return (
    <>
      <Grid container spacing={sizes.baseGap} style={{ minWidth: 100 }}>
        {Connections.map((item, index) => (
          <Grid item xs={12} md={6} key={index} onClick={() => handleItemClick(item)}>
            <ConnectionCard logo_src={item.logo_src} name={item.name} />
          </Grid>
        ))}
      </Grid>
      {modalItem && (
        <ChatManagerModal
          logo_src={modalItem.logo_src}
          ModalContent={modalItem.ModalContent}
          open={Boolean(modalItem)}
          onClose={() => setModalItem(null)}
        />
      )}
    </>
  );
};

export default ConnectionsGrid;
