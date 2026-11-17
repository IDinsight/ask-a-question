/**
 * TanStack Query hooks for the reset-password page. ResetPasswordWrapper is
 * the only caller.
 *
 * The endpoint is public (the user can't sign in yet), so the hook doesn't
 * read or wait for an auth token.
 */
import { useMutation } from "@tanstack/react-query";

import { resetPassword } from "@/client";

/**
 * Reset a password with a recovery code. Resolves with the updated user
 * (`{ username, ... }`). Throws { status, message } for 4xx (e.g. a wrong
 * recovery code) and a plain Error otherwise (see utils/api.ts).
 */
export const useResetPasswordMutation = () =>
  useMutation({
    mutationFn: async ({
      username,
      recoveryCode,
      password,
    }: {
      username: string;
      recoveryCode: string;
      password: string;
    }) => {
      const { data } = await resetPassword({
        body: { username, recovery_code: recoveryCode, password },
      });
      return data;
    },
  });
