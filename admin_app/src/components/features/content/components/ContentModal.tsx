import ReactMarkdown from "react-markdown";
import Link from "next/link";
import {
  IconCheck,
  IconEdit,
  IconThumbDown,
  IconThumbUp,
  IconTrash,
  IconX,
} from "@tabler/icons-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { CustomError } from "@/utils/api";
import { Content, Tag } from "../types";

/**
 * Tailwind classes for markdown rendered without a typography plugin:
 * restores paragraph spacing, list bullets and link underlines.
 */
export const MARKDOWN_CLASSES =
  "wrap-break-word hyphens-auto [&_a]:underline [&_a]:underline-offset-2 [&_li]:my-0.5 [&_ol]:list-decimal [&_ol]:pl-5 [&_p:not(:last-child)]:mb-2 [&_ul]:list-disc [&_ul]:pl-5";

/**
 * "Edit" button that links to the content editor.
 * A disabled link is not a thing, so without edit access we render a plain
 * disabled button instead.
 */
export const EditContentButton = ({
  content_id,
  editAccess,
  variant = "default",
  size = "default",
  className,
  onClick,
}: {
  content_id: number;
  editAccess: boolean;
  variant?: "default" | "ghost" | "outline";
  size?: "default" | "sm" | "lg";
  className?: string;
  onClick?: (event: React.MouseEvent) => void;
}) => {
  const children = (
    <>
      <IconEdit data-icon="inline-start" />
      Edit
    </>
  );
  if (!editAccess) {
    return (
      <Button variant={variant} size={size} className={className} disabled>
        {children}
      </Button>
    );
  }
  return (
    <Button
      variant={variant}
      size={size}
      className={className}
      nativeButton={false}
      render={
        <Link
          href={`/content/edit?content_id=${content_id}`}
          onClick={onClick}
        />
      }
    >
      {children}
    </Button>
  );
};

const ContentViewModal = ({
  title,
  text,
  content_id,
  display_number,
  positive_votes,
  negative_votes,
  last_modified,
  tags,
  related_contents,
  open,
  onClose,
  onApprove,
  onReject,
  onRelatedContentClick,
  editAccess,

  validation_mode = false,
}: {
  title: string;
  text: string;
  content_id: number;
  display_number: number;
  last_modified: string;
  tags?: Tag[];
  related_contents: Content[];
  positive_votes: number;
  negative_votes: number;
  open: boolean;
  onClose: () => void;
  /** Validation mode only: approve / reject (archive) this card. */
  onApprove?: (content_id: number) => void;
  onReject?: (content_id: number) => void;
  editAccess: boolean;
  onRelatedContentClick: (content: Content) => void;
  validation_mode?: boolean;
}) => {
  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent className="gap-5 p-6 text-sm sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">
            Content #{display_number}
          </DialogTitle>
        </DialogHeader>

        {tags && tags.length > 0 && (
          <section className="flex flex-col gap-2">
            <h3 className="text-xs font-medium text-muted-foreground">Tags</h3>
            <div className="flex flex-wrap gap-1.5">
              {tags.map((tag) => (
                <Badge key={tag.tag_id} variant="secondary">
                  {tag.tag_name}
                </Badge>
              ))}
            </div>
          </section>
        )}

        <article className="flex max-h-[60vh] flex-col gap-3 overflow-y-auto border bg-card p-4">
          <h2 className="text-base font-semibold">{title}</h2>
          <div className={MARKDOWN_CLASSES}>
            <ReactMarkdown>{text}</ReactMarkdown>
          </div>
        </article>

        {related_contents && related_contents.length > 0 && (
          <section className="flex flex-col gap-2">
            <h3 className="text-xs font-medium text-muted-foreground">
              Related contents
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {related_contents.map((content) => (
                <Badge
                  key={content.content_id}
                  variant="outline"
                  className="h-6 max-w-64 cursor-pointer hover:bg-muted"
                  render={
                    <button
                      type="button"
                      onClick={() => onRelatedContentClick(content)}
                    />
                  }
                >
                  <span className="truncate">{content.content_title}</span>
                </Badge>
              ))}
            </div>
          </section>
        )}

        <DialogFooter className="flex-col-reverse items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
          {validation_mode ? (
            <div className="flex gap-2">
              <Button
                disabled={!editAccess}
                onClick={() => onApprove?.(content_id)}
              >
                <IconCheck data-icon="inline-start" />
                Approve
              </Button>
              <Button
                variant="destructive"
                disabled={!editAccess}
                onClick={() => onReject?.(content_id)}
              >
                <IconX data-icon="inline-start" />
                Reject
              </Button>
            </div>
          ) : (
            <EditContentButton
              content_id={content_id}
              editAccess={editAccess}
            />
          )}
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span>
              Last modified{" "}
              {new Date(last_modified).toLocaleString(undefined, {
                day: "numeric",
                month: "short",
                year: "numeric",
                hour: "numeric",
                minute: "numeric",
                hour12: true,
              })}
            </span>
            <span className="flex items-center gap-1" title="Upvotes">
              <IconThumbUp className="size-4" aria-label="Upvotes" />
              {positive_votes}
            </span>
            <span className="flex items-center gap-1" title="Downvotes">
              <IconThumbDown className="size-4" aria-label="Downvotes" />
              {negative_votes}
            </span>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

interface ArchiveContentModalProps {
  content_id: number;
  open: boolean;
  onClose: () => void;
  onSuccessfulArchive: (content_id: number) => void;
  onFailedArchive: (content_id: number, error_message: string) => void;
  archiveContent: (content_id: number) => Promise<unknown>;
}

const ArchiveContentModal: React.FC<ArchiveContentModalProps> = ({
  content_id,
  open,
  onClose,
  onSuccessfulArchive,
  onFailedArchive,
  archiveContent,
}) => {
  const handleRemove = () => {
    // Fire and forget: close immediately, report the result via callbacks.
    archiveContent(Number(content_id))
      .then(() => onSuccessfulArchive(content_id))
      .catch((err) => {
        const customError = err as CustomError;
        onFailedArchive(content_id, customError.message);
      });
    onClose();
  };

  return (
    <AlertDialog
      open={open}
      onOpenChange={(nextOpen) => !nextOpen && onClose()}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogMedia className="bg-destructive/10 text-destructive">
            <IconTrash />
          </AlertDialogMedia>
          <AlertDialogTitle>Remove this content?</AlertDialogTitle>
          <AlertDialogDescription>
            Removing this content will mean that it can no longer be accessed.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            onClick={handleRemove}
            autoFocus
          >
            Remove
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};

export { ContentViewModal, ArchiveContentModal };
