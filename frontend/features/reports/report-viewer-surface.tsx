"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button, buttonClassNames } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { ProjectVerificationSnapshot } from "@/features/assessments/api";
import type { AppLocale } from "@/lib/i18n/config";
import { buildLocalePath } from "@/lib/i18n/config";
import type { AppMessages } from "@/lib/i18n/messages";
import { ReportDocument } from "./report-document";
import { ReportJobStatusCard } from "./report-job-status-card";
import { ReportViewerSkeleton } from "./report-viewer-skeleton";
import type {
  ReportJobStatus,
  ReportSnapshot,
  ReportStageSummary,
} from "./reports-normalize";
import { SampleReportHero } from "./sample-report-hero";

type ReportLocaleMismatchNotice = {
  title: string;
  description: string;
} | null;

type ReportViewerSurfaceProps = {
  projectId: string;
  isSample: boolean;
  isZh: boolean;
  locale: AppLocale;
  messages: AppMessages["reportViewer"];
  subtitle: string;
  canViewMessages: boolean | null;
  report: ReportSnapshot | null;
  reportStatus: ReportJobStatus | null;
  activeReportStatus: ReportJobStatus["status"] | null;
  reportLocaleLabel: string | null;
  reportLocaleMismatch: ReportLocaleMismatchNotice;
  decisionBand: string | null;
  decisionVariant: "info" | "warning";
  totalScore: string;
  riskCount: number;
  overallSummary: string;
  currentStageLabel: string | null;
  stageSummaries: ReportStageSummary[];
  confirmedStages: number;
  isEmpty: boolean;
  isLoading: boolean;
  isRefreshing: boolean;
  isStatusLoading: boolean;
  isStartingReport: boolean;
  isReportJobPreparing: boolean;
  exportDisabled: boolean;
  refreshDisabled: boolean;
  errorMessage: string | null;
  statusErrorMessage: string | null;
  shouldShowReportJobStatus: boolean;
  isVerificationLoading: boolean;
  verificationError: string | null;
  verificationSnapshot: ProjectVerificationSnapshot | null;
  interpolate: (template: string, values: Record<string, string | number>) => string;
  onRefresh: () => void;
  onRetryLoad: () => void;
  onRetryRefresh: () => void;
  onStartReport: () => void;
  onPrint: () => void;
  onExportJson: () => void;
  onExportMarkdown: () => void;
};

