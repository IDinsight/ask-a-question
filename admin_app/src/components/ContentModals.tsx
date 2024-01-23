// ConfirmDelete.jsx
import React, { useEffect } from "react";
import { Content, ContentInEdit, Language } from "./ContentCard";
import { XMarkIcon } from "@heroicons/react/20/solid";
import TextareaAutosize from "react-textarea-autosize";

interface ConfirmDeleteProps {
  cardToDelete: Content;
  onDeleteConfirm: (card: Content) => void;
  onClose: () => void;
  title: string;
}
export const ConfirmDelete: React.FC<ConfirmDeleteProps> = ({
  cardToDelete,
  onDeleteConfirm,
  onClose,
  title,
}) => {
  return (
    <div onClick={onClose}>
      <div className="fixed inset-0 z-10 overflow-y-auto flex items-center justify-center">
        <div className="backdrop-blur bg-opacity-10 absolute inset-0"></div>
        <div
          className="bg-gray-200 dark:bg-gray-700 p-4 rounded-lg z-20 shadow-lg dark:outline-none"
          onClick={(e) => e.stopPropagation()}
        >
          <h3
            className="text-lg dark:text-white leading-6 font-medium text-gray-900"
            id="modal-title"
          >
            {title}
          </h3>
          <div className="mt-2">
            <p className="text-sm text-red-600 ">
              ⚠️ This action cannot be undone.
            </p>
          </div>
          <div className="mt-2 italic text-sm">
            <p className="dark:text-gray-400 text-ellipsis overflow-hidden max-w-md max-h-20 font-bold">
              {cardToDelete.content_title}
            </p>
          </div>
          <div className="mt-2 italic text-sm">
            <p className="dark:text-gray-400 text-ellipsis overflow-hidden max-w-md max-h-20">
              {cardToDelete.content_text}
            </p>
          </div>
          <div className="mt-2 italic text-sm">
            <p className="dark:text-gray-300 text-ellipsis overflow-hidden max-w-md max-h-20">
              Language: {cardToDelete.content_language}
            </p>
          </div>
          <div className="mt-2">
            <p className="text-[10px] dark:text-gray-400">
              Content ID: {cardToDelete.content_id}
            </p>
          </div>
          <div className="dark:bg-gray-700 px-4 py-3 sm:flex sm:flex-row-reverse mt-4 rounded-b-lg">
            <button
              type="button"
              className="w-auto inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-red-600 text-base font-medium text-white hover:bg-red-700 focus:outline-none sm:ml-3"
              onClick={() => onDeleteConfirm(cardToDelete)}
            >
              Confirm
            </button>
            <button
              type="button"
              className="text-red-500 background-transparent font-bold uppercase px-6 py-2 text-sm outline-none focus:outline-none mr-1 mb-1"
              onClick={onClose}
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

interface EditModalProps {
  cardToEdit: ContentInEdit | null;
  onTitleChange: (content_title: string) => void;
  onContentChange: (content_text: string) => void;
  onLanguageChange: (content_language: Language) => void;
  onSubmit: () => void;
  onClose: () => void;
}
export const EditModal: React.FC<EditModalProps> = ({
  cardToEdit,
  onTitleChange,
  onContentChange,
  onLanguageChange,
  onSubmit,
  onClose,
}) => {
  return (
    <div
      className="flex backdrop-blur justify-center items-center overflow-x-hidden overflow-y-auto fixed inset-0 z-50 outline-none focus:outline-none"
      onClick={() => onClose()}
    >
      <div
        className="relative w-auto my-6 mx-auto max-w-3xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-0 rounded-lg shadow-lg relative flex flex-col w-full dark:bg-gray-700 bg-gray-200 dark:outline-none focus:outline-none">
          <div className="flex items-start justify-between p-5 rounded-t ">
            <h3 className="text-xl">
              {cardToEdit ? (
                <>
                  Edit Content
                  <div className="text-xs dark:text-gray-400 text-gray-800">
                    id: {cardToEdit.content_id}
                  </div>
                </>
              ) : (
                "New Content"
              )}
            </h3>
            <XMarkIcon className="w-4 h-4 float-right" onClick={onClose} />
          </div>
          <div className="relative px-5 py-1 flex flex-auto mb-2">
            <input
              id="content_title"
              type="text"
              className="shadow appearance-none border active:outline-none border-neutral-400 text-sm rounded w-full dark:bg-gray-800 py-3 px-3 text-gray-800 dark:text-gray-400 overflow-auto required"
              defaultValue={cardToEdit?.content_title || ""}
              placeholder="Enter content title"
              maxLength={150}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                onTitleChange(e.target.value);
              }}
            />
          </div>
          <div className="relative px-5 py-1 flex flex-auto mb-2">
            <TextareaAutosize
              id="content_text"
              cols={75}
              maxRows={6}
              maxLength={1446} // Ensure len("*{title}*\n\n{text}") <= 1600
              className="shadow appearance-none border active:outline-none border-neutral-400 text-sm rounded w-full dark:bg-gray-800 py-3 px-3 text-gray-800 dark:text-gray-400 overflow-auto required min-h-[10rem]"
              defaultValue={cardToEdit?.content_text || ""}
              placeholder="Enter content text"
              onChange={(e: React.FormEvent<HTMLTextAreaElement>) => {
                const target = e.target as HTMLTextAreaElement;
                onContentChange(target.value);
              }}
            />
          </div>
          <div className="relative px-5 py-1 flex flex-auto items-center">
            <label
              htmlFor="content_language"
              className="block text-gray-700 text-sm font-bold mr-2"
            >
              Language
            </label>
            <div className="relative inline-block">
              <select
                id="content_language"
                className="shadow appearance-none border active:outline-none border-neutral-400 text-sm rounded w-32 dark:bg-gray-800 py-2 px-3 text-gray-800 dark:text-gray-400 overflow-auto required mt-2"
                defaultValue={cardToEdit?.content_language || "ENGLISH"}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
                  onLanguageChange(e.target.value as Language);
                }}
              >
                {Object.values(Language).map((language) => (
                  <option key={language} value={language}>
                    {language}
                  </option>
                ))}
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-gray-700">
                <svg
                  className="fill-current h-4 w-4"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                >
                  <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
                </svg>
              </div>
            </div>
          </div>
          <div className="flex items-center justify-end pb-4 px-4 rounded-b">
            <button
              id="closeButton"
              className="text-red-500 background-transparent font-bold uppercase px-6 py-2 text-sm outline-none focus:outline-none mr-1 mb-1"
              type="button"
              onClick={onClose}
            >
              Close
            </button>
            <button
              id="submitButton"
              className="text-white bg-blue-500 active:bg-blue-700 font-bold uppercase text-sm px-6 py-3 rounded shadow hover:shadow-lg outline-none focus:outline-none mr-1 mb-1"
              type="button"
              onClick={() => onSubmit()}
            >
              Submit
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
