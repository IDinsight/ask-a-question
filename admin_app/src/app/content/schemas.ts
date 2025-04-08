export interface DocIndexingTask {
  error_trace: string;
  finished_datetime_utc: string;
  upload_id: string;
  user_id: number;
  workspace_id: number;
  parent_file_name: string;
  created_datetime_utc: string;
  task_id: string;
  doc_name: string;
  task_status: string;
}

export interface DocIndexingStatusRow {
  fileName: string;
  status: "Ongoing" | "Done" | "Error";
  docsIndexed: string;
  errorTrace: string;
  created_at: string;
  finished_at: string;
  tasks: DocIndexingTask[];
}

export interface ContentBody {
  content_title: string;
  content_text: string;
  content_metadata: Record<string, unknown>;
}
export type IndexingStatusResponse = boolean | { detail: string };
