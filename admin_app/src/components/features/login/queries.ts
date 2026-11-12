/**
 * TanStack Query hooks for the login page's first-user setup. LoginWrapper is
 * the only caller.
 *
 * Both endpoints are public (nobody is signed in yet), so unlike the other
 * features these hooks don't read or wait for an auth token. Signing in
 * itself goes through useAuth().login / loginGoogle, not through here.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createFirstUser } from "@/client";
import {
  isRegisterRequiredOptions,
  isRegisterRequiredQueryKey,
} from "@/client/@tanstack/react-query.gen";
import type { RequireRegisterResponse } from "@/client";

/* ------------------------------------------------------------------ */
/* Does the deployment still need its first (admin) user?              */
/* ------------------------------------------------------------------ */

const selectRequireRegister = (data: RequireRegisterResponse | undefined) =>
  !!data?.require_register;

/**
 * Resolves to true when no user exists yet. If the check fails we log it and
 * the sign-in page stays usable (the setup dialogs just don't appear).
 */
export const useRegisterOptionQuery = () => {
  const { queryFn, queryKey } = isRegisterRequiredOptions();
  return useQuery({
    queryKey,
    queryFn: async (context) => {
      try {
        return await queryFn!(context);
      } catch (error) {
        console.error("Could not check whether first-user setup is needed:", error);
        throw error;
      }
    },
    select: selectRequireRegister,
    // One attempt, as before: a failure just skips the setup dialogs.
    retry: false,
  });
};

/* ------------------------------------------------------------------ */
/* Register the first user                                             */
/* ------------------------------------------------------------------ */

/**
 * Creates the first (admin) user. Resolves with `{ recovery_codes }`.
 * Throws { status, message } for 4xx and a plain Error otherwise (see utils/api.ts);
 * the RegisterModal shows the message.
 */
export const useRegisterUserMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      username,
      password,
    }: {
      username: string;
      password: string;
    }) => {
      const { data } = await createFirstUser({
        // The backend always makes the first user an admin of a new workspace.
        body: { username, password },
      });
      return data;
    },
    // A user exists now, so the check's cached answer is out of date. Not
    // awaited: the recovery codes should show without waiting for a refetch.
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: isRegisterRequiredQueryKey() });
    },
  });
};
