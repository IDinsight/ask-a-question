/**
 * TanStack Query hooks for the urgency rules page. UrgencyRulesWrapper is the
 * only caller.
 *
 * Conventions (same as dashboard/queries.ts):
 * - Hooks read the auth token themselves and stay disabled until it exists.
 * - The token is NOT part of the query key; AuthProvider clears the whole cache
 *   when the user or workspace changes.
 * - Rule mutations write their result into the cached list straight away (so
 *   the row updates without waiting for a refetch, as the page did before),
 *   then invalidate the list so it re-syncs with the backend.
 * - Error toasts are left to the caller, which knows the message to show.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/utils/auth";
import {
  addUrgencyRule,
  deleteUrgencyRule,
  getUrgencyDetection,
  getUrgencyRuleList,
  updateUrgencyRule,
} from "./api";
import type { UrgencyDetectionResponse, UrgencyRule } from "./types";

/* ------------------------------------------------------------------ */
/* Query keys                                                          */
/* ------------------------------------------------------------------ */

export const urgencyRuleKeys = {
  all: ["urgency-rules"] as const,
  list: () => [...urgencyRuleKeys.all, "list"] as const,
};

/* ------------------------------------------------------------------ */
/* Rule list + CRUD                                                    */
/* ------------------------------------------------------------------ */

export const useUrgencyRulesQuery = () => {
  const { token } = useAuth();
  return useQuery({
    queryKey: urgencyRuleKeys.list(),
    queryFn: (): Promise<UrgencyRule[]> => getUrgencyRuleList(token!),
    enabled: !!token,
  });
};

/** Shared by the three rule mutations: patch the cached list, then re-sync. */
const useRuleListCache = () => {
  const queryClient = useQueryClient();
  return {
    /** Stop an in-flight refetch from overwriting an optimistic patch. */
    cancel: () => queryClient.cancelQueries({ queryKey: urgencyRuleKeys.list() }),
    patch: (fn: (rules: UrgencyRule[]) => UrgencyRule[]) =>
      queryClient.setQueryData<UrgencyRule[]>(urgencyRuleKeys.list(), (old) =>
        fn(old ?? []),
      ),
    // Not awaited, so the mutation settles as soon as the request does.
    invalidate: () => {
      void queryClient.invalidateQueries({ queryKey: urgencyRuleKeys.list() });
    },
  };
};

/** Create a rule; the saved rule is appended to the list. */
export const useAddUrgencyRuleMutation = () => {
  const { token } = useAuth();
  const cache = useRuleListCache();
  return useMutation({
    mutationFn: (ruleText: string): Promise<UrgencyRule> =>
      addUrgencyRule(ruleText, token!),
    onSuccess: (saved) => {
      cache.patch((rules) => [...rules, saved]);
      cache.invalidate();
    },
  });
};

/**
 * Update a rule's text. The new text shows at once (the old timestamp stays
 * until the backend answers), like the page did before. On failure the
 * invalidation brings back the saved text.
 */
export const useUpdateUrgencyRuleMutation = () => {
  const { token } = useAuth();
  const cache = useRuleListCache();
  return useMutation({
    mutationFn: ({ id, text }: { id: number; text: string }): Promise<UrgencyRule> =>
      updateUrgencyRule(id, text, token!),
    onMutate: async ({ id, text }) => {
      await cache.cancel();
      cache.patch((rules) =>
        rules.map((r) =>
          r.urgency_rule_id === id ? { ...r, urgency_rule_text: text } : r,
        ),
      );
    },
    onSuccess: (saved) => {
      cache.patch((rules) =>
        rules.map((r) => (r.urgency_rule_id === saved.urgency_rule_id ? saved : r)),
      );
    },
    onSettled: cache.invalidate,
  });
};

/** Delete a rule; it leaves the list once the backend confirms. */
export const useDeleteUrgencyRuleMutation = () => {
  const { token } = useAuth();
  const cache = useRuleListCache();
  return useMutation({
    mutationFn: (id: number) => deleteUrgencyRule(id, token!),
    onSuccess: (_data, id) => {
      cache.patch((rules) => rules.filter((r) => r.urgency_rule_id !== id));
      cache.invalidate();
    },
  });
};

/* ------------------------------------------------------------------ */
/* Test panel                                                          */
/* ------------------------------------------------------------------ */

/**
 * Classify a sample message against the workspace's rules. A mutation, not a
 * query: each "send" is a one-off request whose result the test panel keeps.
 */
export const useUrgencyDetectionMutation = () => {
  const { token } = useAuth();
  return useMutation({
    mutationFn: (message: string): Promise<UrgencyDetectionResponse> =>
      getUrgencyDetection(message, token!),
  });
};
