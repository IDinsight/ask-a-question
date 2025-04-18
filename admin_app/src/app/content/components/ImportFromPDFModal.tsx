import React, { useState, useCallback, useEffect } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  DialogContentText,
  Box,
  Typography,
  Alert,
} from "@mui/material";
import { useDropzone } from "react-dropzone";
import { Layout } from "@/components/Layout";
import { LoadingButton } from "@mui/lab";
import { usePostDocumentToIndex } from "../api";
import { useAuth } from "@/utils/auth";
import { useShowIndexingStatusStore } from "../store/indexingStatusStore";

interface CustomError {
  type: string;
  description: string;
}

interface ImportFromPDFModalProps {
  open: boolean;
  onClose: () => void;
}

export const ImportFromPDFModal: React.FC<ImportFromPDFModalProps> = ({
  open,
  onClose,
}) => {
  const { token } = useAuth();
  const { setIsOpen: setOpenIndexHistoryModal } = useShowIndexingStatusStore();
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [importErrorMessages, setImportErrorMessages] = useState<string[]>([]);
  const [importSuccess, setImportSuccess] = useState<boolean | null>(null);
  const { mutate: postDocumentToIndex } = usePostDocumentToIndex(token!);

  useEffect(() => {
    if (!open) {
      setFiles([]);
      setError("");
      setImportErrorMessages([]);
      setImportSuccess(false);
    }
  }, [open]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setError("");
    setFiles(acceptedFiles);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"], "application/zip": [".zip"] },
    multiple: false,

    maxSize: 100 * 1024 * 1024, // 100MB Max file size for now
    onDropRejected: (fileRejections) => {
      const rejection = fileRejections[0];
      if (rejection && rejection.errors && rejection.errors.length > 0) {
        const error = rejection.errors[0];
        if (error.code === "file-too-large") {
          setError(`File is too large. Maximum size is 100MB.`);
        } else if (error.code === "file-invalid-type") {
          setError("Only PDF files are allowed.");
        } else {
          setError(error.message || "File upload rejected");
        }
      } else {
        setError("An unknown error occurred.");
      }
    },
  });

  const handleSubmit = async () => {
    if (files.length > 0) {
      setLoading(true);
      setImportErrorMessages([]);
      // add artificial delay to show loading spinner (for UX)
      await new Promise((resolve) => setTimeout(resolve, 500));
      postDocumentToIndex(
        { file: files[0] },
        {
          onSuccess: () => {
            setImportSuccess(true);
            setFiles([]);
          },
          onError: (error: Error) => {
            setImportErrorMessages(["An error occurred: " + error.message]);
          },
          onSettled: () => {
            setLoading(false);
          },
        },
      );
    } else {
      setImportErrorMessages(["No file selected"]);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle id="import-pdf-dialog-title">
        Generate New Content From PDF
      </DialogTitle>
      <DialogContent>
        <DialogContentText id="import-pdf-dialog-description">
          <Typography>
            You can use this feature to generate new contents from PDF files into AAQ.
            The system will automatically create cards from file content.
          </Typography>
          <p>
            ⚠️ Maximum file size is 100MB.
            <br />
            ⚠️ Either upload a single PDF or a ZIP file with multiple PDFs.
          </p>
        </DialogContentText>
        <Layout.Spacer multiplier={1} />
        {error && (
          <>
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
            <Layout.Spacer multiplier={1} />
          </>
        )}
        <Box
          {...getRootProps()}
          sx={{
            border: "2px dashed #cccccc",
            borderRadius: 2,
            padding: 3,
            textAlign: "center",
            cursor: "pointer",
            display: "flex",
            flexDirection: "column",
            minHeight: "20vh",
            justifyContent: "center",
            alignItems: "center",
            "&:hover": {
              borderColor: "primary.main",
            },
          }}
        >
          <input {...getInputProps()} />
          <DialogContentText>
            {isDragActive ? (
              <Typography>Drop the PDF files here...</Typography>
            ) : (
              <Typography>
                Drag and drop a PDF/ZIP file here, or click to select file
              </Typography>
            )}
            {files.length > 0 && (
              <Box mt={2}>
                {files.map((file) => (
                  <Typography key={file.name} color="primary">
                    {file.name}
                  </Typography>
                ))}
              </Box>
            )}
          </DialogContentText>
        </Box>
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
            <Alert
              variant="standard"
              severity="success"
              action={
                <Box sx={{ display: "flex", gap: 1 }}>
                  <Button
                    variant="outlined"
                    color="inherit"
                    size="small"
                    onClick={() => {
                      onClose();
                      setOpenIndexHistoryModal(true);
                    }}
                  >
                    Check Status
                  </Button>
                </Box>
              }
            >
              Card generation task successfully started!
            </Alert>
          </>
        )}
      </DialogContent>
      <DialogActions sx={{ marginBottom: 1, marginRight: 1 }}>
        <Button onClick={onClose}>Cancel</Button>
        {!importSuccess && (
          <>
            <LoadingButton
              variant="contained"
              disabled={files.length === 0 || loading || !!error}
              autoFocus
              loading={loading}
              onClick={handleSubmit}
            >
              Import
            </LoadingButton>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};
