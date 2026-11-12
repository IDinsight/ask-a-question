export interface ContentDisplay {
  title: string;
  text: string;
  content_id: number;
  display_number: number;
  last_modified: string;
  tags: Tag[];
  positive_votes: number;
  negative_votes: number;
  related_contents: Content[];
}

export interface Content extends EditContentBody {
  content_id: number | null;
  display_number: number;
  positive_votes: number;
  negative_votes: number;
  created_datetime_utc: string;
  updated_datetime_utc: string;
}

export interface EditContentBody {
  content_title: string;
  content_text: string;
  content_tags: number[];
  related_contents_id: number[];
  content_metadata: Record<string, unknown>;
}
export interface Tag {
  tag_id: number;
  tag_name: string;
}

/** Body for creating or editing a content card. */
export interface ContentBody {
  content_title: string;
  content_text: string;
  content_metadata: Record<string, unknown>;
}

/** Is a PDF indexing (docmuncher) job running? `{detail}` when the feature is off. */
export type IndexingStatusResponse = boolean | { detail: string };

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

/** One row of the "PDF upload status" dialog. */
export interface DocIndexingStatusRow {
  fileName: string;
  status: "Ongoing" | "Done" | "Error";
  docsIndexed: string;
  errorTrace: string;
  created_at: string;
  finished_at: string;
  tasks: DocIndexingTask[];
}

export interface DocumentUploadResponse {
  status: number;
  detail: any;
}
