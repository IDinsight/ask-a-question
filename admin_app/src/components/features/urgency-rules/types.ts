/** One urgency rule as the backend returns it. */
export interface UrgencyRule {
  /** null for a rule that is only on screen and hasn't been saved yet. */
  urgency_rule_id: number | null;
  urgency_rule_text: string;
  /** Empty until the backend has saved the rule (the row then shows "Saving…"). */
  updated_datetime_utc: string;
  created_datetime_utc: string;
}

/** Response of POST /urgency-detect (the test panel). */
export interface UrgencyDetectionResponse {
  is_urgent: boolean;
  matched_rules?: string[];
  [key: string]: unknown;
}
