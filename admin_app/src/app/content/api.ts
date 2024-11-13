import api from "@/utils/api";

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
    throw new Error("Error fetching content list");
  }
};

const getContent = async (content_id: number, token: string) => {
  try {
    const response = await api.get(`/content/${content_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching content");
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
    throw new Error("Error archiving content");
  }
};

const deleteContent = async (content_id: number, token: string) => {
  try {
    const response = await api.delete(`/content/${content_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error deleting content");
  }
};

const editContent = async (content_id: number, content: ContentBody, token: string) => {
  try {
    const response = await api.put(`/content/${content_id}`, content, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error editing content");
  }
};

const createContent = async (content: ContentBody, token: string) => {
  try {
    const response = await api.post("/content/", content, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error creating content");
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
    throw new Error("Error creating tag");
  }
};

const getTagList = async (token: string) => {
  try {
    const response = await api.get("/tag/", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error fetching tag list");
  }
};

const deleteTag = async (tag_id: number, token: string) => {
  try {
    const response = await api.delete(`/tag/${tag_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw new Error("Error deleting tag");
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
};
