import Link from "next/link";
import React from "react";
import {
  IconChevronDown,
  IconDownload,
  IconFileTypeCsv,
  IconFileTypePdf,
  IconPlayerPlay,
  IconPlus,
  IconTrash,
} from "@tabler/icons-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ButtonGroup,
  ButtonGroupSeparator,
} from "@/components/ui/button-group";
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Spinner } from "@/components/ui/spinner";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { IndexingStatusResponse } from "../types";
import type { Content, Tag } from "../types";
import { SearchBar, SearchBarProps } from "./SearchBar";

interface TagsFilterProps {
  tags: Tag[];
  filterTags: Tag[];
  setFilterTags: React.Dispatch<React.SetStateAction<Tag[]>>;
}

interface CardsUtilityStripProps extends TagsFilterProps, SearchBarProps {
  editAccess: boolean;
  /** The cards currently shown (after search/tag filtering), for "Select all". */
  cards: Content[];
  selectedContents: number[];
  setSelectedContents: React.Dispatch<React.SetStateAction<number[]>>;
  handleDelete: () => void;
  openSearchSidebar: boolean;
  handleSidebarToggle: () => void;
  openChatSidebar: boolean;
  handleChatSidebarToggle: () => void;
  /** Cards waiting for validation; the "Validate cards" button shows when > 0. */
  unvalidatedCardsCount: number | undefined;
  onValidateClick: () => void;
  /** `true` while a PDF is processing; not a boolean when the feature is off. */
  indexingStatus: IndexingStatusResponse | undefined;
  onIndexingStatusClick: () => void;
  onDownloadClick: () => void;
  onImportCSVClick: () => void;
  onImportPDFClick: () => void;
}

/**
 * Toolbar above the cards grid: search and tag filter on the left; bulk
 * actions while cards are selected, otherwise the page actions, on the right.
 * The dialogs these buttons open are rendered by ContentWrapper.
 */
export const CardsUtilityStrip: React.FC<CardsUtilityStripProps> = ({
  editAccess,
  searchTerm,
  setSearchTerm,
  cards,
  tags,
  selectedContents,
  setSelectedContents,
  filterTags,
  setFilterTags,
  handleDelete,
  openSearchSidebar,
  handleSidebarToggle,
  openChatSidebar,
  handleChatSidebarToggle,
  unvalidatedCardsCount,
  onValidateClick,
  indexingStatus,
  onIndexingStatusClick,
  onDownloadClick,
  onImportCSVClick,
  onImportPDFClick,
}) => {
  const handleSelectAll = () => {
    const allContentIds = cards.map((card) => card.content_id!);
    setSelectedContents(allContentIds);
  };

  const handleDeSelectAll = () => {
    setSelectedContents([]);
  };

  return (
    <div className="flex w-full flex-wrap items-end justify-between gap-4 pb-4">
      {/* Left: search and tag filter */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="w-55">
          <SearchBar searchTerm={searchTerm} setSearchTerm={setSearchTerm} />
        </div>
        <TagsFilter
          tags={tags}
          filterTags={filterTags}
          setFilterTags={setFilterTags}
        />
      </div>

      {/* Right: bulk actions while cards are selected, otherwise page actions */}
      {selectedContents.length > 0 ? (
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            {selectedContents.length} selected
          </span>
          <Button
            variant="outline"
            size="lg"
            onClick={handleSelectAll}
            disabled={!editAccess}
          >
            Select all
          </Button>
          <Button
            variant="outline"
            size="lg"
            onClick={handleDeSelectAll}
            disabled={!editAccess}
          >
            Deselect all
          </Button>
          <Button
            variant="destructive"
            size="lg"
            onClick={handleDelete}
            disabled={!editAccess}
          >
            <IconTrash data-icon="inline-start" />
            Delete
          </Button>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          {(unvalidatedCardsCount ?? 0) > 0 && (
            <Button variant="outline" size="lg" onClick={onValidateClick}>
              Validate cards
              <Badge variant="destructive">{unvalidatedCardsCount}</Badge>
            </Button>
          )}
          {typeof indexingStatus === "boolean" && (
            <Button variant="outline" size="lg" onClick={onIndexingStatusClick}>
              {indexingStatus === true && <Spinner data-icon="inline-start" />}
              {indexingStatus === true ? "Processing PDF" : "PDF upload status"}
            </Button>
          )}
          {/* Test launchers live up here so they're visible without scrolling */}
          <Button
            variant="secondary"
            size="lg"
            disabled={openSearchSidebar}
            onClick={handleSidebarToggle}
          >
            <IconPlayerPlay data-icon="inline-start" />
            Test search
          </Button>
          <Button
            variant="secondary"
            size="lg"
            disabled={openChatSidebar}
            onClick={handleChatSidebarToggle}
          >
            <IconPlayerPlay data-icon="inline-start" />
            Test chat
          </Button>
          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  variant="outline"
                  size="icon-lg"
                  aria-label="Download all contents"
                  disabled={!editAccess}
                  onClick={onDownloadClick}
                />
              }
            >
              <IconDownload />
            </TooltipTrigger>
            <TooltipContent>Download all contents</TooltipContent>
          </Tooltip>
          <AddButtonWithDropdown
            editAccess={editAccess}
            onImportCSVClick={onImportCSVClick}
            onImportPDFClick={onImportPDFClick}
          />
        </div>
      )}
    </div>
  );
};

