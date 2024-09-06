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
import { useAuth } from "@/utils/auth";
import { LoadingButton } from "@mui/lab";
import NoteAddIcon from "@mui/icons-material/NoteAdd";
import { Layout } from "@/components/Layout";
import { appColors, sizes } from "@/utils";
import { bulkUploadContents } from "../api";

interface CustomError {
  type: string;
  description: string;
}

const ImportModal = ({ open, onClose }: { open: boolean; onClose: () => void }) => {
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
    // clear input so that the same file can be selected again
    event.target.value = "";
  };

  const handleImportClick = async () => {
    if (selectedFile) {
      setLoading(true);
      setImportErrorMessages([]);
      // add artifical delay to show loading spinner (for UX)
      await new Promise((resolve) => setTimeout(resolve, 500));
      try {
        const response = await bulkUploadContents(selectedFile, token!);
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
        setImportErrorMessages([
          "An unexpected error occurred. Please try again later.",
        ]);
      } finally {
        setLoading(false);
        setSelectedFile(null);
      }
    } else {
      console.error("No file selected");
      setImportErrorMessages(["No file selected"]);
    }
  };

  // modal auto-close after successful import
  useEffect(() => {
    let timerId: NodeJS.Timeout;
    if (importSuccess) {
      timerId = setTimeout(() => {
        handleClose();
        window.location.reload();
      }, 1000);
    }
    return () => clearTimeout(timerId);
  }, [importSuccess]);

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      aria-labelledby="import-dialog-title"
      aria-describedby="import-dialog-description"
    >
      <DialogTitle id="import-dialog-title">Import New Contents</DialogTitle>
      <DialogContent>
        <DialogContentText id="import-dialog-description">
          <p>
            You can use this feature to import new contents from a CSV file into AAQ.
          </p>
          <p>
            The CSV file should have the following columns:
            <ul>
              <li>
                <strong>
                  <code>title</code>
                </strong>
                : content title, up to 150 characters
              </li>
              <li>
                <strong>
                  <code>text</code>
                </strong>
                : content text, up to 2000 characters
              </li>
              <li>
                (Optional){" "}
                <strong>
                  <code>tags</code>
                </strong>
                : content tags, e.g. "tag1, tag2, tag3"
              </li>
            </ul>
          </p>
          <p>⚠️ Duplicate titles or texts will be rejected.</p>
        </DialogContentText>
        <Layout.Spacer multiplier={1} />
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
            <Button variant="outlined" component="span" startIcon={<NoteAddIcon />}>
              Attach File
            </Button>
          </label>
          <Typography variant="body1" fontSize={14} color={appColors.primary}>
            {selectedFile ? selectedFile.name : "Attach new file"}
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
            <Alert variant="standard" severity="success">
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
          loading={loading}
          onClick={handleImportClick}
        >
          {importSuccess ? "Imported" : "Check and import"}
        </LoadingButton>
      </DialogActions>
    </Dialog>
  );
};

export { ImportModal };
