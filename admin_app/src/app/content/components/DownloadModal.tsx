import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import { useAuth } from "@/utils/auth";
import Papa from "papaparse";
import { useState } from "react";
import { LoadingButton } from "@mui/lab";
import { Content, Tag } from "../types";
import { Layout } from "@/components/Layout";
import { getContentList, getTagList } from "../api";
import { handleApiError } from "@/utils/api";

interface ContentDownload {
  content_id: number | null;
  title: string;
  text: string;
  tags: string[]; // tag names, not IDs
  content_metadata: string;
  positive_votes: number;
  negative_votes: number;
  created_datetime_utc: string;
  updated_datetime_utc: string;
}

const DownloadModal = ({
  open,
  onClose,
  onFailedDownload,
  onNoDataFound,
}: {
  open: boolean;
  onClose: () => void;
  onFailedDownload: (error_message: string) => void;
  onNoDataFound: () => void;
}) => {
  const { token, accessLevel } = useAuth();
  const [loading, setLoading] = useState(false);

  const fetchAndTransformContents = async () => {
    // fetch all contents
    const raw_json_contents = await getContentList({
      token: token!,
      skip: 0,
    });
    if (raw_json_contents.length === 0) {
      return [];
    }
    // fetch all tags (to be able to map tag IDs to tag names)
    const tags_json = await getTagList(token!);
    const tag_list = Object.values<Tag>(tags_json);
    const tag_dict = tag_list.reduce((acc: Record<string, string>, tag: Tag) => {
      acc[tag.tag_id] = tag.tag_name;
      return acc;
    }, {});
    // convert fetched contents to list of json objects
    const list_json_contents = Object.values(raw_json_contents);
    // Convert to ContentDownload structure with tag names and metadata as string
    const list_json_content_download: ContentDownload[] = (
      list_json_contents as Content[]
    ).map((content: Content) => {
      return {
        content_id: content.content_id,
        title: content.content_title,
        text: content.content_text,
        tags: content.content_tags.map((tag_id) => tag_dict[tag_id]),
        content_metadata: JSON.stringify(content.content_metadata),
        positive_votes: content.positive_votes,
        negative_votes: content.negative_votes,
        created_datetime_utc: content.created_datetime_utc,
        updated_datetime_utc: content.updated_datetime_utc,
      };
    });

    return list_json_content_download;
  };

  const downloadCSV = (csvData: string, fileName: string) => {
    const blob = new Blob([csvData], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", fileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDownloadContent = async (
    fetchAndTransformContents: () => Promise<any[]>,
    onNoDataFound: () => void,
    onFailedDownload: (error_message: string) => void,
    setLoading: (loading: boolean) => void,
    onClose: () => void,
  ) => {
    setLoading(true);
    try {
      const list_json_content_download = await fetchAndTransformContents();
      if (list_json_content_download.length === 0) {
        onNoDataFound();
        return;
      }
      const csv = Papa.unparse(list_json_content_download);
      const now = new Date();
      const timestamp = `${now.getFullYear()}_${String(now.getMonth() + 1).padStart(
        2,
        "0",
      )}_${String(now.getDate()).padStart(2, "0")}_${String(now.getHours()).padStart(
        2,
        "0",
      )}${String(now.getMinutes()).padStart(2, "0")}${String(now.getSeconds()).padStart(
        2,
        "0",
      )}`;
      const filename = `content_${timestamp}.csv`;
      downloadCSV(csv, filename);
    } catch (error) {
      try {
        handleApiError(error, "Failed to download content");
      } catch (apiError: any) {
        onFailedDownload(apiError.message);
      }
    } finally {
      setLoading(false);
      onClose();
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      aria-labelledby="download-dialog-title"
      aria-describedby="download-dialog-description"
    >
      <DialogTitle id="download-dialog-title">
        Download all contents?
        <Layout.Spacer horizontal multiplier={50} />
      </DialogTitle>
      <DialogContent>
        <DialogContentText id="download-dialog-description">
          This action will download all contents as a CSV file.
        </DialogContentText>
      </DialogContent>
      <DialogActions sx={{ marginBottom: 1, marginRight: 1 }}>
        <Button onClick={onClose}>Cancel</Button>
        <LoadingButton
          variant="contained"
          autoFocus
          startIcon={<FileDownloadIcon />}
          loading={loading}
          loadingPosition="start"
          onClick={() =>
            handleDownloadContent(
              fetchAndTransformContents,
              onNoDataFound,
              onFailedDownload,
              setLoading,
              onClose,
            )
          }
        >
          Download
        </LoadingButton>
      </DialogActions>
    </Dialog>
  );
};

export { DownloadModal };
