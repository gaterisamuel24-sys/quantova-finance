const STORAGE_KEY = "quantova-last-organization";

/** Remember the last organization opened, so /app reopens it. A convenience only. */
export function rememberLastOrganization(organizationId: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, organizationId);
  } catch {
    // Storage unavailable: /app simply opens the first organization.
  }
}

export function lastOrganizationId(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}
