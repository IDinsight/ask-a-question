/**
 * Error contract shared by every API call in the admin app.
 *
 * The generated client (src/client) throws whatever body the server returned.
 * src/lib/api/interceptors.ts runs every failure through `toApiError`, so
 * callers always see one of two shapes, same as before the BFF refactor:
 *
 * - `CustomError` ({status, message}, a plain object) for 4xx: the backend
 *   rejected the request on purpose; `message` is safe to show the user.
 * - `Error` for 5xx, BFF 502/504 (an `ApiServerError`, with status and body)
 *   and network failures (a plain Error): something broke.
 *   QueryProvider retries these once and never retries a CustomError.
 */
export type CustomError = {
  status: number;
  message: string;
  /** The raw response body, for the few callers that show structured errors. */
  body?: unknown;
};

/** A 5xx (or BFF 502/504) response. Still an Error, so retries and checks work as before. */
export class ApiServerError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body: unknown,
  ) {
    super(message);
    this.name = "ApiServerError";
  }
}

export const isCustomError = (error: unknown): error is CustomError =>
  typeof error === "object" &&
  error !== null &&
  !(error instanceof Error) &&
  typeof (error as CustomError).status === "number" &&
  typeof (error as CustomError).message === "string";

/**
 * Pull a readable message out of an error body. FastAPI uses `{detail}`: a
 * string for HTTPException, or a list of `{msg}` objects for validation (422).
 */
export const extractErrorDetail = (body: unknown): string | undefined => {
  if (typeof body === "string") return body || undefined;
  if (typeof body !== "object" || body === null) return undefined;
  const { detail, message, error_message } = body as Record<string, unknown>;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item as { msg?: unknown })?.msg)
      .filter((msg): msg is string => typeof msg === "string");
    if (messages.length > 0) return messages.join("; ");
  }
  if (typeof message === "string") return message;
  if (typeof error_message === "string") return error_message;
  return undefined;
};

/**
 * Convert a failed call into the contract above.
 * @param body     what the server sent back (parsed JSON or text), or the thrown error
 * @param response the HTTP response; undefined when the request never got one
 */
export const toApiError = (
  body: unknown,
  response: Response | undefined,
): CustomError | Error => {
  if (!response) {
    // No response at all: offline, DNS, CORS, aborted...
    return body instanceof Error ? body : new Error("Could not reach the server");
  }
  const detail = extractErrorDetail(body);
  if (response.status >= 500) {
    return new ApiServerError(
      detail ?? `Server error (${response.status})`,
      response.status,
      body,
    );
  }
  return {
    status: response.status,
    message: detail ?? `Request failed (${response.status})`,
    body,
  };
};

/**
 * Message for the UI: the backend's explanation for a 4xx, otherwise
 * `fallback` (5xx/network messages are not meant for users).
 */
export const getErrorMessage = (error: unknown, fallback: string): string =>
  isCustomError(error) ? error.message : fallback;
