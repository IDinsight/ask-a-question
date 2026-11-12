/**
 * TanStack Query hooks for the content feature (/content and /content/edit).
 * Every API call those pages make goes through a hook here; ContentWrapper and
 * ContentEditWrapper are the only callers.
 *
 * Conventions: see workspace-management/queries.ts (generated client via
 * /bff, hooks disabled until there is a token, generated query keys).
 * - Mutations invalidate the queries they affect instead of the old
 *   "bump a refreshKey and refetch everything" pattern.
 * - The spec types content tags loosely (`unknown[]`), so content responses
 *   are read through the UI types in ./types.ts.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  archiveContent,
  bulkUploadContents,
  chat,
  createContent,
  createTag,
  deleteTag,
  editContent,
  feedback,
  retrieveContent,
  retrieveTag,
  search,
  uploadDocument,
  validateContentCard,
  type FeedbackSentiment,
} from "@/client";
import {
  getAllJobsOptions,
  getAllJobsQueryKey,
  getJobsRunningForUserOptions,
  getJobsRunningForUserQueryKey,
  getNextUnvalidatedContentOptions,
  getNextUnvalidatedContentQueryKey,
  getUnvalidatedCardCountOptions,
  getUnvalidatedCardCountQueryKey,
  retrieveContentByIdOptions,
  retrieveContentByIdQueryKey,
  retrieveContentOptions,
  retrieveContentQueryKey,
  retrieveTagOptions,
  retrieveTagQueryKey,
} from "@/client/@tanstack/react-query.gen";
import type { QueryResponse } from "@/client";
import { ApiServerError, isCustomError } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import type {
  Content,
  ContentBody,
  DocIndexingStatusRow,
  DocIndexingTask,
  CsvUploadResult,
  DocumentUploadResponse,
  IndexingHistoryEntry,
  IndexingStatusResponse,
  Tag,
} from "./types";

/**
 * Search/chat result: the HTTP status plus the response body spread on top
 * (fields are optional because a failed search returns `error` instead).
 */
export type QueryResult = {
  status: number;
  error?: unknown;
} & Partial<QueryResponse>;

/* ------------------------------------------------------------------ */
/* Query keys                                                          */
/* ------------------------------------------------------------------ */

/**
 * The content list request: every card (limit 0 = no limit), as before.
 * Shared by the list query and its invalidations so the keys always match.
 */
const CONTENT_LIST = { query: { skip: 0, limit: 0 } };

/** Named aliases for the generated keys. */
export const contentKeys = {
  /** Prefix of every GET /content/ key (also the dashboard's has-content check). */
  list: () => retrieveContentQueryKey(),
  detail: (contentId: number) =>
    retrieveContentByIdQueryKey({ path: { content_id: contentId } }),
  tags: () => retrieveTagQueryKey(),
  unvalidatedCount: () => getUnvalidatedCardCountQueryKey(),
  nextUnvalidated: () => getNextUnvalidatedContentQueryKey(),
  indexingStatus: () => getJobsRunningForUserQueryKey(),
  indexingHistory: () => getAllJobsQueryKey(),
};

/* ------------------------------------------------------------------ */
/* Formatting                                                          */
/* ------------------------------------------------------------------ */

export const formatDate = (dateString: string) => {
  if (!dateString) return "—";
  const date = new Date(dateString);
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
};

/** GET /docmuncher/status/data rows -> dialog rows, newest first. */
const toIndexingHistoryRows = (entries: unknown[]): DocIndexingStatusRow[] =>
  (entries as IndexingHistoryEntry[])
    .map((entry) => ({
      fileName: entry.parent_file_name,
      status: (entry.overall_status === "Success"
        ? "Done"
        : entry.overall_status === "Failed"
        ? "Error"
        : "Ongoing") as DocIndexingStatusRow["status"],
      docsIndexed: `${entry.docs_indexed} of ${entry.docs_total}`,
      errorTrace: entry.error_trace || "",
      created_at: formatDate(entry.created_datetime_utc),
      finished_at: formatDate(entry.finished_datetime_utc),
      tasks: (entry.tasks as DocIndexingTask[]) || [],
    }))
    .sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );

