import React, { useState } from "react";

import { Grid } from "@mui/material";

import { sizes } from "@/utils";
import glificLogo from "../images/glific_logo.png";
import turnLogo from "../images/turn_logo.png";
import typebotLogo from "../images/typebot_logo.svg";
import ChatManagerCard from "./ChatManagerCard";
import ChatManagerModal from "./ChatManagerModal";
import {
  ChatManagerContentExample,
  TypebotModalContent,
  TurnModalContent,
  GlificModalContent,
} from "./ChatManagerModalContents";

interface ChatManagerInfo {
  logo_src: string;
  name: string;
  ModalContent: React.FC;
}

const ChatManagerGrid = () => {
  const chatManagers: ChatManagerInfo[] = [
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
  ];

  const [modalItem, setModalItem] = useState<ChatManagerInfo | null>(null);
  const handleItemClick = (item: ChatManagerInfo) => {
    setModalItem(item);
  };

  return (
    <>
      <Grid container spacing={sizes.baseGap} style={{ minWidth: 700 }}>
        {chatManagers.map((item, index) => (
          <Grid
            item
            xs={12}
            md={6}
            key={index}
            onClick={() => handleItemClick(item)}
          >
            <ChatManagerCard logo_src={item.logo_src} name={item.name} />
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

export default ChatManagerGrid;
