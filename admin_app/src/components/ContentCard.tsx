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
  showEditButton: boolean;
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
        {card.showEditButton ? (
          <>
            <TrashIcon
              className="w-6 h-6 text-gray-500 cursor-pointer hover:text-red-200"
              onClick={() => card.deleteMe(card.content_id)}
            />
          </>
        ) : null}
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
