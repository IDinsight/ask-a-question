import React, { useState, useCallback, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import {
  IconAlertCircle,
  IconCircleCheck,
  IconFileTypePdf,
  IconUpload,
} from "@tabler/icons-react";

import { Alert, AlertAction, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
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
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent className="gap-5 p-6 text-sm sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">
            Generate new content from PDF
          </DialogTitle>
          <DialogDescription className="text-sm">
            Generate new contents from PDF files into AAQ. The system will
            automatically create cards from the file content.
          </DialogDescription>
        </DialogHeader>

        <ul className="flex list-disc flex-col gap-1 pl-5 text-muted-foreground">
          <li>Maximum file size is 100MB.</li>
          <li>Upload either a single PDF or a ZIP file with multiple PDFs.</li>
        </ul>

        {error && (
          <Alert variant="destructive">
            <IconAlertCircle />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Drop zone: click to browse or drag a file in */}
        <div
          {...getRootProps()}
          className={cn(
            "flex min-h-[20vh] cursor-pointer flex-col items-center justify-center gap-2 border-2 border-dashed p-6 text-center text-muted-foreground transition-colors outline-none hover:border-primary focus-visible:border-primary",
            isDragActive && "border-primary bg-primary/5",
          )}
        >
          <input {...getInputProps()} />
          <IconUpload className="size-6" />
          <p>
            {isDragActive
              ? "Drop the file here..."
              : "Drag and drop a PDF/ZIP file here, or click to select a file"}
          </p>
          {files.map((file) => (
            <p
              key={file.name}
              className="flex items-center gap-1.5 font-medium text-foreground"
            >
              <IconFileTypePdf className="size-4" />
              {file.name}
            </p>
          ))}
        </div>

        {importErrorMessages.map((message, index) => (
          <Alert key={index} variant="destructive">
            <IconAlertCircle />
            <AlertDescription>{message}</AlertDescription>
          </Alert>
        ))}
        {importSuccess && (
          <Alert>
            <IconCircleCheck />
            <AlertDescription>Card generation task successfully started!</AlertDescription>
            <AlertAction>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onClose();
                  setOpenIndexHistoryModal(true);
                }}
              >
                Check status
              </Button>
            </AlertAction>
          </Alert>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {importSuccess ? "Close" : "Cancel"}
          </Button>
          {!importSuccess && (
            <Button
              disabled={files.length === 0 || loading || !!error}
              autoFocus
              onClick={handleSubmit}
            >
              {loading && <Spinner data-icon="inline-start" />}
              Import
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
