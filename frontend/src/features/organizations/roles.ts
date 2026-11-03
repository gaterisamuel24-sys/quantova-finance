import type { Organization } from "./api";

type OrgRole = Organization["my_role"];

// Mirrors the backend's role order. The server enforces permissions on every request;
// the frontend only uses this to hide buttons that would be refused anyway.
const RANK: Record<OrgRole, number> = { viewer: 0, analyst: 1, admin: 2, owner: 3 };

export function hasRoleAtLeast(role: OrgRole, minimum: OrgRole): boolean {
  return RANK[role] >= RANK[minimum];
}

/** Analysts and above can add, edit, delete and import transactions. */
export function canEditLedger(organization: Organization): boolean {
  return hasRoleAtLeast(organization.my_role, "analyst");
}
