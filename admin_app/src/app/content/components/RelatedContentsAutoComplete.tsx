"use client";

import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";

import React from "react";

import { Button, IconButton, TextField } from "@mui/material";
import { Content } from "../types";

interface RelatedContentAutoCompleteProps {
  contents: Array<Content>;
  selectedContents: Array<Content>;
  handleContentChange: (contents: Content[]) => void;
  onSelect: (contents: Content[]) => void;
}

export const RelatedContentsAutoComplete = ({
  contents,
  selectedContents,
  handleContentChange,
  onSelect,
}: RelatedContentAutoCompleteProps) => {
  const [inputVal, setInputVal] = React.useState<string>("");
  const filter = createFilterOptions<Content>();
  return (
    <>
      <Autocomplete
        autoSelect
        selectOnFocus
        clearOnBlur
        handleHomeEndKeys
        multiple
        limitTags={3}
        id="contents-autocomplete"
        options={contents}
        getOptionLabel={(option) => option!.content_title}
        noOptionsText="No contents found"
        value={selectedContents}
        onChange={(event: React.SyntheticEvent, updatedContents: Content[]) => {
          handleContentChange(updatedContents);
        }}
        renderInput={(params) => (
          <TextField
            {...params}
            variant="outlined"
            label="Related Contents (optional)"
            placeholder="Find content"
            onChange={(event) => setInputVal(event.target.value)}
            InputProps={{
              ...params.InputProps,
              style: { backgroundColor: "white" },
            }}
          />
        )}
        filterOptions={(options, params) => {
          const filtered = filter(options, params);
          const { inputValue } = params;
          const isExisting = options.some(
            (option) => inputValue.toUpperCase() === option.content_title,
          );
          return filtered.filter(
            (option) =>
              !selectedContents.some(
                (content) => content.content_title === option.content_title,
              ),
          );
        }}
        sx={{ maxWidth: "500px" }}
        isOptionEqualToValue={(option: Content, value: Content) =>
          value.content_title === option.content_title || value.content_title === ""
        }
      />
    </>
  );
};
