"use client";
import React, { useState } from "react";
import { format } from "date-fns";
import { IconArrowRight, IconClock, IconKey, IconRefresh } from "@tabler/icons-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { toast } from "@/components/ui/toast";
import { useAuth } from "@/utils/auth";
import { CustomError } from "@/utils/api";
import { createNewApiKey } from "./api";
import { KeyRenewConfirmationModal, NewKeyModal } from "./components/APIKeyModals";
import ConnectionsGrid from "./components/ConnectionsGrid";
import { getCurrentWorkspace } from "../workspace-management/api";

const CONTACT_URL = "https://docs.ask-a-question.com/latest/contact_us/";

/** Error toast; rendered by the Toaster in integrations/layout.tsx. */
const showError = (message: string) => toast.add({ title: message, type: "error" });

const IntegrationsPage = () => {
  const { token, userRole } = useAuth();
  const editAccess = userRole == "admin";

  // Workspace details shared by the key and limit cards. `undefined` = still loading.
  const [workspace, setWorkspace] = useState<
    | {
        keyStart: string;
        keyUpdated: string;
        /** null means the workspace has no daily limit. */
        dailyQuota: number | null;
      }
    | undefined
  >(undefined);
  const [refreshKey, setRefreshKey] = useState(0);

  React.useEffect(() => {
    if (!token) return;
    getCurrentWorkspace(token)
      .then((data) =>
        setWorkspace({
          keyStart: data.api_key_first_characters ?? "",
          keyUpdated: data.api_key_updated_datetime_utc
            ? format(data.api_key_updated_datetime_utc, "MMM d, yyyy 'at' HH:mm")
            : "",
          dailyQuota: data.api_daily_quota ?? null,
        }),
      )
      .catch((error: CustomError) => {
        console.error(error);
        showError(error.message || "Error fetching API key");
        setWorkspace({ keyStart: "", keyUpdated: "", dailyQuota: null });
      });
  }, [token, refreshKey]);

  return (
    <div className="px-4 pt-8 pb-16 sm:px-8 md:pt-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <header className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight">Integrations</h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Use your workspace API key to connect Ask a Question to your chat manager.
          </p>
        </header>

        <div className="grid gap-4 md:grid-cols-2">
          {/* Only admins can see or rotate the key */}
          {editAccess && (
            <KeyManagement
              token={token}
              workspace={workspace}
              onKeyRotated={() => setRefreshKey((k) => k + 1)}
            />
          )}
          <DailyLimit
            quota={workspace === undefined ? undefined : workspace.dailyQuota}
          />
        </div>

        <section aria-labelledby="connect" className="flex flex-col gap-3.5">
          <div>
            <h2 id="connect" className="text-base font-semibold tracking-tight">
              Connect a chat manager
            </h2>
            <p className="mt-1 text-[13px] text-muted-foreground">
              Choose a connection to see step-by-step instructions for using it with Ask
              a Question.
            </p>
          </div>
          <ConnectionsGrid />
        </section>
      </div>
    </div>
  );
};

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

const KeyManagement = ({
  token,
  workspace,
  onKeyRotated,
}: {
  token: string | null;
  workspace: { keyStart: string; keyUpdated: string } | undefined;
  onKeyRotated: () => void;
}) => {
  const [confirmationModalOpen, setConfirmationModalOpen] = useState(false);
  const [newKeyModalOpen, setNewKeyModalOpen] = useState(false);
  const [newKey, setNewKey] = useState("");
  const [keyGenerationIsLoading, setKeyGenerationIsLoading] = useState(false);

  const currentKey = workspace?.keyStart ?? "";

  const handleRenew = async () => {
    setKeyGenerationIsLoading(true);
    try {
      const data = await createNewApiKey(token!);
      setNewKey(data.new_api_key);
      setConfirmationModalOpen(false);
      setNewKeyModalOpen(true);
      onKeyRotated(); // refetch the key preview and timestamp
    } catch (error) {
      const customError = error as CustomError;
      showError(customError.message || "Error rotating API key");
      console.error(error);
    } finally {
      setKeyGenerationIsLoading(false);
    }
  };

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
          This workspace doesn’t have an API key yet. Generate one to connect your chat
          manager.
        </p>
      )}

      <hr className="border-border" />
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
            onClick={() => setConfirmationModalOpen(true)}
            disabled={keyGenerationIsLoading}
          >
            <IconRefresh data-icon="inline-start" />
            Regenerate key
          </Button>
        ) : (
          <Button
            key="generate"
            size="lg"
            onClick={handleRenew}
            disabled={keyGenerationIsLoading}
          >
            {keyGenerationIsLoading ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <IconKey data-icon="inline-start" />
            )}
            Generate key
          </Button>
        )}
      </div>

      <KeyRenewConfirmationModal
        open={confirmationModalOpen}
        currentKey={currentKey}
        onClose={() => setConfirmationModalOpen(false)}
        onRenew={handleRenew}
        isLoading={keyGenerationIsLoading}
      />
      <NewKeyModal
        newKey={newKey}
        open={newKeyModalOpen}
        onClose={() => setNewKeyModalOpen(false)}
        onCopy={() => navigator.clipboard.writeText(newKey)}
      />
    </section>
  );
};

/**
 * The workspace's daily request limit. The app has no per-day usage count,
 * so this shows the limit itself rather than a usage meter.
 */
const DailyLimit = ({ quota }: { quota: number | null | undefined }) => (
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
        {quota === null ? "No daily limit" : `${quota.toLocaleString()} requests`}
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

export default IntegrationsPage;
