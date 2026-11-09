import React, { useState } from "react";
import { IconArrowRight, IconCode } from "@tabler/icons-react";

import glificLogo from "../_images/glific_logo.png";
import turnLogo from "../_images/turn_logo.png";
import typebotLogo from "../_images/typebot_logo.svg";
import ChatManagerModal from "./ConnectionModal";
import {
  TypebotModalContent,
  TurnModalContent,
  GlificModalContent,
  RestApiContent,
} from "./ConnectionModalContents";

interface ConnectionInfo {
  /** Logo image; REST API has none and uses a code icon instead. */
  logo_src?: string;
  name: string;
  description: string;
  ModalContent: React.FC;
}

const CONNECTIONS: ConnectionInfo[] = [
  {
    logo_src: typebotLogo.src,
    name: "Typebot",
    description: "Add question answering to flows built in Typebot.",
    ModalContent: TypebotModalContent,
  },
  {
    logo_src: turnLogo.src,
    name: "Turn",
    description: "Answer questions inside your Turn conversations.",
    ModalContent: TurnModalContent,
  },
  {
    logo_src: glificLogo.src,
    name: "Glific",
    description: "Connect your Glific flows to your content.",
    ModalContent: GlificModalContent,
  },
  {
    name: "REST API",
    description: "Call the search and urgency services directly from your own code.",
    ModalContent: RestApiContent,
  },
];

/**
 * Square tile with the connection's logo (or a code icon for the REST API).
 * White behind logos, since some PNGs have their own white background.
 */
const ConnectionLogo = ({ item }: { item: ConnectionInfo }) => (
  <span
    className={`flex size-10 shrink-0 items-center justify-center border ${
      item.logo_src ? "bg-card" : "bg-muted"
    }`}
  >
    {item.logo_src ? (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={item.logo_src} alt="" className="max-h-7 max-w-8 object-contain" />
    ) : (
      <IconCode className="size-4.5" aria-hidden="true" />
    )}
  </span>
);

/** Cards for each chat manager; each opens a dialog with its setup guide. */
const ConnectionsGrid = () => {
  const [modalItem, setModalItem] = useState<ConnectionInfo | null>(null);

  return (
    <>
      <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {CONNECTIONS.map((item) => (
          <li key={item.name}>
            <button
              type="button"
              onClick={() => setModalItem(item)}
              aria-label={`${item.name}: view setup guide`}
              className="flex h-full w-full flex-col gap-2 border bg-card p-4 text-left shadow-xs transition-colors outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
            >
              <span className="flex items-center gap-3">
                <ConnectionLogo item={item} />
                <span className="text-sm font-semibold">{item.name}</span>
              </span>
              <span className="text-[13px] text-muted-foreground">
                {item.description}
              </span>
              <span className="mt-auto inline-flex items-center gap-1.5 pt-1 text-[13px] font-medium text-primary">
                View setup guide
                <IconArrowRight className="size-3.5" aria-hidden="true" />
              </span>
            </button>
          </li>
        ))}
      </ul>
      <ChatManagerModal
        name={modalItem?.name ?? ""}
        logo={modalItem ? <ConnectionLogo item={modalItem} /> : null}
        ModalContent={modalItem?.ModalContent ?? null}
        open={modalItem !== null}
        onClose={() => setModalItem(null)}
      />
    </>
  );
};

export default ConnectionsGrid;
