import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { AppMessages } from "@/lib/i18n/messages";
import type { ReportJobStatusValue } from "./reports-normalize";

type ReportViewerMessages = AppMessages["reportViewer"];

export function resolveReportJobStatusCopy(
  status: ReportJobStatusValue | null,
  messages: ReportViewerMessages
) {
  const labels = messages.reportStatus.statuses;
  switch (status) {
    case "ready":
      return {
        badge: labels.ready,
        title: messages.reportStatus.readyTitle,
        description: messages.reportStatus.readyDescription,
        variant: "success" as const,
      };
    case "running":
      return {
        badge: labels.running,
        title: messages.reportStatus.runningTitle,
        description: messages.reportStatus.runningDescription,
        variant: "info" as const,
      };
    case "finalizing":
      return {
        badge: labels.finalizing,
        title: messages.reportStatus.finalizingTitle,
        description: messages.reportStatus.finalizingDescription,
        variant: "info" as const,
      };
    case "failed":
      return {
        badge: labels.failed,
        title: messages.reportStatus.failedTitle,
        description: messages.reportStatus.failedDescription,
        variant: "danger" as const,
      };
    case "stale":
      return {
        badge: labels.stale,
        title: messages.reportStatus.staleTitle,
        description: messages.reportStatus.staleDescription,
        variant: "warning" as const,
      };
    case "not_started":
      return {
        badge: labels.not_started,
        title: messages.reportStatus.notStartedTitle,
        description: messages.reportStatus.notStartedDescription,
        variant: "secondary" as const,
      };
    case "queued":
    default:
      return {
        badge: labels.queued,
        title: messages.reportStatus.queuedTitle,
        description: messages.reportStatus.queuedDescription,
        variant: "info" as const,
      };
  }
}

type ReportJobStatusCardProps = {
  errorMessage: string | null;
  isLoading: boolean;
  isStarting: boolean;
  messages: ReportViewerMessages;
  onRetry: () => void;
  retryable: boolean;
  status: ReportJobStatusValue | null;
};

export function ReportJobStatusCard({
  status,
  errorMessage,
  retryable,
  isStarting,
  isLoading,
  onRetry,
  messages,
}: ReportJobStatusCardProps) {
  const copy = resolveReportJobStatusCopy(status, messages);
  const canRetry =
    retryable &&
    (status === "failed" || status === "stale" || status === "not_started");
  const description =
    errorMessage ??
    (!canRetry &&
    (status === "failed" || status === "stale" || status === "not_started")
      ? messages.reportStatus.notRetryableDescription
      : copy.description);

  return (
    <Card variant={errorMessage || status === "failed" ? "alert" : "soft"}>
      <CardHeader className="workspace-panel__header">
        <div className="stack-sm">
          <CardTitle>{copy.title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </div>
        <Badge variant={copy.variant}>
          {isStarting || isLoading
            ? messages.reportStatus.statuses.queued
            : copy.badge}
        </Badge>
      </CardHeader>
      {canRetry ? (
        <CardContent>
          <Button
            type="button"
            onClick={onRetry}
            disabled={isStarting || isLoading}
          >
            {isStarting
              ? messages.reportStatus.actions.starting
              : messages.reportStatus.actions.retry}
          </Button>
        </CardContent>
      ) : null}
    </Card>
  );
}
