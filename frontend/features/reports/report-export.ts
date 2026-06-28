type DownloadAnchor = {
  href: string;
  download: string;
  click: () => void;
  remove?: () => void;
  rel?: string;
};

type ExportDeps = {
  createObjectUrl?: (blob: Blob) => string;
  revokeObjectUrl?: (url: string) => void;
  createAnchor?: () => DownloadAnchor | null;
};

const resolveExportDeps = (deps?: ExportDeps) => {
  const createObjectUrl =
    deps?.createObjectUrl ?? ((blob: Blob) => URL.createObjectURL(blob));
  const revokeObjectUrl =
    deps?.revokeObjectUrl ?? ((url: string) => URL.revokeObjectURL(url));
  const createAnchor =
    deps?.createAnchor ??
    (() => {
      if (typeof document === "undefined") {
        return null;
      }
      return document.createElement("a");
    });

  return { createObjectUrl, revokeObjectUrl, createAnchor };
};

const triggerDownload = (
  blob: Blob,
  filename: string,
  deps?: ExportDeps
) => {
  const { createObjectUrl, revokeObjectUrl, createAnchor } =
    resolveExportDeps(deps);
  const anchor = createAnchor();
  if (!anchor) {
    return;
  }

  const url = createObjectUrl(blob);
  anchor.href = url;
  anchor.download = filename;
  anchor.rel = "noopener";
  anchor.click();
  anchor.remove?.();
  revokeObjectUrl(url);
};

const sanitizeFilename = (value: string): string => {
  const trimmed = value.trim();
  if (!trimmed) {
    return "project";
  }
  return trimmed.replace(/[^a-zA-Z0-9-_]+/g, "_");
};

export const buildReportFilename = (
  projectId: string,
  extension: "json" | "md",
  now: Date = new Date()
): string => {
  const safeProjectId = sanitizeFilename(projectId);
  const stamp = now.toISOString().slice(0, 10);
  return `ideasense-report_${safeProjectId}_${stamp}.${extension}`;
};

export const exportJson = (
  report: unknown,
  filename: string,
  deps?: ExportDeps
) => {
  const blob = new Blob([JSON.stringify(report, null, 2)], {
    type: "application/json",
  });
  triggerDownload(blob, filename, deps);
};

export const exportMarkdown = (
  markdown: string,
  filename: string,
  deps?: ExportDeps
) => {
  const blob = new Blob([markdown], { type: "text/markdown" });
  triggerDownload(blob, filename, deps);
};
