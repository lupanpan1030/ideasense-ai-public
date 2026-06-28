import path from "node:path";

const API_BASE_PATH = "/api/v1";
// Keep Next/Turbopack resolution within the frontend package.
// The repo root doesn't have a package.json or node_modules, which breaks
// resolving dev deps like tailwindcss.
const PROJECT_ROOT = path.resolve(__dirname);

const normalizeBaseUrl = (value: string | undefined): string => {
  if (!value) {
    return "";
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }
  return trimmed.endsWith("/") ? trimmed.slice(0, -1) : trimmed;
};

const resolveBackendBaseUrl = (): string => {
  const publicBaseUrl = normalizeBaseUrl(
    process.env.NEXT_PUBLIC_API_BASE_URL
  );
  if (publicBaseUrl) {
    return publicBaseUrl;
  }
  return normalizeBaseUrl(process.env.BACKEND_INTERNAL_URL);
};

const buildRewriteDestination = (baseUrl: string): string => {
  if (!baseUrl) {
    return "";
  }
  if (baseUrl.endsWith(API_BASE_PATH)) {
    return `${baseUrl}/:path*`;
  }
  return `${baseUrl}${API_BASE_PATH}/:path*`;
};

const nextConfig = {
  outputFileTracingRoot: PROJECT_ROOT,
  turbopack: {
    root: PROJECT_ROOT,
  },
  async rewrites() {
    const baseUrl = resolveBackendBaseUrl();
    if (!baseUrl) {
      return [];
    }
    return [
      {
        source: `${API_BASE_PATH}/:path*`,
        destination: buildRewriteDestination(baseUrl),
      },
    ];
  },
};

export default nextConfig;
