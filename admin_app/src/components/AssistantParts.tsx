import React from "react";
import { IconSparkles } from "@tabler/icons-react";

import { Button } from "@/components/ui/button";
import { MessageAvatar } from "@/components/ui/message";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

/**
 * Small pieces shared by the test chat and test search panels so both
 * render answers the same way.
 */

/** Ghost icon button with a tooltip, used for header and message actions. */
export const IconButtonWithTooltip = ({
  label,
  onClick,
  disabled,
  size = "icon",
  pressed,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  size?: "icon" | "icon-sm";
  // Set for toggle buttons (e.g. feedback thumbs) so screen readers hear the state
  pressed?: boolean;
  children: React.ReactNode;
}) => (
  <Tooltip>
    <TooltipTrigger
      render={
        <Button
          variant="ghost"
          size={size}
          aria-label={label}
          aria-pressed={pressed}
          onClick={onClick}
          disabled={disabled}
        />
      }
    >
      {children}
    </TooltipTrigger>
    <TooltipContent>{label}</TooltipContent>
  </Tooltip>
);

/**
 * Small round mark that identifies the assistant's turns.
 *
 * MessageAvatar defaults to the bottom of the turn and moves up when there is a
 * footer. That drifts once sources or actions sit under the bubble, so pin it
 * to the top instead. The 5px offset centres the 28px avatar on a one-line
 * bubble (1px border + 8px padding + 20px line + 8px padding + 1px = 38px).
 */
export const AssistantAvatar = () => (
  <MessageAvatar className="mt-[5px] size-7 min-w-7 self-start bg-primary text-primary-foreground group-has-data-[slot=message-footer]/message:translate-y-0">
    <IconSparkles className="size-3.5" />
  </MessageAvatar>
);
