import api, { handleApiError } from "@/utils/api";
import { AxiosError } from "axios";

/**
 * Plain async API calls for the content feature (and its /content/edit route).
 * Components never call these directly: they go through the TanStack Query
 * hooks in ./queries.ts. `getContentList` is also used by the dashboard.
 *
 * Errors: `handleApiError` throws `{status, message}` (CustomError) for 4xx
 * and a plain Error for 5xx/network failures.
 */
export type IndexingStatusResponse = boolean | { detail: string };

export interface DocIndexingTask {
  error_trace: string;
  finished_datetime_utc: string;
  upload_id: string;
  user_id: number;
  workspace_id: number;
  parent_file_name: string;
  created_datetime_utc: string;
  task_id: string;
  doc_name: string;
  task_status: string;
}

export interface DocIndexingStatusRow {
  fileName: string;
  status: "Ongoing" | "Done" | "Error";
  docsIndexed: string;
  errorTrace: string;
  created_at: string;
  finished_at: string;
  tasks: DocIndexingTask[];
}

export interface ContentBody {
  content_title: string;
  content_text: string;
  content_metadata: Record<string, unknown>;
}

export interface DocumentUploadResponse {
  status: number;
  detail: any;
}

const formatDate = (dateString: string) => {
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

const getContentList = async ({
  token,
  skip = 0,
  limit = 0,
}: {
  token: string;
  skip?: number;
  limit?: number;
}) => {
  try {
    const response = await api.get(`/content/?skip=${skip}&limit=${limit}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    let errorMessage = "Error fetching content list";
    handleApiError(error, errorMessage);
  }
};

const getContent = async (content_id: number, token: string) => {
  try {
    const response = await api.get(`/content/${content_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    let errorMessage = "Error fetching content";
    handleApiError(error, errorMessage);
  }
};

const archiveContent = async (content_id: number, token: string) => {
  try {
    const response = await api.patch(
      `/content/${content_id}`,
      {},
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return response.data;
  } catch (error) {
    let errorMessage = "Error archiving content";
    handleApiError(error, errorMessage);
  }
};

const deleteContent = async (content_id: number, token: string) => {
  try {
    const response = await api.delete(`/content/${content_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    let errorMessage = "Error deleting content";
    handleApiError(error, errorMessage);
  }
};

const editContent = async (content_id: number, content: ContentBody, token: string) => {
  try {
    const response = await api.put(`/content/${content_id}`, content, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    let errorMessage = "Error editing content";
    handleApiError(error, errorMessage);
  }
};

const createContent = async (content: ContentBody, token: string) => {
  try {
    const response = await api.post("/content/", content, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    let errorMessage = "Error creating content";
    handleApiError(error, errorMessage);
  }
};

const bulkUploadContents = async (file: File, token: string) => {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await api.post("/content/csv-upload", formData, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "multipart/form-data",
      },
    });

    return { status: response.status, data: response.data };
  } catch (error: any) {
    if (error.response) {
      const errorResponse = error.response.data;
      const detail = errorResponse.detail || "An unknown error occurred";
      return { status: error.response.status, detail: detail };
    } else {
      throw new Error("An unexpected error occurred during the bulk upload.");
    }
  }
};

const createTag = async (tag: string, token: string) => {
  try {
    const response = await api.post(
      "/tag/",
      { tag_name: tag },
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return response.data;
  } catch (error) {
    let errorMessage = "Error creating tag";
    handleApiError(error, errorMessage);
  }
};

const getTagList = async (token: string) => {
  try {
    const response = await api.get("/tag/", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    let errorMessage = "Error fetching tag list";
    handleApiError(error, errorMessage);
  }
};

const deleteTag = async (tag_id: number, token: string) => {
  try {
    const response = await api.delete(`/tag/${tag_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    let errorMessage = "Error deleting tag";
    handleApiError(error, errorMessage);
  }
};

/** Is a PDF indexing (docmuncher) job running? `{detail}` when the feature is off. */
const getIndexingStatus = async (token: string): Promise<IndexingStatusResponse> => {
  try {
    const response = await api.get("/docmuncher/status/is_job_running", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    const errorMessage = "Error fetching indexing status";
    handleApiError(error, errorMessage);
    throw error; // unreachable: handleApiError always throws
  }
};

/** How many cards (e.g. generated from a PDF) are waiting for validation. */
const getUnvalidatedCardsCount = async (token: string): Promise<number> => {
  try {
    const response = await api.get("/content/unvalidated-count", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    const errorMessage = "Error fetching unvalidated count";
    handleApiError(error, errorMessage);
    throw error;
  }
};

/** The next card waiting for validation (`null` when there is none). */
const getNextUnvalidatedCard = async (token: string) => {
  try {
    const response = await api.get("/content/next-unvalidated", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    const errorMessage = "Error fetching next unvalidated card";
    handleApiError(error, errorMessage);
    throw error;
  }
};

const validateContent = async (content_id: number, token: string) => {
  try {
    const response = await api.patch(
      `/content/validate/${content_id}`,
      {},
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return response.data;
  } catch (error) {
    const errorMessage = "Error validating content card";
    handleApiError(error, errorMessage);
    throw error;
  }
};

/**
 * Upload a PDF/ZIP for card generation. Unlike the other calls this throws a
 * plain Error carrying the backend's `detail`, which the PDF modal shows.
 */
const postDocumentToIndex = async (
  file: File,
  token: string,
): Promise<DocumentUploadResponse> => {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await api.post("/docmuncher/upload", formData, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "multipart/form-data",
      },
    });
    return { status: response.status, detail: response.data };
  } catch (error: any) {
    if (error.response) {
      const errorResponse = error.response.data;
      throw new Error(errorResponse.detail || "Error indexing document");
    }
    throw new Error("Error indexing document");
  }
};

const getDocIndexingStatusData = async (
  token: string,
): Promise<DocIndexingStatusRow[] | undefined> => {
  try {
    const response = await api.get("/docmuncher/status/data", {
      headers: { Authorization: `Bearer ${token}` },
    });

    return response.data
      .map((entry: any) => ({
        fileName: entry.parent_file_name,
        status:
          entry.overall_status === "Success"
            ? "Done"
            : entry.overall_status === "Failed"
            ? "Error"
            : "Ongoing",
        docsIndexed: `${entry.docs_indexed} of ${entry.docs_total}`,
        errorTrace: entry.error_trace || "",
        created_at: formatDate(entry.created_datetime_utc),
        finished_at: formatDate(entry.finished_datetime_utc),
        tasks: (entry.tasks as DocIndexingTask[]) || [],
      }))
      .sort(
        (a: DocIndexingStatusRow, b: DocIndexingStatusRow) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );
  } catch (error) {
    let errorMessage = "Error fetching indexing status";
    handleApiError(error, errorMessage);
  }
};

export {
  formatDate,
  getContentList,
  getContent,
  archiveContent,
  deleteContent,
  editContent,
  createContent,
  bulkUploadContents,
  createTag,
  getTagList,
  deleteTag,
  getIndexingStatus,
  postDocumentToIndex,
  getDocIndexingStatusData,
  getUnvalidatedCardsCount,
  getNextUnvalidatedCard,
  validateContent,
};

/* Test sidebars: search / chat / response feedback (moved from utils/api.ts). */
const getSearch = async (
  question: string,
  generate_llm_response: boolean,
  token: string,
): Promise<{ status: number; data?: any; error?: any } | undefined> => {
  try {
    const response = await api.post(
      "/search",
      {
        query_text: question,
        generate_llm_response,
      },
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );

    return { status: response.status, ...response.data };
  } catch (err) {
    const error = err as AxiosError;
    if (error.response) {
      return { status: error.response.status, error: error.response.data };
    } else {
      handleApiError(error, "Error performing search");
      console.error("Error performing search", error.message);
    }
  }
};

const getChat = async (
  question: string,
  generate_llm_response: boolean,
  token: string,
  session_id?: number,
): Promise<{ status: number; data?: any; error?: any } | undefined> => {
  try {
    const response = await api.post(
      "/chat",
      {
        query_text: question,
        generate_llm_response,
        session_id,
      },
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return { status: response.status, ...response.data };
  } catch (err) {
    const error = err as AxiosError;
    handleApiError(error, "Error returning chat response");
    console.error("Error returning chat response", error.message);
  }
};
const postResponseFeedback = async (
  query_id: number,
  feedback_sentiment: string,
  feedback_secret_key: string,
  token: string,
) => {
  try {
    const response = await api.post(
      "/response-feedback",
      {
        query_id,
        feedback_sentiment,
        feedback_secret_key,
      },
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    return response.data;
  } catch (error) {
    handleApiError(error, "Error sending response feedback");
    console.error("Error sending response feedback", error);
  }
};

export { getSearch, getChat, postResponseFeedback };
