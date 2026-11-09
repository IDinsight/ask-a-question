"use client";

import React from "react";

import {
  Combobox,
  ComboboxChip,
  ComboboxChips,
  ComboboxChipsInput,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxItem,
  ComboboxList,
  ComboboxValue,
  useComboboxAnchor,
} from "@/components/ui/combobox";
import { Field, FieldLabel } from "@/components/ui/field";
import { Content } from "../types";

interface RelatedContentAutoCompleteProps {
  contents: Array<Content>;
  selectedContents: Array<Content>;
  handleContentChange: (contents: Content[]) => void;
}

/**
 * Multi-select for linking related contents to the card being edited.
 * Selected contents show as chips; the dropdown filters by title.
 */
export const RelatedContentsAutoComplete = ({
  contents,
  selectedContents,
  handleContentChange,
}: RelatedContentAutoCompleteProps) => {
  const anchor = useComboboxAnchor();

  return (
    <Field className="max-w-[500px]">
      <FieldLabel htmlFor="related-contents-input" className="text-sm">
        Related contents (optional)
      </FieldLabel>
      <Combobox
        multiple
        autoHighlight
        items={contents}
        value={selectedContents}
        onValueChange={(updated) => handleContentChange(updated as Content[])}
        itemToStringLabel={(content: Content) => content.content_title}
        // Match on ID when we have one; fall back to title for unsaved items.
        isItemEqualToValue={(a: Content, b: Content) =>
          a.content_id !== null && b.content_id !== null
            ? a.content_id === b.content_id
            : a.content_title === b.content_title
        }
      >
        <ComboboxChips ref={anchor} className="min-h-9 bg-card">
          <ComboboxValue>
            {(values: Content[]) => (
              <>
                {values.map((content) => (
                  <ComboboxChip key={content.content_id ?? content.content_title}>
                    <span className="max-w-48 truncate">{content.content_title}</span>
                  </ComboboxChip>
                ))}
                <ComboboxChipsInput
                  id="related-contents-input"
                  placeholder={values.length ? "" : "Find content"}
                />
              </>
            )}
          </ComboboxValue>
        </ComboboxChips>
        <ComboboxContent anchor={anchor}>
          <ComboboxEmpty>No contents found</ComboboxEmpty>
          <ComboboxList>
            {(content: Content) => (
              <ComboboxItem
                key={content.content_id ?? content.content_title}
                value={content}
              >
                <span className="truncate">{content.content_title}</span>
              </ComboboxItem>
            )}
          </ComboboxList>
        </ComboboxContent>
      </Combobox>
    </Field>
  );
};
