import React, { useState, useEffect } from "react";
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Typography,
} from "@mui/material";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { LoadingButton } from "@mui/lab";
import FileUploadIcon from "@mui/icons-material/FileUpload";
import CheckIcon from "@mui/icons-material/Check";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import { Layout } from "./Layout";
import { appColors, sizes } from "@/utils";

interface CustomError {
  type: string;
  description: string;
}

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
  const [importErrorMessages, setImportErrorMessages] = useState<string[]>([]);
  const [importSuccess, setImportSuccess] = useState<boolean | null>(null);

  const handleClose = () => {
    onClose();
    setSelectedFile(null);
    setImportErrorMessages([]);
    setImportSuccess(false);
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files ? event.target.files[0] : null;
    setSelectedFile(file);
  };

  const handleImportClick = async () => {
    if (selectedFile) {
      setLoading(true);
      // add artifical delay to show loading spinner (for UX)
      await new Promise((resolve) => setTimeout(resolve, 500));
      try {
        const response = await apiCalls.bulkUploadContents(
          selectedFile,
          token!,
        );
        if (response.status === 200) {
          setImportSuccess(true);
          setSelectedFile(null);
        } else {
          console.error("Error uploading file:", response.detail);
          if (response.detail.errors) {
            const errorDescriptions = response.detail.errors.map(
              (error: CustomError) => error.description,
            );
            setImportErrorMessages(errorDescriptions);
          } else {
            setImportErrorMessages(["An unknown error occurred"]);
          }
        }
      } catch (error) {
        console.error("Error during import:", error);
        setImportErrorMessages(["An unexpected error occurred"]);
      } finally {
        setLoading(false);
      }
    } else {
      console.error("No file selected");
      setImportErrorMessages(["No file selected"]);
    }
  };

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
          <br />
          <br />
          ⚠️ Be careful not to upload duplicates of what's already in the
          database.
        </DialogContentText>
        <Layout.Spacer multiplier={2} />
        <Layout.FlexBox
          flexDirection="row"
          justifyContent="left"
          alignItems="center"
          gap={sizes.baseGap}
        >
          <Layout.Spacer horizontal />
          <input
            id="choose-file"
            type="file"
            accept=".csv"
            hidden
            onChange={handleFileChange}
          />
          <label htmlFor="choose-file">
            <Button
              variant="outlined"
              component="span"
              startIcon={<CloudUploadIcon />}
            >
              Upload
            </Button>
          </label>
          <Typography variant="body1" fontSize={14} color={appColors.primary}>
            {selectedFile ? selectedFile.name : "No file chosen"}
          </Typography>
          <Layout.Spacer horizontal />
        </Layout.FlexBox>
        {importErrorMessages.length > 0 && (
          <>
            <Layout.Spacer multiplier={2} />
            {importErrorMessages.map((error, index) => (
              <React.Fragment key={index}>
                <Alert variant="outlined" severity="error">
                  {error}
                </Alert>
                <Layout.Spacer multiplier={1} />
              </React.Fragment>
            ))}
          </>
        )}
        {importSuccess && (
          <>
            <Layout.Spacer multiplier={2} />
            <Alert variant="outlined" severity="success" sx={{ px: 3, py: 0 }}>
              File uploaded successfully!
            </Alert>
          </>
        )}
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
          onClick={handleImportClick}
        >
          {importSuccess ? "Imported" : "Check and import"}
        </LoadingButton>
      </DialogActions>
    </Dialog>
  );
};

export { ImportModal };
