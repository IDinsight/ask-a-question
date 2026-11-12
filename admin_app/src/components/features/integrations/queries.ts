/**
 * TanStack Query hooks for the integrations page. IntegrationsWrapper is the
 * only caller.
 *
 * Conventions: see workspace-management/queries.ts (generated client via
 * /bff, hooks disabled until there is a token, generated query keys).
 */
import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";

import { getNewApiKey } from "@/client";
import { retrieveCurrentWorkspaceOptions } from "@/client/@tanstack/react-query.gen";
import { toast } from "@/components/ui/toast";
import { workspaceKeys } from "@/components/features/workspace-management/queries";
import type { CustomError } from "@/utils/api";
import { useAuth } from "@/utils/auth";

/* ------------------------------------------------------------------ */
/* Query keys                                                          */
/* ------------------------------------------------------------------ */

// The current workspace is shared with workspace management: both features
// read workspaceKeys.currentWorkspace(), so renaming the workspace or rotating
// the key there/here refreshes the other page too. Both use the same generated
// retrieveCurrentWorkspaceOptions(), so the cached shape is the same.

/* ------------------------------------------------------------------ */
/* Current workspace (API key preview + daily quota)                   */
/* ------------------------------------------------------------------ */

/** The fields of /workspace/current-workspace this page uses. */
interface CurrentWorkspaceResponse {
  api_key_first_characters?: string | null;
  api_key_updated_datetime_utc?: string | null;
  api_daily_quota?: number | null;
}

/** Workspace details shared by the key and limit cards. */
export interface WorkspaceKeyInfo {
  keyStart: string;
  keyUpdated: string;
  /** null means the workspace has no daily limit. */
  dailyQuota: number | null;
}

const parseWorkspace = (data: CurrentWorkspaceResponse): WorkspaceKeyInfo => ({
  keyStart: data.api_key_first_characters ?? "",
  keyUpdated: data.api_key_updated_datetime_utc
    ? format(data.api_key_updated_datetime_utc, "MMM d, yyyy 'at' HH:mm")
    : "",
  dailyQuota: data.api_daily_quota ?? null,
});

const NO_WORKSPACE: WorkspaceKeyInfo = {
  keyStart: "",
  keyUpdated: "",
  dailyQuota: null,
};

/**
 * The current workspace's key preview and daily quota.
 *
 * A failed fetch shows an error toast and falls back to an empty workspace
 * ("no key, no limit"), as the page did before the TanStack refactor.
 */
export const useCurrentWorkspaceQuery = () => {
  const { token } = useAuth();
  const query = useQuery({
    ...retrieveCurrentWorkspaceOptions(),
    select: parseWorkspace,
    enabled: !!token,
  });

  // Toast once per failure (the effect only re-runs when the error changes).
  useEffect(() => {
    if (!query.error) return;
    console.error(query.error);
    toast.add({
      title:
        (query.error as unknown as CustomError).message ||
        "Error fetching API key",
      type: "error",
    });
  }, [query.error]);

  return { ...query, data: query.isError ? NO_WORKSPACE : query.data };
};

/* ------------------------------------------------------------------ */
/* Rotate / generate the workspace API key                             */
/* ------------------------------------------------------------------ */

/**
 * Creates a new API key (the old one stops working at once). Resolves with
 * `{ new_api_key }`; on success the key preview and timestamp are refetched.
 * Callers handle showing the new key and any error toast.
 */
export const useRotateApiKeyMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => (await getNewApiKey()).data,
    // Not awaited: the new-key dialog should open straight away, as before,
    // while the preview refetches in the background.
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: workspaceKeys.currentWorkspace(),
      });
    },
  });
};
