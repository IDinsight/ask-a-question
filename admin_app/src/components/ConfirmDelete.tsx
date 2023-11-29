// ConfirmDelete.jsx
"use client";

import React, { useState, useEffect } from "react";

const ConfirmDelete = ({
  itemToDelete,
  onDeleteConfirm,
  onClose,
  title,
  message,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    setIsOpen(true);
  }, []);

  const handleCancel = () => {
    setIsOpen(false);
    onClose?.();
  };

  const handleConfirm = () => {
    onDeleteConfirm?.(itemToDelete);
    setIsOpen(false);
  };

  if (!isOpen) return null;

  return (
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
          <p className="text-sm dark:text-gray-400">{message}</p>
        </div>
        <div className="dark:bg-gray-700 px-4 py-3 sm:flex sm:flex-row-reverse mt-4 rounded-b-lg">
          <button
            type="button"
            className="w-auto inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-red-600 text-base font-medium text-white hover:bg-red-700 focus:outline-none sm:ml-3"
            onClick={handleConfirm}
          >
            Confirm
          </button>
          <button
            type="button"
            className="text-red-500 background-transparent font-bold uppercase px-6 py-2 text-sm outline-none focus:outline-none mr-1 mb-1"
            onClick={handleCancel}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDelete;
