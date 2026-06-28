export const AUTH_UNAUTHORIZED_EVENT = "auth:unauthorized";
export const ORG_CONTEXT_INVALID_EVENT = "org:invalid-context";

export class ApiError extends Error {
  status: number;
  url?: string;
  data?: unknown;

  constructor({
    status,
    message,
    url,
    data,
  }: {
    status: number;
    message: string;
    url?: string;
    data?: unknown;
  }) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.url = url;
    this.data = data;
  }
}

type TokenStore = {
  getToken: () => string | null;
  setToken: (token: string, options?: { persist?: boolean }) => void;
  setTokenPreservingPersistence?: (token: string) => void;
  clearToken: () => void;
};

type OrgStore = {
  getOrgId: () => string | null;
  clearOrgId: () => void;
};

type ApiClientOptions = {
  baseUrl?: string;
  fetch?: typeof fetch;
  tokenStore?: TokenStore;
  onUnauthorized?: (error: ApiError) => void;
  orgStore?: OrgStore;
  onOrgContextInvalid?: (error: ApiError) => void;
};

type ApiClient = {
  fetchJson: <T>(path: string, init?: RequestInit) => Promise<T>;
  postJson: <T>(path: string, body: unknown, init?: RequestInit) => Promise<T>;
};

const API_BASE_PATH = "/api/v1";

const normalizeBaseUrl = (value: string): string => {
  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }
  return trimmed.endsWith("/") ? trimmed.slice(0, -1) : trimmed;
};

export const getApiBaseUrl = (): string =>
  normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL ?? "");

const normalizeApiPath = (path: string): string => {
  const trimmedPath = path.trim();
  const normalizedPath = trimmedPath.startsWith("/")
    ? trimmedPath
    : `/${trimmedPath}`;
  if (!normalizedPath || normalizedPath === "/") {
    return API_BASE_PATH;
  }
  if (
    normalizedPath === API_BASE_PATH ||
    normalizedPath.startsWith(`${API_BASE_PATH}/`)
  ) {
    return normalizedPath;
  }
  return `${API_BASE_PATH}${normalizedPath}`;
};

export const buildApiUrl = (
  path: string,
  baseUrl: string = getApiBaseUrl()
): string => {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }

  const normalizedPath = normalizeApiPath(path);
  const normalizedBase = normalizeBaseUrl(baseUrl);
  if (!normalizedBase) {
    return normalizedPath;
  }

  if (
    normalizedBase.endsWith(API_BASE_PATH) &&
    normalizedPath.startsWith(API_BASE_PATH)
  ) {
    return `${normalizedBase}${normalizedPath.slice(API_BASE_PATH.length)}`;
  }

  return `${normalizedBase}${normalizedPath}`;
};

export const emitUnauthorizedEvent = (
  error?: Error | ApiError | null
): void => {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(
    new CustomEvent(AUTH_UNAUTHORIZED_EVENT, { detail: { error } })
  );
};

const emitUnauthorized = (error: ApiError) => {
  emitUnauthorizedEvent(error);
};

export const emitOrgContextInvalidEvent = (
  error?: Error | ApiError | null
): void => {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(
    new CustomEvent(ORG_CONTEXT_INVALID_EVENT, { detail: { error } })
  );
};

const emitOrgContextInvalid = (error: ApiError) => {
  emitOrgContextInvalidEvent(error);
};

const getErrorMessage = (data: unknown, fallback: string): string => {
  if (typeof data === "string" && data.trim()) {
    return data;
  }
  if (data && typeof data === "object") {
    if ("detail" in data && typeof data.detail === "string") {
      return data.detail;
    }
    if ("message" in data && typeof data.message === "string") {
      return data.message;
    }
  }
  return fallback || "Request failed";
};

const parseResponseBody = async (response: Response): Promise<unknown> => {
  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    const text = await response.text().catch(() => "");
    return text || null;
  }

  return response.json().catch(() => null);
};

let cachedTokenStore: Promise<TokenStore> | null = null;
let cachedOrgStore: Promise<OrgStore> | null = null;

