/**
 * TanStack Query hooks for the urgency rules page. UrgencyRulesWrapper is the
 * only caller.
 *
 * Conventions: see workspace-management/queries.ts (generated client via
 * /bff, hooks disabled until there is a token, generated query keys).
 * - Rule mutations write their result into the cached list straight away (so
 *   the row updates without waiting for a refetch, as the page did before),
 *   then invalidate the list so it re-syncs with the backend.
 * - Error toasts are left to the caller, which knows the message to show.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  classifyText,
  createUrgencyRule,
  deleteUrgencyRule,
  updateUrgencyRule,
  type UrgencyRuleRetrieve,
} from "@/client";
import {
  getUrgencyRulesOptions,
  getUrgencyRulesQueryKey,
} from "@/client/@tanstack/react-query.gen";
import { useAuth } from "@/utils/auth";
import type { UrgencyDetectionResponse } from "./types";

/* ------------------------------------------------------------------ */
/* Query keys                                                          */
/* ------------------------------------------------------------------ */

export const urgencyRuleKeys = {
  list: () => getUrgencyRulesQueryKey(),
};

/* ------------------------------------------------------------------ */
/* Rule list + CRUD                                                    */
/* ------------------------------------------------------------------ */

export const useUrgencyRulesQuery = () => {
  const { token } = useAuth();
  return useQuery({ ...getUrgencyRulesOptions(), enabled: !!token });
};

/** Shared by the three rule mutations: patch the cached list, then re-sync. */
const useRuleListCache = () => {
  const queryClient = useQueryClient();
  return {
    /** Stop an in-flight refetch from overwriting an optimistic patch. */
    cancel: () =>
      queryClient.cancelQueries({ queryKey: urgencyRuleKeys.list() }),
    patch: (fn: (rules: UrgencyRuleRetrieve[]) => UrgencyRuleRetrieve[]) =>
      queryClient.setQueryData<UrgencyRuleRetrieve[]>(
        urgencyRuleKeys.list(),
        (old) => fn(old ?? []),
      ),
    // Not awaited, so the mutation settles as soon as the request does.
    invalidate: () => {
      void queryClient.invalidateQueries({ queryKey: urgencyRuleKeys.list() });
    },
  };
};

/** Create a rule; the saved rule is appended to the list. */
export const useAddUrgencyRuleMutation = () => {
  const cache = useRuleListCache();
  return useMutation({
    mutationFn: async (ruleText: string) =>
      (await createUrgencyRule({ body: { urgency_rule_text: ruleText } })).data,
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
  const cache = useRuleListCache();
  return useMutation({
    mutationFn: async ({ id, text }: { id: number; text: string }) =>
      (
        await updateUrgencyRule({
          path: { urgency_rule_id: id },
          body: { urgency_rule_text: text },
        })
      ).data,
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
        rules.map((r) =>
          r.urgency_rule_id === saved.urgency_rule_id ? saved : r,
        ),
      );
    },
    onSettled: cache.invalidate,
  });
};

/** Delete a rule; it leaves the list once the backend confirms. */
export const useDeleteUrgencyRuleMutation = () => {
  const cache = useRuleListCache();
  return useMutation({
    mutationFn: async (id: number) =>
      (await deleteUrgencyRule({ path: { urgency_rule_id: id } })).data,
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
export const useUrgencyDetectionMutation = () =>
  useMutation({
    mutationFn: async (message: string): Promise<UrgencyDetectionResponse> =>
      (await classifyText({ body: { message_text: message } })).data,
  });
