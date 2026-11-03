import { API_ORIGIN } from "../config";
import { authFetch } from "./auth-fetch";
import { toApiError } from "./errors";

/** The file name from a Content-Disposition header, if it has a plain one. */
export function filenameFromDisposition(header: string | null): string | null {
  const match = header?.match(/filename="([^"/\\]+)"/);
  return match ? match[1] : null;
}

/**
 * Download a file from the API and hand it to the browser as a download.
 *
 * Downloads need the access token, which a plain <a href> cannot send, so the file is
 * fetched with authFetch (token attached, refreshed once on 401) and saved from memory.
 */
export async function downloadFromApi(
  path: string,
  query: Record<string, string | undefined>,
  fallbackName: string,
): Promise<void> {
  const url = new URL(path, API_ORIGIN);
  for (const [name, value] of Object.entries(query)) {
    if (value) url.searchParams.set(name, value);
  }

  const response = await authFetch(new Request(url, { credentials: "include" }));
  if (!response.ok) {
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      body = undefined;
    }
    throw toApiError(body, response, "Could not download the file.");
  }

  const blobUrl = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download =
    filenameFromDisposition(response.headers.get("Content-Disposition")) ?? fallbackName;
  document.body.append(link);
  link.click();
  link.remove();
  // Give the browser a moment to start the download before releasing the memory.
  setTimeout(() => URL.revokeObjectURL(blobUrl), 10_000);
}
