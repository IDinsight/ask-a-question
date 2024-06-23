import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { useState, useEffect } from "react";
import { LoadingButton } from "@mui/lab";
import FileUploadIcon from "@mui/icons-material/FileUpload";
import CheckIcon from "@mui/icons-material/Check";
import { Layout } from "./Layout";

const ImportModal = ({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) => {
  const { token, accessLevel } = useAuth();
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importErrorMessage, setImportErrorMessage] = useState<string | null>(
    null,
  );
  const [importSuccess, setImportSuccess] = useState<boolean | null>(null);

  const handleClose = () => {
    onClose();
    setSelectedFile(null);
    setImportErrorMessage(null);
    setImportSuccess(false);
  };

  // Set a 3s timer to close the modal after a successful import
  useEffect(() => {
    let timerId: NodeJS.Timeout;
    if (importSuccess) {
      timerId = setTimeout(() => {
        handleClose();
        window.location.reload();
      }, 1500);
    }
    return () => clearTimeout(timerId);
  }, [importSuccess]);

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      aria-labelledby="alert-dialog-title"
      aria-describedby="alert-dialog-description"
    >
      <DialogTitle id="alert-dialog-title" sx={{ minWidth: "800px" }}>
        Import New Contents
      </DialogTitle>
      <DialogContent>
        <DialogContentText id="alert-dialog-description">
          You can use this feature to import new contents from a CSV file. The
          CSV file must include "content_title" and "content_text" as columns.
          <Layout.Spacer />
          ⚠️ Be careful not to upload duplicates of what's already in the
          database.
        </DialogContentText>
        <Layout.Spacer multiplier={2} />
        <Layout.FlexBox
          sx={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <input
            type="file"
            accept=".csv"
            onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
          />
        </Layout.FlexBox>
        {importErrorMessage ? (
          <>
            <Layout.Spacer multiplier={2} />
            <Alert variant="outlined" severity="error" sx={{ px: 3, py: 0 }}>
              {importErrorMessage}
            </Alert>
          </>
        ) : null}
        {importSuccess ? (
          <>
            <Layout.Spacer multiplier={2} />
            <Alert variant="outlined" severity="success" sx={{ px: 3, py: 0 }}>
              File uploaded successfully!
            </Alert>
          </>
        ) : null}
      </DialogContent>
      <DialogActions sx={{ marginBottom: 1, marginRight: 1 }}>
        <Button onClick={handleClose}>Cancel</Button>
        <LoadingButton
          variant="contained"
          disabled={!selectedFile || loading}
          autoFocus
          startIcon={importSuccess ? <CheckIcon /> : <FileUploadIcon />}
          loading={loading}
          loadingPosition="start"
          onClick={async () => {
            if (selectedFile) {
              setLoading(true);
              const response = await apiCalls.bulkUploadContents(
                selectedFile,
                token!,
              );
              if (response.status === 200) {
                setLoading(false);
                setImportSuccess(true);
                setSelectedFile(null);
              } else {
                console.error("Error uploading file:", response.detail);
                setImportErrorMessage(response.detail);
                setLoading(false);
              }
            } else {
              console.error("No file selected");
              setImportErrorMessage("No file selected");
              setLoading(false);
            }
          }}
        >
          {importSuccess ? "Imported" : "Check and import"}
        </LoadingButton>
      </DialogActions>
    </Dialog>
  );
};

export { ImportModal };
