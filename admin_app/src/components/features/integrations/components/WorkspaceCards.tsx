import React from "react";
import {
  IconArrowRight,
  IconClock,
  IconKey,
  IconRefresh,
} from "@tabler/icons-react";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import type { WorkspaceKeyInfo } from "../queries";
import { KeyRenewConfirmationModal, NewKeyModal } from "./APIKeyModals";

const CONTACT_URL = "https://docs.ask-a-question.com/latest/contact_us/";

/** Card heading with a muted icon, as on the design board. */
const CardHeading = ({
  id,
  icon: Icon,
  children,
}: {
  id: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
}) => (
  <div className="flex items-center gap-2.5">
    <Icon className="size-4.5 text-muted-foreground" aria-hidden="true" />
    <h2 id={id} className="text-base font-semibold tracking-tight">
      {children}
    </h2>
  </div>
);

/**
 * Workspace API key card (admins only). Presentational: the Wrapper owns the
 * rotate-key mutation and which dialog is open.
 */
export const KeyManagement = ({
  workspace,
  isGenerating,
  confirmationOpen,
  onOpenConfirmation,
  onCloseConfirmation,
  onRenew,
  newKey,
  newKeyOpen,
  onCloseNewKey,
}: {
  /** `undefined` = still loading. */
  workspace: Pick<WorkspaceKeyInfo, "keyStart" | "keyUpdated"> | undefined;
  /** True while a new key is being generated. */
  isGenerating: boolean;
  confirmationOpen: boolean;
  onOpenConfirmation: () => void;
  onCloseConfirmation: () => void;
  /** Generate a new key (from the confirmation dialog or the first-key button). */
  onRenew: () => void;
  newKey: string;
  newKeyOpen: boolean;
  onCloseNewKey: () => void;
}) => {
  const currentKey = workspace?.keyStart ?? "";

  return (
    <section
      aria-labelledby="api-key"
      className="flex flex-col gap-4 border bg-card p-5 shadow-xs"
    >
      <CardHeading id="api-key" icon={IconKey}>
        Workspace API key
      </CardHeading>

      {workspace === undefined ? (
        <div
          className="flex flex-col gap-2"
          role="status"
          aria-label="Checking for current API key"
        >
          <Skeleton className="h-9" />
          <Skeleton className="h-4 w-48" />
        </div>
      ) : currentKey ? (
        <>
          {/* Only the first characters are known; the rest is masked */}
          <div className="flex h-9 items-center justify-between gap-3 border border-input px-3 shadow-xs">
            <span className="truncate font-mono text-sm">
              {currentKey}
              <span aria-hidden="true">••••••••••••••••••••</span>
              <span className="sr-only">(rest of key hidden)</span>
            </span>
            <span className="shrink-0 border border-input px-2.5 py-0.5 text-xs text-muted-foreground">
              Active
            </span>
          </div>
          {workspace.keyUpdated && (
            <span className="text-xs text-muted-foreground">
              Last updated {workspace.keyUpdated}
            </span>
          )}
        </>
      ) : (
        <p className="text-sm text-muted-foreground">
          This workspace doesn’t have an API key yet. Generate one to connect
          your chat manager.
        </p>
      )}

      <Separator />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="max-w-65 text-xs text-muted-foreground">
          {currentKey
            ? "Regenerating creates a new key and immediately invalidates the old one."
            : "You’ll see the full key once, so have somewhere safe to save it."}
        </span>
        {/* No button until we know whether a key exists; separate keys stop React
            reusing one element (and animating its colours) between the two states */}
        {workspace === undefined ? (
          <Skeleton className="h-9 w-36" />
        ) : currentKey ? (
          <Button
            key="regenerate"
            variant="outline"
            size="lg"
            className="text-destructive hover:text-destructive"
            onClick={onOpenConfirmation}
            disabled={isGenerating}
          >
            <IconRefresh data-icon="inline-start" />
            Regenerate key
          </Button>
        ) : (
          <Button
            key="generate"
            size="lg"
            onClick={onRenew}
            disabled={isGenerating}
          >
            {isGenerating ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <IconKey data-icon="inline-start" />
            )}
            Generate key
          </Button>
        )}
      </div>

      <KeyRenewConfirmationModal
        open={confirmationOpen}
        currentKey={currentKey}
        onClose={onCloseConfirmation}
        onRenew={onRenew}
        isLoading={isGenerating}
      />
      <NewKeyModal
        newKey={newKey}
        open={newKeyOpen}
        onClose={onCloseNewKey}
        onCopy={() => navigator.clipboard.writeText(newKey)}
      />
    </section>
  );
};

/**
 * The workspace's daily request limit. The app has no per-day usage count,
 * so this shows the limit itself rather than a usage meter.
 */
export const DailyLimit = ({ quota }: { quota: number | null | undefined }) => (
  <section
    aria-labelledby="daily-limit"
    className="flex flex-col gap-4 border bg-card p-5 shadow-xs"
  >
    <CardHeading id="daily-limit" icon={IconClock}>
      Daily API limit
    </CardHeading>
    {quota === undefined ? (
      <Skeleton className="h-8 w-40" />
    ) : (
      <p className="text-2xl font-semibold tracking-tight tabular-nums">
        {quota === null
          ? "No daily limit"
          : `${quota.toLocaleString()} requests`}
        {quota !== null && (
          <span className="ml-1.5 text-sm font-normal text-muted-foreground">
            per day
          </span>
        )}
      </p>
    )}
    <p className="text-[13px] text-muted-foreground">
      The limit resets daily. Need a higher limit for a launch or pilot?
    </p>
    <a
      href={CONTACT_URL}
      className="inline-flex w-fit items-center gap-1.5 text-[13px] font-medium text-primary underline-offset-4 hover:underline"
    >
      Contact us
      <IconArrowRight className="size-3.5" aria-hidden="true" />
    </a>
  </section>
);
