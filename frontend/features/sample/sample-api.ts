import { cache } from "react";
import { buildApiUrl } from "@/lib/api/client";
import {
  normalizeProjectsListResponse,
  type ProjectsListResult,
  type ProjectSummary,
} from "@/features/projects/projects";
import {
  normalizeChatRole,
  type ChatMessage,
} from "@/features/chat/chat-state";
import {
  normalizeReportResponse,
  type ReportSnapshot,
} from "@/features/reports/reports-normalize";

const SAMPLE_REVALIDATE_SECONDS = 300;

class SampleApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "SampleApiError";
    this.status = status;
  }
}

const getSampleRequestErrorMessage = (status: number): string => {
  if (status === 404) {
    return "Sample resource not found.";
  }
  if (status >= 500) {
    return "Sample service is unavailable.";
  }
  return "Sample request failed.";
};

const resolveBaseUrl = (): string => {
  const envValue =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.BACKEND_INTERNAL_URL ?? "";
  const trimmed = envValue.trim();
  return trimmed.endsWith("/") ? trimmed.slice(0, -1) : trimmed;
};

const resolveServerOrigin = async (): Promise<string> => {
  if (typeof window !== "undefined") {
    return "";
  }
  try {
    const headersModule = await import("next/headers");
    const headerList = await headersModule.headers();
    const forwardedHost = headerList.get("x-forwarded-host");
    const host = forwardedHost ?? headerList.get("host");
    if (!host) {
      return "";
    }
    const proto = headerList.get("x-forwarded-proto") ?? "http";
    return `${proto}://${host}`;
  } catch {
    return "";
  }
};

const fetchSampleJson = async (
  path: string,
  init: RequestInit = {}
): Promise<unknown> => {
  let baseUrl = resolveBaseUrl();
  if (!baseUrl) {
    baseUrl = await resolveServerOrigin();
  }
  const url = buildApiUrl(path, baseUrl);
  const response = await fetch(url, {
    ...init,
    headers: init.headers,
    // Public sample pages: cache real sample data so a backend blip serves the
    // last good snapshot instead of an empty page (resilience via cached real
    // data, never fabricated content).
    next: { revalidate: SAMPLE_REVALIDATE_SECONDS },
  });

  if (!response.ok) {
    throw new SampleApiError(
      response.status,
      getSampleRequestErrorMessage(response.status)
    );
  }

  return response.json();
};

export async function fetchSampleProjects(
  options: { stage?: string; limit?: number; offset?: number } = {}
): Promise<ProjectsListResult> {
  const params = new URLSearchParams();
  if (options.stage) {
    params.set("stage", options.stage);
  }
  if (typeof options.limit === "number") {
    params.set("limit", String(options.limit));
  }
  if (typeof options.offset === "number") {
    params.set("offset", String(options.offset));
  }
  const query = params.toString();
  const path = query ? `/sample/projects?${query}` : "/sample/projects";
  const response = await fetchSampleJson(path);
  const normalized = normalizeProjectsListResponse(response);
  if (!normalized) {
    throw new Error("Invalid sample projects payload.");
  }
  return normalized;
}

type SampleConversationMessage = {
  id?: unknown;
  role?: unknown;
  content?: unknown;
  created_at?: unknown;
  stage?: unknown;
  meta?: unknown;
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

const normalizeStageValue = (value: unknown): string | null => {
  const trimmed = toTrimmedString(value);
  return trimmed ? trimmed.toLowerCase() : null;
};

const resolveMessageId = (value: unknown, fallbackIndex: number): string => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return `sample-${value}`;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed) {
      return trimmed;
    }
  }
  return `sample-${fallbackIndex}`;
};

const normalizeSampleMessage = (
  payload: unknown,
  index: number
): ChatMessage | null => {
  if (!isRecord(payload)) {
    return null;
  }
  const response = payload as SampleConversationMessage;
  const role = normalizeChatRole(response.role);
  if (!role) {
    return null;
  }
  const content = typeof response.content === "string" ? response.content : "";
  const createdAt = toTrimmedString(response.created_at);
  const stage = normalizeStageValue(response.stage);
  const meta = isRecord(response.meta) ? response.meta : null;

  return {
    id: resolveMessageId(response.id, index),
    role,
    content,
    createdAt,
    stage,
    meta,
    status: "complete",
  };
};

export async function fetchSampleChatMessages(
  sampleId: string
): Promise<ChatMessage[]> {
  const response = await fetchSampleJson(`/sample/projects/${sampleId}/chat`);
  if (!isRecord(response) || !Array.isArray(response.messages)) {
    throw new Error("Invalid sample chat payload.");
  }
  return response.messages
    .map((item, index) => normalizeSampleMessage(item, index))
    .filter((item): item is ChatMessage => Boolean(item));
}

export async function fetchSampleReport(
  sampleId: string
): Promise<ReportSnapshot | null> {
  try {
    const response = await fetchSampleJson(
      `/sample/projects/${sampleId}/report`
    );
    const normalized = normalizeReportResponse(response, sampleId);
    if (!normalized) {
      throw new Error("Invalid sample report payload.");
    }
    return normalized;
  } catch (error) {
    if (error instanceof SampleApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

/**
 * Request-scoped sample project list. The sample layout (sidebar) and the
 * `/sample` list page both need this; `cache()` dedupes them into one fetch per
 * request so they cannot split-brain across data states. On any failure it
 * returns an empty list so callers render an explicit empty state rather than
 * fabricated fallback content.
 */
export const getSampleProjectsCached = cache(
  async (): Promise<ProjectSummary[]> => {
    try {
      const result = await fetchSampleProjects();
      return result.projects;
    } catch {
      return [];
    }
  }
);

/**
 * The featured sample report for the standalone `/sample-report` page: the first
 * report-stage sample, rendered from real DB data. Returns null when no report
 * sample is available.
 */
export async function getFeaturedSampleReport(): Promise<ReportSnapshot | null> {
  const projects = await getSampleProjectsCached();
  const featured =
    projects.find((project) => project.stage.value === "report") ?? null;
  if (!featured) {
    return null;
  }
  return fetchSampleReport(featured.id);
}
