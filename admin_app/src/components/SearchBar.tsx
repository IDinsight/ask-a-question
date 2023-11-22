import React from "react";

interface SearchBarProps {
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({ onChange }) => {
  return (
    <div className="w-full max-w-xs px-3 py-3">
      <input
        type="text"
        className="w-full rounded p-2 placeholder-gray-500 border border-gray-600 dark:bg-gray-800 focus:border-blue-500 focus:outline-none"
        placeholder="Filter cards"
        onChange={onChange}
      />
    </div>
  );
};
