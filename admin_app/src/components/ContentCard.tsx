// CardPage.tsx
"use client";
import React, { useState } from "react";
import { PencilIcon, TrashIcon } from "@heroicons/react/20/solid";

export type Content = {
  content_id: string;
  content_text: string;
};

interface ContentCardProps extends Content {
  expanded: boolean;
  deleteMe: (id: string) => void;
  editMe: (content: Content) => void;
}

export const ContentCard: React.FC<ContentCardProps> = (
  card: ContentCardProps,
) => {
  const [expanded, setToggleExpand] = useState(false);

  return (
    <div
      key={card.content_id}
      className={`relative min-h-[10rem] p-6 bg-white border border-gray-200 rounded-lg shadow dark:bg-gray-800 dark:border-gray-700 ${
        expanded ? "row-span-2 col-span-2" : ""
      }`}
      onDoubleClick={() => setToggleExpand(!expanded)}
    >
      {/* Icons Container */}
      <div className="absolute flex top-2 right-2 ">
        <PencilIcon
          data-modal-target="edit-content-modal"
          data-modal-toggle="edit-content-modal"
          className="w-3 h-3 text-gray-500 cursor-pointer hover:text-red-200"
          onClick={() =>
            card.editMe({
              content_id: card.content_id,
              content_text: card.content_text,
            })
          }
        />
        <TrashIcon
          className="w-3 h-3 text-gray-500 cursor-pointer hover:text-red-200"
          onClick={() => card.deleteMe(card.content_id)}
        />
      </div>
      <p
        className={`mb-3 overflow-auto whitespace-pre-line text-sm text-gray-700 dark:text-gray-400 ${
          expanded ? "line-clamp-[12]" : "line-clamp-4"
        }`}
      >
        {card.content_text}
      </p>
      {expanded ? (
        <p className="mb-3 text-xs font-light text-gray-800 dark:text-gray-600 absolute p-1 bottom-0 right-2 float-right">
          id: {card.content_id}
        </p>
      ) : null}
    </div>
  );
};