/**
 * Multi-select tag filter. Shows the first chosen tag as a chip and
 * "+N" for the rest, so the toolbar doesn't grow as tags are added.
 */
const TagsFilter: React.FC<TagsFilterProps> = ({
  tags,
  filterTags,
  setFilterTags,
}) => {
  const anchor = useComboboxAnchor();
  return (
    <Combobox
      multiple
      autoHighlight
      items={tags}
      value={filterTags}
      onValueChange={(updatedTags) => setFilterTags(updatedTags as Tag[])}
      itemToStringLabel={(tag: Tag) => tag.tag_name}
      isItemEqualToValue={(a: Tag, b: Tag) => a.tag_id === b.tag_id}
    >
      <ComboboxChips ref={anchor} className="min-h-9 w-60 flex-nowrap bg-card">
        <ComboboxValue>
          {(values: Tag[]) => (
            <>
              {values.slice(0, 1).map((tag) => (
                <ComboboxChip key={tag.tag_id}>
                  <span className="max-w-24 truncate">{tag.tag_name}</span>
                </ComboboxChip>
              ))}
              {values.length > 1 && (
                <span className="shrink-0 text-xs text-muted-foreground">
                  +{values.length - 1}
                </span>
              )}
              <ComboboxChipsInput
                aria-label="Filter by tag"
                placeholder={values.length ? "" : "Filter by tag"}
                className="min-w-10"
              />
            </>
          )}
        </ComboboxValue>
      </ComboboxChips>
      <ComboboxContent anchor={anchor}>
        <ComboboxEmpty>No tags found</ComboboxEmpty>
        <ComboboxList>
          {(tag: Tag) => (
            <ComboboxItem key={tag.tag_id} value={tag}>
              <span className="wrap-break-word">{tag.tag_name}</span>
            </ComboboxItem>
          )}
        </ComboboxList>
      </ComboboxContent>
    </Combobox>
  );
};

/** "New" button plus a dropdown for the bulk import options. */
const AddButtonWithDropdown: React.FC<{
  editAccess: boolean;
  onImportCSVClick: () => void;
  onImportPDFClick: () => void;
}> = ({ editAccess, onImportCSVClick, onImportPDFClick }) => {
  return (
    // Split button: "New" opens the editor, the arrow opens the import menu
    <ButtonGroup aria-label="Add content">
      {editAccess ? (
        <Button
          size="lg"
          nativeButton={false}
          render={<Link href="/content/edit" />}
        >
          <IconPlus data-icon="inline-start" />
          New
        </Button>
      ) : (
        <Button size="lg" disabled>
          <IconPlus data-icon="inline-start" />
          New
        </Button>
      )}
      {/* Visible divider between the two halves (both are filled navy) */}
      <ButtonGroupSeparator className="bg-primary-foreground/30" />
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <Button
              size="icon-lg"
              aria-label="Import or generate cards"
              disabled={!editAccess}
            />
          }
        >
          <IconChevronDown />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="min-w-52">
          <DropdownMenuItem onClick={onImportCSVClick}>
            <IconFileTypeCsv />
            Import cards from CSV
          </DropdownMenuItem>
          <DropdownMenuItem onClick={onImportPDFClick}>
            <IconFileTypePdf />
            Generate cards from PDF
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </ButtonGroup>
  );
};
