// CardPage.tsx
import React, { useState } from "react";
import { PencilIcon, TrashIcon } from "@heroicons/react/20/solid";

export type Content = {
  content_id: string;
  content_title: string;
  content_text: string;
  content_language: string;
};

interface ContentCardProps {
  content: Content;
  editMe: (content: Content) => void;
  showEditButton: boolean;
  deleteMe: (content: Content) => void;
}

export const ContentCard: React.FC<ContentCardProps> = ({
  content,
  editMe,
  showEditButton,
  deleteMe,
}) => {
  const [isExpanded, setToggleExpand] = useState(false);

  return (
    <div
      key={content.content_id}
      className={`relative min-h-[10rem] p-6 bg-white border border-gray-200 rounded-lg shadow dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-100 ${
        isExpanded ? "row-span-2 col-span-2" : ""
      }`}
      onDoubleClick={() => setToggleExpand(!isExpanded)}
    >
      {/* Trash Icon Container */}
      <div className="absolute top-2 right-2">
        {showEditButton ? (
          <TrashIcon
            className="w-4 h-4 text-gray-500 cursor-pointer hover:text-red-200"
            onClick={() => deleteMe(content)}
          />
        ) : null}
      </div>

      {/* Pencil Icon Container */}
      <div className="absolute bottom-2 right-2">
        {showEditButton ? (
          <PencilIcon
            data-modal-target="edit-content-modal"
            data-modal-toggle="edit-content-modal"
            className="w-4 h-4 text-gray-500 cursor-pointer hover:text-red-200"
            onClick={() => editMe(content)}
          />
        ) : null}
      </div>
      <p
        className={`mb-3 overflow-auto whitespace-pre-line text-sm text-gray-700 dark:text-gray-400 font-bold ${
          isExpanded ? "line-clamp-[12]" : "line-clamp-4"
        }`}
      >
        {content.content_title}
      </p>
      <p
        className={`mb-3 overflow-auto whitespace-pre-line text-sm text-gray-700 dark:text-gray-400 ${
          isExpanded ? "line-clamp-[12]" : "line-clamp-4"
        }`}
      >
        {content.content_text}
      </p>
      <p
        className={`mb-3 font-light overflow-auto whitespace-pre-line text-sm text-gray-500 dark:text-gray-600 absolute bottom-0 float-left ${
          isExpanded ? "line-clamp-[12] py-3" : "line-clamp-4"
        }`}
      >
        {content.content_language}
      </p>
      {isExpanded ? (
        <p className="mb-3 text-xs font-light text-gray-800 dark:text-gray-600 absolute p-3 bottom-0 right-2 float-right">
          id: {content.content_id}
        </p>
      ) : null}
    </div>
  );
};
