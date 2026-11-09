import React from "react";
import { IconTrash } from "@tabler/icons-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "cn";
import {
  ArchiveContentModal,
  ContentViewModal,
  EditContentButton,
} from "./ContentModal";
import { Content, ContentDisplay, Tag } from "../types";

// Used by the cards grid on the content page to work out how many cards fit.
const CARD_HEIGHT = 210;
const CARD_MIN_WIDTH = 280;

interface ContentCardProps {
  title: string;
  text: string;
  content_id: number;
  display_number: number;
  last_modified: string;
  tags: Tag[];
  positive_votes: number;
  negative_votes: number;
  related_contents: Content[];
  onSuccessfulArchive: (content_id: number) => void;
  onFailedArchive: (content_id: number, error_message: string) => void;
  archiveContent: (content_id: number) => Promise<any>;
  editAccess: boolean;
  isSelectMode: boolean;
  selectedContents: number[];
  setSelectedContents: (selectedContents: number[]) => void;
  getRelatedContent: (content_id: number[]) => Content[];
}

const ContentCard: React.FC<ContentCardProps> = ({
  title,
  text,
  content_id,
  display_number,
  last_modified,
  tags,
  positive_votes,
  negative_votes,
  related_contents,
  onSuccessfulArchive,
  onFailedArchive,
  archiveContent,
  editAccess,
  isSelectMode,
  selectedContents,
  setSelectedContents,
  getRelatedContent,
}) => {
  const [openReadModal, setOpenReadModal] = React.useState<boolean>(false);
  const [openArchiveModal, setOpenArchiveModal] = React.useState<boolean>(false);
  const checked = selectedContents.includes(content_id);

  // The view modal can hop to related contents, so it shows whichever
  // content is "current" rather than always this card.
  const thisContent: ContentDisplay = {
    title,
    text,
    content_id,
    display_number,
    last_modified,
    tags,
    positive_votes,
    negative_votes,
    related_contents,
  };
  const [currentContent, setCurrentContent] =
    React.useState<ContentDisplay>(thisContent);

  const truncateTagName = (tagName: string): string => {
    return tagName.length > 15 ? `${tagName.slice(0, 15)}...` : tagName;
  };

  const handleRelatedContentClick = (content: Content) => {
    setCurrentContent({
      title: content.content_title,
      text: content.content_text,
      content_id: content.content_id!,
      display_number: content.display_number,
      last_modified: content.updated_datetime_utc,
      tags: tags.filter((tag) => content.content_tags.includes(tag.tag_id)),
      positive_votes: content.positive_votes,
      negative_votes: content.negative_votes,
      related_contents: getRelatedContent(content.related_contents_id),
    } as ContentDisplay);
  };

  const openCard = () => {
    setCurrentContent(thisContent);
    setOpenReadModal(true);
  };

  const handleCheckedChange = (newChecked: boolean) => {
    if (newChecked && !checked) {
      setSelectedContents([...selectedContents, content_id]);
    } else if (!newChecked && checked) {
      setSelectedContents(selectedContents.filter((id) => id !== content_id));
    }
  };

  // Hover-revealed controls also show on keyboard focus so they stay reachable.
  const revealOnHover =
    "opacity-0 transition-opacity group-hover/content-card:opacity-100 group-focus-within/content-card:opacity-100";

  return (
    <>
      <Card
        role="button"
        tabIndex={0}
        aria-label={`Open content #${display_number}: ${title}`}
        onClick={openCard}
        onKeyDown={(event) => {
          // Only react to keys pressed on the card itself, not its buttons.
          if (event.target !== event.currentTarget) return;
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openCard();
          }
        }}
        className={cn(
          "group/content-card relative cursor-pointer justify-between gap-2 p-4 text-sm shadow-sm transition-shadow hover:shadow-md focus-visible:ring-2 focus-visible:ring-ring",
          checked && "ring-2 ring-primary",
        )}
        style={{ height: CARD_HEIGHT, minWidth: CARD_MIN_WIDTH }}
      >
        <div className="flex h-5 items-center justify-between">
          {/* Selection checkbox: always visible in select mode, else on hover */}
          <div
            className={cn(!isSelectMode && !checked && revealOnHover)}
            onClick={(e) => e.stopPropagation()}
          >
            <Checkbox
              checked={checked}
              onCheckedChange={handleCheckedChange}
              aria-label={`Select content #${display_number}`}
            />
          </div>
          {tags && tags.length > 0 && (
            <div className="flex items-center gap-1">
              <Badge variant="outline" className="text-muted-foreground">
                {truncateTagName(tags[0].tag_name)}
              </Badge>
              {tags.length > 1 && (
                <span className="text-xs text-muted-foreground">
                  +{tags.length - 1}
                </span>
              )}
            </div>
          )}
        </div>

        <div className="flex min-w-0 flex-col gap-1">
          <h3 className="truncate text-base font-semibold">{title}</h3>
          <p className="line-clamp-2 text-muted-foreground">{text}</p>
        </div>

        <p className="text-xs text-muted-foreground">
          Last updated{" "}
          {new Date(last_modified).toLocaleString(undefined, {
            day: "numeric",
            month: "short",
            year: "numeric",
          })}
        </p>

        <div className={cn("flex items-center justify-between", revealOnHover)}>
          <EditContentButton
            content_id={content_id}
            editAccess={editAccess}
            variant="ghost"
            size="sm"
            className="-ml-2"
            onClick={(event) => event.stopPropagation()}
          />
          <Button
            variant="ghost"
            size="icon-sm"
            disabled={!editAccess}
            aria-label={`Delete content #${display_number}`}
            className="text-muted-foreground hover:text-destructive"
            onClick={(event) => {
              event.stopPropagation();
              setSelectedContents(selectedContents.filter((id) => id !== content_id));
              setOpenArchiveModal(true);
            }}
          >
            <IconTrash />
          </Button>
        </div>
      </Card>
      <ContentViewModal
        title={currentContent.title}
        text={currentContent.text}
        content_id={currentContent.content_id}
        display_number={currentContent.display_number}
        last_modified={currentContent.last_modified}
        related_contents={currentContent.related_contents}
        tags={currentContent.tags}
        open={openReadModal}
        positive_votes={currentContent.positive_votes}
        negative_votes={currentContent.negative_votes}
        onClose={() => setOpenReadModal(false)}
        editAccess={editAccess}
        onRelatedContentClick={handleRelatedContentClick}
      />
      <ArchiveContentModal
        content_id={content_id}
        open={openArchiveModal}
        onClose={() => setOpenArchiveModal(false)}
        onSuccessfulArchive={onSuccessfulArchive}
        onFailedArchive={onFailedArchive}
        archiveContent={archiveContent}
      />
    </>
  );
};

export { ContentCard, CARD_HEIGHT, CARD_MIN_WIDTH };
