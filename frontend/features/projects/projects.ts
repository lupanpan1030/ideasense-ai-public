import { normalizeProjectId } from "./project-id";
import { getSafeErrorMessage } from "@/lib/api/safe-error-message";
import { normalizeAppLocale, type AppLocale } from "@/lib/i18n/config";

type ProjectStageVariant = "default" | "success" | "warning" | "danger" | "info";

type ProjectStage = {
  value: string;
  label: string;
  variant: ProjectStageVariant;
};

export type ProjectsArchivedFilter = "active" | "archived" | "all";
export type ProjectsSortField = "updated_at" | "created_at" | "title";
export type ProjectsSortOrder = "asc" | "desc";

export type ProjectSummary = {
  id: string;
  title: string;
  description: string;
  stage: ProjectStage;
  isArchived: boolean;
  createdAt: string | null;
  createdAtLabel: string;
  updatedAt: string | null;
  updatedAtLabel: string;
};

export type ProjectRuntimeSnapshot = {
  projectId: string;
  orgId: string;
  stage: string;
  variant: string;
  currentQuestionId: string | null;
  nextQuestionId: string | null;
  missingPaths: string[];
  turnState: string;
  runtimeVersion: number;
  createdAt: string | null;
  updatedAt: string | null;
};

export type ProjectQuestionInstanceSnapshot = {
  id: string;
  questionBankQuestionId: string;
  status: string;
  askedCount: number;
  createdAt: string | null;
  updatedAt: string | null;
};

export type ProjectCreateResult = {
  project: ProjectSummary;
  runtime: ProjectRuntimeSnapshot;
  questionInstance: ProjectQuestionInstanceSnapshot;
};

export type ProjectsListResult = {
  projects: ProjectSummary[];
  total: number;
  limit: number;
  offset: number;
};

type ProjectListItem = {
  id?: string | null;
  title?: string | null;
  description?: string | null;
  current_stage?: string | null;
  is_archived?: boolean | null;
  created_at?: string | null;
  updated_at?: string | null;
};

type ProjectsResponse = {
  projects?: ProjectListItem[] | null;
  total?: unknown;
  limit?: unknown;
  offset?: unknown;
};

type ProjectEnvelope = {
  project?: ProjectListItem | null;
};

type ProjectRuntimeItem = {
  project_id?: unknown;
  org_id?: unknown;
  stage?: unknown;
  variant?: unknown;
  current_question_bank_question_id?: unknown;
  next_question_bank_question_id?: unknown;
  missing_paths?: unknown;
  turn_state?: unknown;
  runtime_version?: unknown;
  created_at?: unknown;
  updated_at?: unknown;
};

type ProjectQuestionInstanceItem = {
  id?: unknown;
  question_bank_question_id?: unknown;
  status?: unknown;
  asked_count?: unknown;
  created_at?: unknown;
  updated_at?: unknown;
};

type ProjectCreateResponse = {
  project?: ProjectListItem | null;
  runtime?: ProjectRuntimeItem | null;
  question_instance?: ProjectQuestionInstanceItem | null;
};

const DEFAULT_TITLE = "Untitled project";
const DEFAULT_DESCRIPTION = "No description yet.";
const DEFAULT_CREATED_LABEL = "Created unknown";
const DEFAULT_UPDATED_LABEL = "Updated unknown";

const STAGE_MAP: Record<string, ProjectStage> = {
  problem: { value: "problem", label: "Problem", variant: "info" },
  market: { value: "market", label: "Market", variant: "warning" },
  tech: { value: "tech", label: "Tech", variant: "success" },
  report: { value: "report", label: "Report", variant: "default" },
};

const UNKNOWN_STAGE: ProjectStage = {
  value: "unknown",
  label: "Unknown",
  variant: "warning",
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const toTrimmedString = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const toNumber = (value: unknown): number | null => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    const parsed = Number(trimmed);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
};

const toBoolean = (value: unknown): boolean | null => {
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "number") {
    if (value === 1) {
      return true;
    }
    if (value === 0) {
      return false;
    }
  }
  if (typeof value === "string") {
    const trimmed = value.trim().toLowerCase();
    if (trimmed === "true") {
      return true;
    }
    if (trimmed === "false") {
      return false;
    }
  }
  return null;
};

const toStringArray = (value: unknown): string[] => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean);
};

const resolveProjectStage = (value: unknown): ProjectStage => {
  const key = toTrimmedString(value)?.toLowerCase();
  if (key && STAGE_MAP[key]) {
    return STAGE_MAP[key];
  }
  return UNKNOWN_STAGE;
};

const formatCreatedAt = (
  value: unknown
): { iso: string | null; label: string } => {
  const raw = toTrimmedString(value);
  if (!raw) {
    return { iso: null, label: DEFAULT_CREATED_LABEL };
  }

  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) {
    return { iso: null, label: DEFAULT_CREATED_LABEL };
  }

  const formatted = new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);

  return {
    iso: date.toISOString(),
    label: `Created ${formatted}`,
  };
};

