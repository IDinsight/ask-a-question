"use client";
import React, { useState } from "react";

import { toast } from "@/components/ui/toast";
import { useAuth } from "@/utils/auth";
import { CustomError } from "@/utils/api";
import ConnectionsGrid from "./components/ConnectionsGrid";
import { DailyLimit, KeyManagement } from "./components/WorkspaceCards";
import { useCurrentWorkspaceQuery, useRotateApiKeyMutation } from "./queries";

/** Error toast; rendered by the Toaster in integrations/layout.tsx. */
const showError = (message: string) =>
  toast.add({ title: message, type: "error" });

/**
 * The integrations feature. Owns:
 * - the current-workspace query (key preview, daily quota) and the
 *   rotate-key mutation (see ./queries.ts);
 * - which key dialog is open and the newly generated key.
 * Child components are presentational and get everything through props.
 */
const IntegrationsPage = () => {
  const { userRole } = useAuth();
  const editAccess = userRole == "admin";

  // `undefined` while loading; the cards show skeletons until then.
  const workspace = useCurrentWorkspaceQuery().data;
  const rotateKey = useRotateApiKeyMutation();

  const [confirmationModalOpen, setConfirmationModalOpen] = useState(false);
  const [newKeyModalOpen, setNewKeyModalOpen] = useState(false);
  const [newKey, setNewKey] = useState("");

  // Generate a key, then swap the confirmation dialog for the one showing it.
  // The mutation refetches the key preview and timestamp on success.
  const handleRenew = () =>
    rotateKey.mutate(undefined, {
      onSuccess: (data) => {
        setNewKey(data.new_api_key);
        setConfirmationModalOpen(false);
        setNewKeyModalOpen(true);
      },
      onError: (error) => {
        const customError = error as unknown as CustomError;
        showError(customError.message || "Error rotating API key");
        console.error(error);
      },
    });

  return (
    <div className="px-4 pt-8 pb-16 sm:px-8 md:pt-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <header className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight">
            Integrations
          </h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Use your workspace API key to connect Ask a Question to your chat
            manager.
          </p>
        </header>

        <div className="grid gap-4 md:grid-cols-2">
          {/* Only admins can see or rotate the key */}
          {editAccess && (
            <KeyManagement
              workspace={workspace}
              isGenerating={rotateKey.isPending}
              confirmationOpen={confirmationModalOpen}
              onOpenConfirmation={() => setConfirmationModalOpen(true)}
              onCloseConfirmation={() => setConfirmationModalOpen(false)}
              onRenew={handleRenew}
              newKey={newKey}
              newKeyOpen={newKeyModalOpen}
              onCloseNewKey={() => setNewKeyModalOpen(false)}
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
              Choose a connection to see step-by-step instructions for using it
              with Ask a Question.
            </p>
          </div>
          <ConnectionsGrid />
        </section>
      </div>
    </div>
  );
};

export default IntegrationsPage;