/* ------------------------------------------------------------------ */
/* Reads                                                               */
/* ------------------------------------------------------------------ */

/** Every (non-archived) content card in the workspace. */
export const useContentListQuery = () => {
  const { token } = useAuth();
  return useQuery({
    ...retrieveContentOptions(CONTENT_LIST),
    select: (data) => data as unknown as Content[],
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
    // -1 only builds a key while idle (contentId null); it is never fetched.
    ...retrieveContentByIdOptions({ path: { content_id: contentId ?? -1 } }),
    select: (data) => data as unknown as Content,
    enabled: !!token && contentId !== null,
    gcTime: 0,
  });
};

export const useTagListQuery = () => {
  const { token } = useAuth();
  return useQuery({
    ...retrieveTagOptions(),
    select: (data): Tag[] => data,
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
  const { queryKey, queryFn } = getJobsRunningForUserOptions();
  return useQuery({
    queryKey,
    // The spec says boolean; the backend sends {detail} when docmuncher is off.
    queryFn: async (context): Promise<IndexingStatusResponse> => {
      const data = await queryFn!(context);
      queryClient.invalidateQueries({
        queryKey: contentKeys.unvalidatedCount(),
      });
      return data as IndexingStatusResponse;
    },
    enabled: !!token,
    refetchInterval: (query) => (query.state.data === true ? 3000 : false),
    refetchIntervalInBackground: true,
  });
};

export const useUnvalidatedCountQuery = () => {
  const { token } = useAuth();
  return useQuery({
    ...getUnvalidatedCardCountOptions(),
    enabled: !!token,
  });
};

/** The next card to validate; only fetched while the validation dialog is open. */
export const useNextUnvalidatedCardQuery = (enabled: boolean) => {
  const { token } = useAuth();
  return useQuery({
    ...getNextUnvalidatedContentOptions(),
    // null when there is no card left to validate. Typed `any` as before the
    // refactor: ContentWrapper spreads it into ContentViewModal, which only
    // renders once a card exists.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    select: (data): any => data,
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
    ...getAllJobsOptions(),
    select: (data) => toIndexingHistoryRows(data ?? []),
    enabled: !!token && enabled,
    staleTime: 0,
  });
};

/* ------------------------------------------------------------------ */
/* Content writes                                                      */
/* ------------------------------------------------------------------ */

/** Archiving changes the list and may remove an unvalidated card. */
const invalidateAfterArchive = (
  queryClient: ReturnType<typeof useQueryClient>,
) =>
  Promise.all([
    queryClient.invalidateQueries({ queryKey: contentKeys.list() }),
    queryClient.invalidateQueries({ queryKey: contentKeys.unvalidatedCount() }),
    queryClient.invalidateQueries({ queryKey: contentKeys.nextUnvalidated() }),
  ]);

/** Archive ("delete") one card. */
export const useArchiveContentMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (contentId: number) =>
      (await archiveContent({ path: { content_id: contentId } })).data,
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
              await archiveContent({ path: { content_id } });
              successCount++;
            } catch (error) {
              console.error(
                `Failed to delete content ID ${content_id}:`,
                error,
              );
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
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (contentId: number) =>
      (await validateContentCard({ path: { content_id: contentId } })).data,
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: contentKeys.list() }),
        queryClient.invalidateQueries({
          queryKey: contentKeys.unvalidatedCount(),
        }),
        queryClient.invalidateQueries({
          queryKey: contentKeys.nextUnvalidated(),
        }),
      ]),
  });
};