export function ReportViewerSurface({
  projectId,
  isSample,
  isZh,
  locale,
  messages,
  subtitle,
  canViewMessages,
  report,
  reportStatus,
  activeReportStatus,
  reportLocaleLabel,
  reportLocaleMismatch,
  decisionBand,
  decisionVariant,
  totalScore,
  riskCount,
  overallSummary,
  currentStageLabel,
  stageSummaries,
  confirmedStages,
  isEmpty,
  isLoading,
  isRefreshing,
  isStatusLoading,
  isStartingReport,
  isReportJobPreparing,
  exportDisabled,
  refreshDisabled,
  errorMessage,
  statusErrorMessage,
  shouldShowReportJobStatus,
  isVerificationLoading,
  verificationError,
  verificationSnapshot,
  interpolate,
  onRefresh,
  onRetryLoad,
  onRetryRefresh,
  onStartReport,
  onPrint,
  onExportJson,
  onExportMarkdown,
}: ReportViewerSurfaceProps) {
  return (
    <div
      className={[
        "page",
        "page--report",
        isSample ? "page--report-sample" : "",
        isSample ? "sample-showcase-page" : "",
        isSample ? "sample-showcase-surface" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <section className="report-hero">
        {isSample ? (
          <SampleReportHero
            isZh={isZh}
            messages={messages}
            projectId={projectId}
            projectTitle={report?.project.title ?? projectId}
            decisionBand={decisionBand ?? messages.shell.states.notScored}
            totalScore={totalScore}
            riskCount={riskCount}
            locale={locale}
          />
        ) : (
          <div className="page-header page-header--report">
            <div className="stack-sm">
              <p className="eyebrow">
                {messages.shell.projectEyebrowPrefix} {projectId}
              </p>
              <h1 className="page-title">{messages.shell.title}</h1>
              <p className="page-subtitle">{subtitle}</p>
            </div>
            <div className="page-actions">
              {canViewMessages ? (
                <Link
                  className={buttonClassNames({ variant: "secondary" })}
                  href={buildLocalePath(locale, `/projects/${projectId}/chat`)}
                >
                  {messages.shell.actions.backToChat}
                </Link>
              ) : null}
              <Button
                type="button"
                variant="secondary"
                onClick={onRefresh}
                disabled={refreshDisabled}
                aria-label={messages.shell.actions.refreshAriaLabel}
              >
                {isRefreshing
                  ? messages.shell.actions.refreshing
                  : messages.shell.actions.refresh}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={onPrint}
                disabled={exportDisabled}
                aria-label={messages.shell.actions.printPdfAriaLabel}
              >
                {messages.shell.actions.printPdf}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={onExportJson}
                disabled={exportDisabled}
                aria-label={messages.shell.actions.exportJsonAriaLabel}
              >
                {messages.shell.actions.exportJson}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={onExportMarkdown}
                disabled={exportDisabled}
                aria-label={messages.shell.actions.exportMarkdownAriaLabel}
              >
                {messages.shell.actions.exportMarkdown}
              </Button>
            </div>
          </div>
        )}
      </section>

      {isSample ? null : <Separator />}

      <div className="report-scroll">
        <div
          className={[
            "report-canvas",
            isSample ? "report-canvas--sample" : "",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          {shouldShowReportJobStatus ? (
            <div className="stack-lg">
              <ReportJobStatusCard
                status={activeReportStatus}
                errorMessage={statusErrorMessage}
                retryable={reportStatus?.retryable ?? false}
                isStarting={isStartingReport}
                isLoading={isStatusLoading}
                onRetry={onStartReport}
                messages={messages}
              />
              {isStatusLoading || isReportJobPreparing || isLoading ? (
                <ReportViewerSkeleton />
              ) : null}
            </div>
          ) : isLoading && !report ? (
            <ReportViewerSkeleton />
          ) : errorMessage && !report ? (
            <Card variant="alert" role="alert">
              <CardHeader className="stack-sm">
                <CardTitle>{messages.shell.states.unavailableTitle}</CardTitle>
                <CardDescription>{errorMessage}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="cluster">
                  <Button
                    type="button"
                    onClick={onRetryLoad}
                    disabled={isLoading || isRefreshing}
                  >
                    {messages.shell.actions.retry}
                  </Button>
                  {canViewMessages ? (
                    <Link
                      className={buttonClassNames({ variant: "ghost" })}
                      href={buildLocalePath(locale, `/projects/${projectId}/chat`)}
                    >
                      {messages.shell.actions.returnToChat}
                    </Link>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          ) : isEmpty ? (
            <Card className="empty-state">
              <CardHeader className="stack-sm">
                <CardTitle>{messages.shell.states.emptyTitle}</CardTitle>
                <CardDescription>
                  {messages.shell.states.emptyDescription}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="cluster">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={onRefresh}
                    disabled={refreshDisabled}
                  >
                    {messages.shell.actions.refresh}
                  </Button>
                  {canViewMessages ? (
                    <Link
                      className={buttonClassNames({ variant: "ghost" })}
                      href={buildLocalePath(locale, `/projects/${projectId}/chat`)}
                    >
                      {messages.shell.actions.backToChat}
                    </Link>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          ) : report ? (
            <div className="stack-lg">
              {errorMessage ? (
                <Card variant="alert" role="alert">
                  <CardHeader className="stack-sm">
                    <CardTitle>{messages.shell.states.refreshFailedTitle}</CardTitle>
                    <CardDescription>{errorMessage}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Button
                      type="button"
                      onClick={onRetryRefresh}
                      disabled={refreshDisabled}
                    >
                      {messages.shell.actions.retryRefresh}
                    </Button>
                  </CardContent>
                </Card>
              ) : null}

              {reportLocaleMismatch ? (
                <Card variant="soft" role="note">
                  <CardHeader className="stack-sm">
                    <div className="cluster-tight">
                      <Badge variant="outline">
                        {messages.localeNotice.badgePrefix}: {reportLocaleLabel}
                      </Badge>
                    </div>
                    <CardTitle>{reportLocaleMismatch.title}</CardTitle>
                    <CardDescription>
                      {reportLocaleMismatch.description}
                    </CardDescription>
                  </CardHeader>
                </Card>
              ) : null}

              <ReportDocument
                confirmedStages={confirmedStages}
                currentStageLabel={currentStageLabel}
                decisionBand={decisionBand}
                decisionVariant={decisionVariant}
                interpolate={interpolate}
                isSample={isSample}
                isVerificationLoading={isVerificationLoading}
                locale={locale}
                messages={messages}
                overallSummary={overallSummary}
                report={report}
                riskCount={riskCount}
                stageSummaries={stageSummaries}
                totalScore={totalScore}
                verificationError={verificationError}
                verificationSnapshot={verificationSnapshot}
              />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
