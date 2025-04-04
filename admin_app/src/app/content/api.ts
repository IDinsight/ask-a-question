import api, { handleApiError } from "@/utils/api";

type IndexingStatusResponse = boolean | { detail: string };

export interface DocIndexingStatusRow {
  fileName: string;
  status: "Ongoing" | "Done" | "Error";
  docsIndexed: string;
  errorTrace: string;
  created_at: string;
  finished_at: string;
}

interface ContentBody {
  content_title: string;
  content_text: string;
  content_metadata: Record<string, unknown>;
}
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

const getIndexingStatus = async (
  token: string,
): Promise<IndexingStatusResponse | undefined> => {
  try {
    const response = await api.get("/docmuncher/status/is_job_running", {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (response.status === 200) {
      return response.data;
    } else {
      throw new Error("Unexpected response status");
    }
  } catch (error) {
    let errorMessage = "Error fetching indexing status";
    handleApiError(error, errorMessage);
  }
};

const postDocumentToIndex = async (file: File, token: string) => {
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
  } catch (error) {
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
};