const formatUpdatedAt = (
  value: unknown
): { iso: string | null; label: string } => {
  const raw = toTrimmedString(value);
  if (!raw) {
    return { iso: null, label: DEFAULT_UPDATED_LABEL };
  }

  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) {
    return { iso: null, label: DEFAULT_UPDATED_LABEL };
  }

  const formatted = new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);

  return {
    iso: date.toISOString(),
    label: `Updated ${formatted}`,
  };
};

const normalizeProject = (value: unknown): ProjectSummary | null => {
  if (!isRecord(value)) {
    return null;
  }

  const id = normalizeProjectId(toTrimmedString(value.id));
  if (!id) {
    return null;
  }

  const title = toTrimmedString(value.title) ?? DEFAULT_TITLE;
  const description = toTrimmedString(value.description) ?? DEFAULT_DESCRIPTION;
  const stage = resolveProjectStage(value.current_stage);
  const isArchived = toBoolean(value.is_archived) ?? false;
  const { iso: createdIso, label: createdLabel } = formatCreatedAt(
    value.created_at
  );
  const { iso, label } = formatUpdatedAt(value.updated_at);

  return {
    id,
    title,
    description,
    stage,
    isArchived,
    createdAt: createdIso,
    createdAtLabel: createdLabel,
    updatedAt: iso,
    updatedAtLabel: label,
  };
};

const normalizeProjectEnvelope = (payload: unknown): ProjectSummary | null => {
  if (!isRecord(payload)) {
    return null;
  }

  const project = (payload as ProjectEnvelope).project;
  return normalizeProject(project);
};

export const normalizeProjectsResponse = (payload: unknown): ProjectSummary[] => {
  if (!isRecord(payload)) {
    return [];
  }

  const projects = (payload as ProjectsResponse).projects;
  if (!Array.isArray(projects)) {
    return [];
  }

  return projects
    .map((project) => normalizeProject(project))
    .filter((project): project is ProjectSummary => Boolean(project));
};

export const normalizeProjectsListResponse = (
  payload: unknown
): ProjectsListResult | null => {
  if (!isRecord(payload)) {
    return null;
  }
  const projects = normalizeProjectsResponse(payload);
  const total = toNumber((payload as ProjectsResponse).total);
  const limit = toNumber((payload as ProjectsResponse).limit);
  const offset = toNumber((payload as ProjectsResponse).offset);
  if (total === null || limit === null || offset === null) {
    return null;
  }
  return { projects, total, limit, offset };
};

const normalizeProjectRuntime = (
  payload: unknown
): ProjectRuntimeSnapshot | null => {
  if (!isRecord(payload)) {
    return null;
  }

  const projectId = normalizeProjectId(toTrimmedString(payload.project_id));
  const orgId = toTrimmedString(payload.org_id);
  const stage = toTrimmedString(payload.stage);
  const variant = toTrimmedString(payload.variant);
  const currentQuestionId = toTrimmedString(
    payload.current_question_bank_question_id
  );
  const nextQuestionId = toTrimmedString(
    payload.next_question_bank_question_id
  );
  const missingPaths = toStringArray(payload.missing_paths);
  const turnState = toTrimmedString(payload.turn_state);
  const runtimeVersion = toNumber(payload.runtime_version);
  const createdAt = toTrimmedString(payload.created_at);
  const updatedAt = toTrimmedString(payload.updated_at);

  if (
    !projectId ||
    !orgId ||
    !stage ||
    !variant ||
    runtimeVersion === null ||
    !turnState
  ) {
    return null;
  }
  const isReportStage = stage.toLowerCase() === "report";
  if (!currentQuestionId && !isReportStage) {
    return null;
  }

  return {
    projectId,
    orgId,
    stage,
    variant,
    currentQuestionId: currentQuestionId ?? null,
    nextQuestionId: nextQuestionId ?? currentQuestionId ?? null,
    missingPaths,
    turnState,
    runtimeVersion,
    createdAt,
    updatedAt,
  };
};

const normalizeProjectQuestionInstance = (
  payload: unknown
): ProjectQuestionInstanceSnapshot | null => {
  if (!isRecord(payload)) {
    return null;
  }

  const id = toTrimmedString(payload.id);
  const questionBankQuestionId = toTrimmedString(
    payload.question_bank_question_id
  );
  const status = toTrimmedString(payload.status);
  const askedCount = toNumber(payload.asked_count);
  const createdAt = toTrimmedString(payload.created_at);
  const updatedAt = toTrimmedString(payload.updated_at);

  if (!id || !questionBankQuestionId || !status || askedCount === null) {
    return null;
  }

  return {
    id,
    questionBankQuestionId,
    status,
    askedCount,
    createdAt,
    updatedAt,
  };
};