/** Create a card (`content_id === null`) or update an existing one. */
export const useSaveContentMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      contentId,
      body,
    }: {
      contentId: number | null;
      body: ContentBody;
    }): Promise<Content> => {
      const { data } =
        contentId === null
          ? await createContent({ body })
          : await editContent({ path: { content_id: contentId }, body });
      return data as unknown as Content;
    },
    onSuccess: (_data, { contentId }) => {
      // Not awaited: the editor navigates away right after saving.
      queryClient.invalidateQueries({ queryKey: contentKeys.list() });
      if (contentId !== null) {
        queryClient.invalidateQueries({
          queryKey: contentKeys.detail(contentId),
        });
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
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (file: File): Promise<CsvUploadResult> => {
      try {
        const { data, response } = await bulkUploadContents({ body: { file } });
        return { status: response.status, data };
      } catch (error) {
        // A rejected file: hand back the backend's `detail` (per-row errors).
        if (isCustomError(error) || error instanceof ApiServerError) {
          const body = error.body as { detail?: unknown } | undefined;
          return {
            status: error.status,
            // Assumes the backend's 4xx `detail` matches CsvUploadResult.
            detail:
              (body?.detail as CsvUploadResult["detail"]) ||
              "An unknown error occurred",
          };
        }
        throw new Error("An unexpected error occurred during the bulk upload.");
      }
    },
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
  const queryClient = useQueryClient();
  return useMutation({
    // Throws a plain Error carrying the backend's `detail`, which the PDF modal shows.
    mutationFn: async (file: File): Promise<DocumentUploadResponse> => {
      try {
        const { data, response } = await uploadDocument({ body: { file } });
        return { status: response.status, detail: data };
      } catch (error) {
        throw new Error(
          isCustomError(error) || error instanceof ApiServerError
            ? error.message
            : "Error indexing document",
        );
      }
    },
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({
          queryKey: contentKeys.indexingStatus(),
        }),
        queryClient.invalidateQueries({
          queryKey: contentKeys.indexingHistory(),
        }),
      ]),
  });
};

/**
 * Fetch everything the CSV download needs, fresh from the API (not the
 * cache), at the moment the user clicks Download. Tags are only fetched when
 * there is content to export.
 */
export const useDownloadContentsMutation = () =>
  useMutation({
    mutationFn: async (): Promise<{ contents: Content[]; tags: Tag[] }> => {
      const { data } = await retrieveContent(CONTENT_LIST);
      const contents = data as unknown as Content[];
      if (contents.length === 0) return { contents: [], tags: [] };
      const { data: tags } = await retrieveTag();
      return { contents, tags };
    },
  });

/* ------------------------------------------------------------------ */
/* Tag writes (editor)                                                 */
/* ------------------------------------------------------------------ */

export const useCreateTagMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (tagName: string): Promise<Tag> =>
      (await createTag({ body: { tag_name: tagName } })).data,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: contentKeys.tags() }),
  });
};

/** Deleting a tag also strips it from every card, so the list is refreshed too. */
export const useDeleteTagMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (tagId: number) =>
      (await deleteTag({ path: { tag_id: tagId } })).data,
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
export const useSearchMutation = () =>
  useMutation({
    mutationFn: async ({
      question,
      generateLLMResponse,
    }: {
      question: string;
      generateLLMResponse: boolean;
    }): Promise<QueryResult> => {
      try {
        const { data, response } = await search({
          body: {
            query_text: question,
            generate_llm_response: generateLLMResponse,
          },
        });
        return { status: response.status, ...data };
      } catch (error) {
        if (isCustomError(error) || error instanceof ApiServerError) {
          return { status: error.status, error: error.body };
        }
        throw error;
      }
    },
  });

/** "Test chat". Pass the session id from the first reply to continue a chat. */
export const useChatMutation = () =>
  useMutation({
    mutationFn: async ({
      question,
      sessionId,
    }: {
      question: string;
      sessionId?: number;
    }): Promise<QueryResult> => {
      const { data, response } = await chat({
        body: {
          query_text: question,
          generate_llm_response: true,
          session_id: sessionId,
        },
      });
      return { status: response.status, ...data };
    },
  });

export const useResponseFeedbackMutation = () =>
  useMutation({
    mutationFn: async ({
      queryId,
      sentiment,
      feedbackSecretKey,
    }: {
      queryId: number;
      sentiment: string;
      feedbackSecretKey: string;
    }) =>
      (
        await feedback({
          body: {
            query_id: queryId,
            feedback_sentiment: sentiment as FeedbackSentiment,
            feedback_secret_key: feedbackSecretKey,
          },
        })
      ).data,
  });
