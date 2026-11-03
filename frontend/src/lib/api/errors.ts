// Turn FastAPI error bodies into messages people can read.
// FastAPI sends {"detail": "text"} for most errors and
// {"detail": [{"loc": [...], "msg": "..."}]} for validation errors (422).

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function clean(message: string): string {
  return message.replace(/^Value error, /, "");
}

/** The main message from an API error body, or a fallback. */
export function errorMessage(error: unknown, fallback: string): string {
  if (!isRecord(error)) return fallback;
  const { detail } = error;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && isRecord(detail[0]) && typeof detail[0].msg === "string") {
    return clean(detail[0].msg);
  }
  return fallback;
}

/** Per-field messages from a 422 validation error, keyed by field name. */
export function fieldErrors(error: unknown): Record<string, string> {
  const result: Record<string, string> = {};
  if (!isRecord(error) || !Array.isArray(error.detail)) return result;
  for (const issue of error.detail) {
    if (!isRecord(issue) || !Array.isArray(issue.loc) || typeof issue.msg !== "string") continue;
    const field = issue.loc[issue.loc.length - 1];
    if (typeof field === "string" && !(field in result)) result[field] = clean(issue.msg);
  }
  return result;
}

/** An API call that failed, with a readable message, the HTTP status and per-field errors. */
export class ApiRequestError extends Error {
  readonly status: number;
  readonly fieldErrors: Record<string, string>;

  constructor(message: string, status: number, fields: Record<string, string> = {}) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.fieldErrors = fields;
  }
}

export function toApiError(error: unknown, response: Response, fallback: string): ApiRequestError {
  return new ApiRequestError(errorMessage(error, fallback), response.status, fieldErrors(error));
}
