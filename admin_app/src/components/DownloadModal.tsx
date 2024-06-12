import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import Papa from "papaparse";
import { useState } from "react";
import { LoadingButton } from "@mui/lab";

const MAX_CARDS_TO_FETCH = 200;

const DownloadModal = ({
  open,
  onClose,
  onFailedDownload,
}: {
  open: boolean;
  onClose: () => void;
  onFailedDownload: () => void;
}) => {
  const { token, accessLevel } = useAuth();
  const [loading, setLoading] = useState(false);

  const fetchAndCleanContents = async () => {
    // fetch all contents
    const raw_json_data = await apiCalls.getContentList({
      token: token!,
      skip: 0,
      limit: MAX_CARDS_TO_FETCH,
    });
    // convert to list of json objects
    const json_data_list = Object.values(raw_json_data);
    // move content_id to be frst and drop user_id
    const ordered_json_data_list = json_data_list.map((item) => {
      const { user_id, content_id, ...rest } = item;
      return {
        content_id,
        ...rest,
      };
    });
    // stringify json element
    const processed_contents_json = ordered_json_data_list.map((item) => {
      return {
        ...item,
        content_metadata: JSON.stringify(item.content_metadata),
      };
    });
    // get list of tags and replace tag ids with tag names
    const tags_json = await apiCalls.getTagList(token!);
    const tag_list = Object.values(tags_json);
    const tag_dict = tag_list.reduce((acc, tag) => {
      acc[tag.tag_id] = tag.tag_name;
      return acc;
    }, {});
    processed_contents_json.forEach((item) => {
      item.content_tags = item.content_tags.map(
        (tag_id: number) => tag_dict[tag_id],
      );
    });

    return processed_contents_json;
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

  const handleDownloadContent = async () => {
    setLoading(true);
    try {
      const processed_contents_json = await fetchAndCleanContents();
      // convert to csv
      const csv = Papa.unparse(processed_contents_json);
      downloadCSV(csv, "content.csv");
    } catch (error) {
      console.error("Failed to download content", error);
      onFailedDownload();
    } finally {
      setLoading(false);
      onClose();
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      aria-labelledby="alert-dialog-title"
      aria-describedby="alert-dialog-description"
    >
      <DialogTitle id="alert-dialog-title" sx={{ minWidth: "800px" }}>
        {"Download all contents?"}
      </DialogTitle>
      <DialogContent>
        <DialogContentText id="alert-dialog-description">
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
          onClick={handleDownloadContent}
        >
          Download
        </LoadingButton>
      </DialogActions>
    </Dialog>
  );
};

export { DownloadModal };
