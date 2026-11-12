import React, { useState, useEffect, useRef } from "react";
import {
  IconAlertCircle,
  IconCircleCheck,
  IconFileUpload,
} from "@tabler/icons-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
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
import type { CsvUploadResult } from "../types";

const ImportFromCSVModal = ({
  open,
  onClose,
  uploadCsv,
}: {
  open: boolean;
  onClose: () => void;
  /**
   * Uploads the file. Resolves with `{status: 200}` on success or
   * `{status, detail}` when the backend rejects the file; rejects only on a
   * network failure. Supplied by ContentWrapper, which refreshes the list.
   */
  uploadCsv: (file: File) => Promise<CsvUploadResult>;
}) => {
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importErrorMessages, setImportErrorMessages] = useState<string[]>([]);
  const [importSuccess, setImportSuccess] = useState<boolean | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

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
        const response = await uploadCsv(selectedFile);
        if (response.status === 200) {
          setImportSuccess(true);
          setSelectedFile(null);
        } else {
          console.error("Error uploading file:", response.detail);
          // `detail` is per-row errors, or a plain message string.
          const detail = response.detail;
          if (typeof detail === "object" && detail.errors) {
            const errorDescriptions = detail.errors.map(
              (error) => error.description,
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

  // Modal auto-closes shortly after a successful import. (The card list is
  // refreshed by the upload mutation, so no page reload is needed.)
  // Hold the latest handleClose in a ref so the timer effect below doesn't
  // re-run (and restart the timer) every render. Updated in an effect, not
  // during render. (useEffectEvent would fit, but @types/react is still v18.)
  const handleCloseRef = useRef(handleClose);
  useEffect(() => {
    handleCloseRef.current = handleClose;
  });
  useEffect(() => {
    let timerId: NodeJS.Timeout;
    if (importSuccess) {
      timerId = setTimeout(() => {
        handleCloseRef.current();
      }, 1000);
    }
    return () => clearTimeout(timerId);
  }, [importSuccess]);

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && handleClose()}>
      <DialogContent className="gap-5 p-6 text-sm sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">
            Import new content from CSV
          </DialogTitle>
          <DialogDescription className="text-sm">
            Import new contents from a CSV file into AAQ.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2 text-muted-foreground">
          <p>The CSV file should have the following columns:</p>
          <ul className="flex list-disc flex-col gap-1 pl-5">
            <li>
              <code className="font-mono font-semibold text-foreground">
                title
              </code>
              : content title, up to 150 characters
            </li>
            <li>
              <code className="font-mono font-semibold text-foreground">
                text
              </code>
              : content text, up to 2000 characters
            </li>
            <li>
              (Optional){" "}
              <code className="font-mono font-semibold text-foreground">
                tags
              </code>
              : content tags, e.g. &quot;tag1, tag2, tag3&quot;
            </li>
          </ul>
          <p>Duplicate titles or texts will be rejected.</p>
        </div>

        <div className="flex items-center gap-3">
          <input
            ref={fileInputRef}
            id="choose-file"
            type="file"
            accept=".csv"
            hidden
            onChange={handleFileChange}
          />
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
          >
            <IconFileUpload data-icon="inline-start" />
            Attach file
          </Button>
          <span className="min-w-0 truncate text-muted-foreground">
            {selectedFile ? selectedFile.name : "No file selected"}
          </span>
        </div>

        {importErrorMessages.map((error, index) => (
          <Alert key={index} variant="destructive">
            <IconAlertCircle />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ))}
        {importSuccess && (
          <Alert>
            <IconCircleCheck />
            <AlertDescription>File uploaded successfully!</AlertDescription>
          </Alert>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            disabled={!selectedFile || loading}
            autoFocus
            onClick={handleImportClick}
          >
            {loading && <Spinner data-icon="inline-start" />}
            {importSuccess ? "Imported" : "Check and import"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export { ImportFromCSVModal };
