import type { ProjectSummary, ProjectsArchivedFilter, ProjectsSortField, ProjectsSortOrder } from "./projects";

export const LOADING_PLACEHOLDERS = [0, 1, 2];
export const STAGE_ORDER = ["problem", "market", "tech", "report"];
export const ARCHIVED_FILTERS: ProjectsArchivedFilter[] = [
  "active",
  "archived",
  "all",
];
export const SORT_FIELDS: ProjectsSortField[] = ["updated_at", "created_at", "title"];
export const SORT_ORDERS: ProjectsSortOrder[] = ["desc", "asc"];
export const DEFAULT_ARCHIVED_FILTER: ProjectsArchivedFilter = "active";
export const DEFAULT_SORT_FIELD: ProjectsSortField = "updated_at";
export const DEFAULT_SORT_ORDER: ProjectsSortOrder = "desc";
export const ORG_SELECTION_SESSION_KEY = "ideasense.org.selection.done";

const escapeRegExp = (value: string): string =>
  value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

export const interpolate = (
  template: string,
  values: Record<string, string | number>
): string =>
  Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template
  );

export const highlightText = (text: string, query: string) => {
  const trimmed = query.trim();
  if (!trimmed) {
    return text;
  }
  const regex = new RegExp(`(${escapeRegExp(trimmed)})`, "ig");
  const lowered = trimmed.toLowerCase();
  return text.split(regex).map((part, index) =>
    part.toLowerCase() === lowered ? (
      <mark key={`${part}-${index}`} className="project-highlight">
        {part}
      </mark>
    ) : (
      part
    )
  );
};

export const formatOrgRoleLabel = (
  role: string | null | undefined,
  memberFallback: string
) => {
  if (!role) {
    return memberFallback;
  }
  return role.charAt(0).toUpperCase() + role.slice(1);
};

export const filterProjects = (projects: ProjectSummary[], query: string) => {
  const trimmed = query.trim().toLowerCase();
  if (!trimmed) {
    return projects;
  }

  return projects.filter((project) => {
    const haystack = [project.title, project.description, project.stage.label]
      .join(" ")
      .toLowerCase();
    return haystack.includes(trimmed);
  });
};
