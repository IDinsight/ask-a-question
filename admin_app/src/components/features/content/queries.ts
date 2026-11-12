/**
 * TanStack Query hooks for the content feature (/content and /content/edit).
 * Every API call those pages make goes through a hook here; ContentWrapper and
 * ContentEditWrapper are the only callers.
 *
 * Conventions (same as dashboard/queries.ts):
 * - Hooks read the auth token themselves and stay disabled until it exists.
 * - The token is NOT part of the query key; AuthProvider clears the whole cache
 *   when the user or workspace changes.
 * - Mutations invalidate the queries they affect instead of the old
 *   "bump a refreshKey and refetch everything" pattern.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/utils/auth";
import {
  archiveContent,
  bulkUploadContents,
  ContentBody,
  createContent,
  createTag,
  deleteTag,
  editContent,
  getChat,
  getContent,
  getContentList,
  getDocIndexingStatusData,
  getIndexingStatus,
  getNextUnvalidatedCard,
  getSearch,
  getTagList,
  getUnvalidatedCardsCount,
  postDocumentToIndex,
  postResponseFeedback,
  validateContent,
} from "./api";
import type { Content, Tag } from "./types";

/* ------------------------------------------------------------------ */
/* Query keys                                                          */
/* ------------------------------------------------------------------ */

export const contentKeys = {
  all: ["content"] as const,
  list: () => [...contentKeys.all, "list"] as const,
  detail: (contentId: number | null) =>
    [...contentKeys.all, "detail", contentId] as const,
  tags: () => [...contentKeys.all, "tags"] as const,
  unvalidatedCount: () => [...contentKeys.all, "unvalidated-count"] as const,
  nextUnvalidated: () => [...contentKeys.all, "next-unvalidated"] as const,
  indexingStatus: () => [...contentKeys.all, "indexing-status"] as const,
  indexingHistory: () => [...contentKeys.all, "indexing-history"] as const,
};

/* ------------------------------------------------------------------ */
/* Reads                                                               */
/* ------------------------------------------------------------------ */

/** Every (non-archived) content card in the workspace. */
export const useContentListQuery = () => {
  const { token } = useAuth();
  return useQuery({
    queryKey: contentKeys.list(),
    queryFn: (): Promise<Content[]> => getContentList({ token: token!, skip: 0 }),
    enabled: !!token,
  });
};

/**
 * One content card, for the editor. Idle when creating a new card.
 * Not cached across visits (gcTime 0): the editor copies the first result into
 * form state, so it must always start from fresh data, as the old fetch did.
 */
export const useContentQuery = (contentId: number | null) => {
  const { token } = useAuth();
  return useQuery({
    queryKey: contentKeys.detail(contentId),
    queryFn: (): Promise<Content> => getContent(contentId!, token!),
    enabled: !!token && contentId !== null,
    gcTime: 0,
  });
};

export const useTagListQuery = () => {
  const { token } = useAuth();
  return useQuery({
    queryKey: contentKeys.tags(),
    queryFn: (): Promise<Tag[]> => getTagList(token!),
    enabled: !!token,
  });
};

/**
 * Whether a PDF indexing job is running. Polls every 3s while it is, and
 * refreshes the unvalidated count on each poll since the job keeps adding
 * cards that need validating.
 */
export const useIndexingStatusQuery = () => {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: contentKeys.indexingStatus(),
    queryFn: async () => {
      const data = await getIndexingStatus(token!);
      queryClient.invalidateQueries({ queryKey: contentKeys.unvalidatedCount() });
      return data;
    },
    enabled: !!token,
    refetchInterval: (query) => (query.state.data === true ? 3000 : false),
    refetchIntervalInBackground: true,
  });
};

export const useUnvalidatedCountQuery = () => {
  const { token } = useAuth();
  return useQuery({
    queryKey: contentKeys.unvalidatedCount(),
    queryFn: () => getUnvalidatedCardsCount(token!),
    enabled: !!token,
  });
};

/** The next card to validate; only fetched while the validation dialog is open. */
export const useNextUnvalidatedCardQuery = (enabled: boolean) => {
  const { token } = useAuth();
  return useQuery({
    queryKey: contentKeys.nextUnvalidated(),
    queryFn: () => getNextUnvalidatedCard(token!),
    enabled: !!token && enabled,
  });
};

/**
 * PDF upload history for the "PDF upload status" dialog. Fetched only while
 * the dialog is open, and refetched every time it opens (staleTime 0), as the
 * old effect did.
 */
export const useIndexingHistoryQuery = (enabled: boolean) => {
  const { token } = useAuth();
  return useQuery({
    queryKey: contentKeys.indexingHistory(),
    queryFn: async () => (await getDocIndexingStatusData(token!)) || [],
    enabled: !!token && enabled,
    staleTime: 0,
  });
};

/* ------------------------------------------------------------------ */
/* Content writes                                                      */
/* ------------------------------------------------------------------ */

/** Archiving changes the list and may remove an unvalidated card. */
const invalidateAfterArchive = (queryClient: ReturnType<typeof useQueryClient>) =>
  Promise.all([
    queryClient.invalidateQueries({ queryKey: contentKeys.list() }),
    queryClient.invalidateQueries({ queryKey: contentKeys.unvalidatedCount() }),
    queryClient.invalidateQueries({ queryKey: contentKeys.nextUnvalidated() }),
  ]);

/** Archive ("delete") one card. */
export const useArchiveContentMutation = () => {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (contentId: number) => archiveContent(contentId, token!),
    onSuccess: () => invalidateAfterArchive(queryClient),
  });
};