const resolveTokenStore = async (): Promise<TokenStore> => {
  if (!cachedTokenStore) {
    cachedTokenStore = import("../storage/token").then(
      (module) => module.tokenStorage
    );
  }
  return cachedTokenStore;
};

const resolveOrgStore = async (): Promise<OrgStore> => {
  if (!cachedOrgStore) {
    cachedOrgStore = import("../storage/org").then(
      (module) => module.orgStorage
    );
  }
  return cachedOrgStore;
};

const ORG_CONTEXT_ERROR_MESSAGES = new Set([
  "Invalid organization context",
  "Organization access denied",
]);

const isOrgContextError = (error: ApiError): boolean =>
  error.status === 403 && ORG_CONTEXT_ERROR_MESSAGES.has(error.message);

export function createApiClient(options: ApiClientOptions = {}): ApiClient {
  const {
    baseUrl,
    fetch: fetcher = fetch,
    tokenStore,
    onUnauthorized,
    orgStore,
    onOrgContextInvalid,
  } = options;

  const resolvedBaseUrl = normalizeBaseUrl(baseUrl ?? getApiBaseUrl());
  const handleUnauthorized = onUnauthorized ?? emitUnauthorized;
  const handleOrgContextInvalid =
    onOrgContextInvalid ?? emitOrgContextInvalid;

  const fetchJson = async <T>(
    path: string,
    init: RequestInit = {}
  ): Promise<T> => {
    const resolvedTokenStore = tokenStore ?? (await resolveTokenStore());
    const resolvedOrgStore = orgStore ?? (await resolveOrgStore());
    const headers = new Headers(init.headers);
    const token = resolvedTokenStore.getToken();

    if (token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    const orgId = resolvedOrgStore.getOrgId();
    const orgHeaderApplied = Boolean(orgId) && !headers.has("X-Org-ID");
    if (orgHeaderApplied) {
      headers.set("X-Org-ID", orgId!);
    }

    const url = buildApiUrl(path, resolvedBaseUrl);
    const executeRequest = async (requestHeaders: Headers) => {
      const response = await fetcher(url, { ...init, headers: requestHeaders });
      const data = await parseResponseBody(response);
      const refreshedToken = response.headers.get("x-auth-token");
      if (refreshedToken) {
        if (resolvedTokenStore.setTokenPreservingPersistence) {
          resolvedTokenStore.setTokenPreservingPersistence(refreshedToken);
        } else {
          resolvedTokenStore.setToken(refreshedToken);
        }
      }
      return { response, data };
    };

    const { response, data } = await executeRequest(headers);

    if (!response.ok) {
      const error = new ApiError({
        status: response.status,
        message: getErrorMessage(data, response.statusText),
        url,
        data,
      });

      if (response.status === 401) {
        resolvedTokenStore.clearToken();
        handleUnauthorized(error);
      }
      if (response.status === 403 && isOrgContextError(error)) {
        resolvedOrgStore.clearOrgId();
        if (orgHeaderApplied) {
          const retryHeaders = new Headers(headers);
          retryHeaders.delete("X-Org-ID");
          const retry = await executeRequest(retryHeaders);
          if (retry.response.ok) {
            return retry.data as T;
          }
          const retryError = new ApiError({
            status: retry.response.status,
            message: getErrorMessage(
              retry.data,
              retry.response.statusText
            ),
            url,
            data: retry.data,
          });
          if (retry.response.status === 401) {
            resolvedTokenStore.clearToken();
            handleUnauthorized(retryError);
          }
          if (
            retry.response.status === 403 &&
            isOrgContextError(retryError)
          ) {
            handleOrgContextInvalid(retryError);
          }
          throw retryError;
        }
        handleOrgContextInvalid(error);
      }

      throw error;
    }

    return data as T;
  };

  const postJson = async <T>(
    path: string,
    body: unknown,
    init: RequestInit = {}
  ): Promise<T> => {
    const headers = new Headers(init.headers);
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    return fetchJson<T>(path, {
      ...init,
      method: init.method ?? "POST",
      body: JSON.stringify(body),
      headers,
    });
  };

  return { fetchJson, postJson };
}

export const apiClient = createApiClient();
export type { ApiClient };
