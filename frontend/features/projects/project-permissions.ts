import { apiClient } from "@/lib/api/client";
import { normalizeProjectId } from "@/features/projects/project-id";

export type ProjectPermissions = {
  can_view_project: boolean;
  can_view_messages: boolean;
  can_view_facts: boolean;
  can_comment: boolean;
};

const normalizePermissions = (payload: unknown): ProjectPermissions | null => {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const record = payload as Record<string, unknown>;
  return {
    can_view_project: Boolean(record.can_view_project),
    can_view_messages: Boolean(record.can_view_messages),
    can_view_facts: Boolean(record.can_view_facts),
    can_comment: Boolean(record.can_comment),
  };
};

export async function fetchProjectPermissions(
  projectId: string,
  options: { signal?: AbortSignal } = {}
): Promise<ProjectPermissions> {
  const normalizedProjectId = normalizeProjectId(projectId);
  if (!normalizedProjectId) {
    throw new Error("Invalid project id.");
  }

  const response = await apiClient.fetchJson<unknown>(
    `/projects/${normalizedProjectId}/permissions`,
    { signal: options.signal }
  );
  const normalized = normalizePermissions(response);
  if (!normalized) {
    throw new Error("Invalid permissions payload.");
  }
  return normalized;
}
