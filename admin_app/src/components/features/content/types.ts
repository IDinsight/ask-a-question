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
