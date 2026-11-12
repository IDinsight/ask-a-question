import React, { useState } from "react";
import { IconPencil, IconUserMinus } from "@tabler/icons-react";

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
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import type { UserRole } from "@/components/features/workspace-management/types";

interface UserCardProps {
  adminUsername: string;
  userId: number;
  username: string;
  userRole: UserRole;
  onRemoveUser: (userId: number) => void;
  onEditUser: () => void;
}

const getUserInitials = (name: string) =>
  name
    .split(" ")
    .map((word) => word[0])
    .join("")
    .toUpperCase();

/**
 * One row in the workspace user list. Edit and remove appear on hover or
 * keyboard focus; removing asks for confirmation first.
 */
const UserCard: React.FC<UserCardProps> = ({
  username,
  adminUsername,
  userId,
  userRole,
  onRemoveUser,
  onEditUser,
}) => {
  const [open, setOpen] = useState(false);
  const isYou = username == adminUsername;

  return (
    <li className="group flex items-center gap-3 border-b px-4 py-3 last:border-b-0">
      <Avatar className="size-9">
        <AvatarFallback className="bg-primary text-xs font-semibold text-primary-foreground">
          {getUserInitials(username)}
        </AvatarFallback>
      </Avatar>
      <div className="flex min-w-0 flex-1 flex-col">
        <span className="flex items-center gap-2 text-sm font-medium wrap-break-word">
          {username}
          {isYou && (
            <span className="text-xs font-normal text-muted-foreground">
              (You)
            </span>
          )}
        </span>
        <span className="text-xs text-muted-foreground">
          {userRole == "admin" ? "Admin" : "Read only"}
        </span>
      </div>
      <div className="flex shrink-0 gap-1 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={`Edit ${username}`}
          onClick={onEditUser}
        >
          <IconPencil />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          className="text-destructive hover:text-destructive"
          aria-label={`Remove ${username} from workspace`}
          onClick={() => setOpen(true)}
        >
          <IconUserMinus />
        </Button>
      </div>

      <AlertDialog open={open} onOpenChange={setOpen}>
        <AlertDialogContent className="p-6">
          <AlertDialogHeader>
            <AlertDialogMedia className="text-destructive">
              <IconUserMinus />
            </AlertDialogMedia>
            <AlertDialogTitle className="text-base">
              Remove {username} from this workspace?
            </AlertDialogTitle>
            <AlertDialogDescription className="text-sm">
              If this is the user’s only workspace, they will be{" "}
              <b className="font-semibold text-foreground">
                deleted from the system
              </b>
              .
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel size="lg">Cancel</AlertDialogCancel>
            <AlertDialogAction
              size="lg"
              variant="destructive"
              autoFocus
              onClick={() => {
                onRemoveUser(userId);
                setOpen(false);
              }}
            >
              <IconUserMinus data-icon="inline-start" />
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </li>
  );
};

export { UserCard };