export async function fetchProjects(
  options: {
    signal?: AbortSignal;
    offset?: number;
    limit?: number;
    stage?: string;
    archived?: ProjectsArchivedFilter;
    sort?: ProjectsSortField;
    order?: ProjectsSortOrder;
  } = {}
): Promise<ProjectsListResult> {
  const { apiClient } = await import("../../lib/api/client");
  const params = new URLSearchParams();
  if (typeof options.offset === "number") {
    params.set("offset", String(options.offset));
  }
  if (typeof options.limit === "number") {
    params.set("limit", String(options.limit));
  }
  if (options.stage) {
    params.set("stage", options.stage);
  }
  if (options.archived) {
    params.set("archived", options.archived);
  }
  if (options.sort) {
    params.set("sort", options.sort);
  }
  if (options.order) {
    params.set("order", options.order);
  }
  const query = params.toString();
  const path = query ? `/projects?${query}` : "/projects";

  const response = await apiClient.fetchJson<unknown>(path, {
    signal: options.signal,
  });

  const normalized = normalizeProjectsListResponse(response);
  if (!normalized) {
    throw new Error("Invalid projects payload.");
  }
  return normalized;
}

export async function createProject(payload: {
  title: string;
  description?: string | null;
  outputLocale?: AppLocale;
}): Promise<ProjectCreateResult> {
  const { apiClient } = await import("../../lib/api/client");
  const title = payload.title.trim();
  if (!title) {
    throw new Error("Project title is required.");
  }

  const description =
    typeof payload.description === "string" ? payload.description.trim() : "";

  const response = await apiClient.postJson<unknown>("/projects", {
    title,
    description: description ? description : undefined,
    output_locale: normalizeAppLocale(payload.outputLocale),
  });

  const normalizedProject = normalizeProjectEnvelope(response);
  const runtime = normalizeProjectRuntime(
    (response as ProjectCreateResponse).runtime
  );
  const questionInstance = normalizeProjectQuestionInstance(
    (response as ProjectCreateResponse).question_instance
  );
  if (!normalizedProject || !runtime || !questionInstance) {
    throw new Error("Invalid project payload.");
  }

  return {
    project: normalizedProject,
    runtime,
    questionInstance,
  };
}

export async function updateProject(
  projectId: string,
  payload: {
    title?: string | null;
    description?: string | null;
    isArchived?: boolean | null;
  }
): Promise<ProjectSummary> {
  const { apiClient } = await import("../../lib/api/client");
  const normalizedId = normalizeProjectId(projectId);
  if (!normalizedId) {
    throw new Error("Project ID is required.");
  }

  const body: Record<string, unknown> = {};
  if ("title" in payload) {
    body.title = payload.title;
  }
  if ("description" in payload) {
    body.description = payload.description;
  }
  if ("isArchived" in payload) {
    body.is_archived = payload.isArchived;
  }

  if (!Object.keys(body).length) {
    throw new Error("No project updates provided.");
  }

  const response = await apiClient.postJson<unknown>(
    `/projects/${normalizedId}`,
    body,
    { method: "PATCH" }
  );
  const normalizedProject = normalizeProjectEnvelope(response);
  if (!normalizedProject) {
    throw new Error("Invalid project payload.");
  }
  return normalizedProject;
}

export async function deleteProject(projectId: string): Promise<void> {
  const { apiClient } = await import("../../lib/api/client");
  const normalizedId = normalizeProjectId(projectId);
  if (!normalizedId) {
    throw new Error("Project ID is required.");
  }
  await apiClient.fetchJson(`/projects/${normalizedId}`, {
    method: "DELETE",
  });
}

export const getProjectsErrorMessage = (error: unknown): string => {
  return getSafeErrorMessage(error, {
    default: "Unable to load projects.",
    network: "Network error. Check your connection and try again.",
    notFound: "Project not found or it was deleted.",
    sessionExpired: "Your session expired. Please sign in again.",
    unavailable: "Projects service is unavailable. Please try again soon.",
  });
};

export const getProjectCreateErrorMessage = (error: unknown): string => {
  return getSafeErrorMessage(error, {
    default: "Unable to create project.",
    network: "Network error. Check your connection and try again.",
    sessionExpired: "Your session expired. Please sign in again.",
    unavailable: "Projects service is unavailable. Please try again soon.",
  });
};

const getProjectActionErrorMessage = (
  error: unknown,
  fallback: string
): string => {
  return getSafeErrorMessage(error, {
    default: fallback,
    network: "Network error. Check your connection and try again.",
    sessionExpired: "Your session expired. Please sign in again.",
    unavailable: "Projects service is unavailable. Please try again soon.",
  });
};

export const getProjectUpdateErrorMessage = (error: unknown): string =>
  getProjectActionErrorMessage(error, "Unable to update project.");

export const getProjectDeleteErrorMessage = (error: unknown): string =>
  getProjectActionErrorMessage(error, "Unable to delete project.");