export interface BulkArchiveResult {
  successCount: number;
  failedContentIds: number[];
}

/**
 * Archive several cards, in batches of 20 so we don't fire dozens of requests
 * at once. Per-card failures are collected rather than thrown, so the caller
 * can report partial success and keep the failed ones selected.
 */
export const useBulkArchiveContentMutation = () => {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (contentIds: number[]): Promise<BulkArchiveResult> => {
      const BATCH_SIZE = 20;
      let successCount = 0;
      const failedContentIds: number[] = [];
      for (let i = 0; i < contentIds.length; i += BATCH_SIZE) {
        const batch = contentIds.slice(i, i + BATCH_SIZE);
        await Promise.all(
          batch.map(async (content_id) => {
            try {
              await archiveContent(content_id, token!);
              successCount++;
            } catch (error) {
              console.error(`Failed to delete content ID ${content_id}:`, error);
              failedContentIds.push(content_id);
            }
          }),
        );
      }
      return { successCount, failedContentIds };
    },
    // Some cards may have been archived even if something went wrong.
    onSettled: () => invalidateAfterArchive(queryClient),
  });
};

/** Approve a card in validation mode. */
export const useValidateContentMutation = () => {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (contentId: number) => validateContent(contentId, token!),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: contentKeys.list() }),
        queryClient.invalidateQueries({ queryKey: contentKeys.unvalidatedCount() }),
        queryClient.invalidateQueries({ queryKey: contentKeys.nextUnvalidated() }),
      ]),
  });
};

/** Create a card (`content_id === null`) or update an existing one. */
export const useSaveContentMutation = () => {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      contentId,
      body,
    }: {
      contentId: number | null;
      body: ContentBody;
    }): Promise<Content> =>
      contentId === null
        ? createContent(body, token!)
        : editContent(contentId, body, token!),
    onSuccess: (_data, { contentId }) => {
      // Not awaited: the editor navigates away right after saving.
      queryClient.invalidateQueries({ queryKey: contentKeys.list() });
      if (contentId !== null) {
        queryClient.invalidateQueries({ queryKey: contentKeys.detail(contentId) });
      }
    },
  });
};

/**
 * CSV import. Resolves with `{status, data}` on success and `{status, detail}`
 * for a rejected file (the modal shows the per-row errors); only throws on a
 * network failure.
 */
export const useBulkUploadContentsMutation = () => {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => bulkUploadContents(file, token!),
    onSuccess: (response) => {
      if (response.status !== 200) return;
      // Imported rows can add cards and tags.
      queryClient.invalidateQueries({ queryKey: contentKeys.list() });
      queryClient.invalidateQueries({ queryKey: contentKeys.tags() });
    },
  });
};

/** Upload a PDF/ZIP for card generation; the status button starts polling. */
export const usePostDocumentToIndexMutation = () => {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => postDocumentToIndex(file, token!),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: contentKeys.indexingStatus() }),
        queryClient.invalidateQueries({ queryKey: contentKeys.indexingHistory() }),
      ]),
  });
};

/**
 * Fetch everything the CSV download needs, fresh from the API (not the
 * cache), at the moment the user clicks Download. Tags are only fetched when
 * there is content to export.
 */
export const useDownloadContentsMutation = () => {
  const { token } = useAuth();
  return useMutation({
    mutationFn: async (): Promise<{ contents: Content[]; tags: Tag[] }> => {
      const contents: Content[] = await getContentList({ token: token!, skip: 0 });
      if (contents.length === 0) return { contents: [], tags: [] };
      const tags: Tag[] = await getTagList(token!);
      return { contents, tags };
    },
  });
};

/* ------------------------------------------------------------------ */
/* Tag writes (editor)                                                 */
/* ------------------------------------------------------------------ */

export const useCreateTagMutation = () => {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tagName: string): Promise<Tag> => createTag(tagName, token!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: contentKeys.tags() }),
  });
};

/** Deleting a tag also strips it from every card, so the list is refreshed too. */
export const useDeleteTagMutation = () => {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tagId: number) => deleteTag(tagId, token!),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: contentKeys.tags() }),
        queryClient.invalidateQueries({ queryKey: contentKeys.list() }),
      ]),
  });
};

/* ------------------------------------------------------------------ */
/* Test sidebars: search, chat and response feedback                   */
/* ------------------------------------------------------------------ */

/**
 * "Test search". Resolves with `{status, ...body}`, including for HTTP errors
 * (`{status, error}`), which the sidebar shows; throws only when there was
 * no response at all.
 */
export const useSearchMutation = () => {
  const { token } = useAuth();
  return useMutation({
    mutationFn: ({
      question,
      generateLLMResponse,
    }: {
      question: string;
      generateLLMResponse: boolean;
    }) => getSearch(question, generateLLMResponse, token!),
  });
};

/** "Test chat". Pass the session id from the first reply to continue a chat. */
export const useChatMutation = () => {
  const { token } = useAuth();
  return useMutation({
    mutationFn: ({ question, sessionId }: { question: string; sessionId?: number }) =>
      getChat(question, true, token!, sessionId),
  });
};

export const useResponseFeedbackMutation = () => {
  const { token } = useAuth();
  return useMutation({
    mutationFn: ({
      queryId,
      sentiment,
      feedbackSecretKey,
    }: {
      queryId: number;
      sentiment: string;
      feedbackSecretKey: string;
    }) => postResponseFeedback(queryId, sentiment, feedbackSecretKey, token!),
  });
};
