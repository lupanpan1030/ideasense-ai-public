"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  fetchProjectReport,
  fetchProjectReportStatus,
  getReportErrorMessage,
} from "./reports-api";
import { fetchProjectPermissions } from "@/features/projects/project-permissions";
import {
  confirmStage,
  fetchStageVerification,
  type ProjectVerificationSnapshot,
} from "@/features/assessments/api";
import { fetchProjectContext } from "@/features/context/project-context";
import {
  buildReportMarkdown,
  buildStageSummaries,
  isReportEmpty,
} from "./reports-normalize";
import type {
  ReportJobStatus,
  ReportSnapshot,
} from "./reports-normalize";
import { buildReportFilename, exportJson, exportMarkdown } from "./report-export";
import { buildSampleVerificationSnapshot } from "./report-sample-verification";
import {
  formatScore,
  resolveDecisionVariant,
} from "./report-viewer-helpers";
import { ReportViewerSurface } from "./report-viewer-surface";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import { getLocaleDisplayName } from "@/lib/i18n/artifact-locale";

type ReportViewerProps = {
  projectId: string;
  mode?: "live" | "sample";
  reportOverride?: ReportSnapshot;
  autoStartReport?: boolean;
};

export function ReportViewer({
  projectId,
  mode = "live",
  reportOverride,
  autoStartReport = false,
}: ReportViewerProps) {
  const appMessages = useAppMessages();
  const locale = useAppLocale();
  const { reportViewer: messages } = appMessages;
  const isSample = mode === "sample";
  const isZh = locale === "zh";
  const [report, setReport] = useState<ReportSnapshot | null>(
    reportOverride ?? null
  );
  const [reportStatus, setReportStatus] = useState<ReportJobStatus | null>(null);
  const [isLoading, setIsLoading] = useState(!reportOverride);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isStatusLoading, setIsStatusLoading] = useState(!reportOverride);
  const [isStartingReport, setIsStartingReport] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusErrorMessage, setStatusErrorMessage] = useState<string | null>(
    null
  );
  const [verificationSnapshot, setVerificationSnapshot] =
    useState<ProjectVerificationSnapshot | null>(() =>
      isSample ? buildSampleVerificationSnapshot(reportOverride ?? null) : null
    );
  const [verificationError, setVerificationError] = useState<string | null>(null);
  const [isVerificationLoading, setIsVerificationLoading] = useState(false);
  const [canViewMessages, setCanViewMessages] = useState<boolean | null>(
    isSample ? false : null
  );
  const abortRef = useRef<AbortController | null>(null);
  const statusAbortRef = useRef<AbortController | null>(null);
  const verificationAbortRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);
  const statusRequestIdRef = useRef(0);
  const verificationRequestIdRef = useRef(0);
  const startReportAttemptedRef = useRef(false);
  const isMountedRef = useRef(true);

  const isEmpty = useMemo(() => isReportEmpty(report), [report]);
  const reportMarkdown = useMemo(
    () => (report ? buildReportMarkdown(report, appMessages) : ""),
    [appMessages, report]
  );
  const stageSummaries = useMemo(
    () =>
      report
        ? buildStageSummaries(report.assessments, report.userEditedPaths)
        : [],
    [report]
  );
  const confirmedStages = useMemo(
    () => stageSummaries.filter((stage) => stage.status === "confirmed").length,
    [stageSummaries]
  );
  const decisionBand = report?.dvfScoreboard.decisionBand ?? null;
  const decisionVariant = resolveDecisionVariant(decisionBand);
  const totalScore = formatScore(report?.dvfScoreboard.totalScore ?? null);
  const riskCount = report?.keyRisks.length ?? 0;
  const overallSummary = report?.overallSummary?.trim() ?? "";
  const currentStageLabel = report
    ? messages.stageLabels[report.project.currentStage] ?? report.project.currentStage
    : null;
  const reportLocaleLabel = report
    ? getLocaleDisplayName(appMessages, report.artifactLocale)
    : null;
  const activeReportStatus = reportStatus?.status ?? null;
  const isReportJobPreparing =
    isStartingReport ||
    activeReportStatus === "queued" ||
    activeReportStatus === "running" ||
    activeReportStatus === "finalizing";

  const interpolate = useCallback(
    (template: string, values: Record<string, string | number>) =>
      Object.entries(values).reduce(
        (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
        template
      ),
    []
  );
  const reportLocaleMismatch =
    report &&
    report.artifactLocale &&
    report.artifactLocale !== locale &&
    reportLocaleLabel
      ? {
          title: interpolate(messages.localeNotice.mismatchTitle, {
            locale: reportLocaleLabel,
          }),
          description: messages.localeNotice.mismatchDescription,
        }
      : null;

  const loadVerification = useCallback(
    async ({ silent }: { silent?: boolean } = {}) => {
      if (isSample) {
        return;
      }
      const requestId = verificationRequestIdRef.current + 1;
      verificationRequestIdRef.current = requestId;
      const controller = new AbortController();
      if (verificationAbortRef.current) {
        verificationAbortRef.current.abort();
      }
      verificationAbortRef.current = controller;

      if (!silent) {
        setIsVerificationLoading(true);
      }

      try {
        const snapshot = await fetchStageVerification(projectId, {
          signal: controller.signal,
        });
        if (
          !isMountedRef.current ||
          controller.signal.aborted ||
          verificationRequestIdRef.current !== requestId
        ) {
          return;
        }
        setVerificationSnapshot(snapshot);
        setVerificationError(null);
      } catch {
        if (
          !isMountedRef.current ||
          controller.signal.aborted ||
          verificationRequestIdRef.current !== requestId
        ) {
          return;
        }
        setVerificationError("Unable to load verification.");
      } finally {
        if (verificationAbortRef.current === controller) {
          verificationAbortRef.current = null;
        }
        if (
          !isMountedRef.current ||
          controller.signal.aborted ||
          verificationRequestIdRef.current !== requestId
        ) {
          return;
        }
        setIsVerificationLoading(false);
      }
    },
    [projectId, isSample]
  );

  const loadReport = useCallback(
    async ({ silent }: { silent?: boolean } = {}) => {
      if (isSample) {
        return;
      }
      const requestId = requestIdRef.current + 1;
      requestIdRef.current = requestId;
      const controller = new AbortController();
      if (abortRef.current) {
        abortRef.current.abort();
      }
      abortRef.current = controller;

      if (silent) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }

      try {
        const snapshot = await fetchProjectReport(projectId, {
          signal: controller.signal,
          outputLocale: locale,
        });
        if (
          !isMountedRef.current ||
          controller.signal.aborted ||
          requestIdRef.current !== requestId
        ) {
          return;
        }
        setReport(snapshot);
        setErrorMessage(null);
      } catch (error) {
        if (
          !isMountedRef.current ||
          controller.signal.aborted ||
          requestIdRef.current !== requestId
        ) {
          return;
        }
        setErrorMessage(getReportErrorMessage(error));
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
        }
        if (
          !isMountedRef.current ||
          controller.signal.aborted ||
          requestIdRef.current !== requestId
        ) {
          return;
        }
        if (silent) {
          setIsRefreshing(false);
        } else {
          setIsLoading(false);
        }
      }
    },
    [locale, projectId, isSample]
  );

  const loadReportStatus = useCallback(
    async ({ silent }: { silent?: boolean } = {}) => {
      if (isSample) {
        return null;
      }
      const requestId = statusRequestIdRef.current + 1;
      statusRequestIdRef.current = requestId;
      const controller = new AbortController();
      if (statusAbortRef.current) {
        statusAbortRef.current.abort();
      }
      statusAbortRef.current = controller;

      if (!silent) {
        setIsStatusLoading(true);
      }

      try {
        const status = await fetchProjectReportStatus(projectId, {
          signal: controller.signal,
          outputLocale: locale,
        });
        if (
          !isMountedRef.current ||
          controller.signal.aborted ||
          statusRequestIdRef.current !== requestId
        ) {
          return null;
        }
        setReportStatus(status);
        setStatusErrorMessage(null);
        if (status.status !== "ready") {
          setIsLoading(false);
        }
        return status;
      } catch (error) {
        if (
          !isMountedRef.current ||
          controller.signal.aborted ||
          statusRequestIdRef.current !== requestId
        ) {
          return null;
        }
        setStatusErrorMessage(getReportErrorMessage(error));
        setIsLoading(false);
        return null;
      } finally {
        if (statusAbortRef.current === controller) {
          statusAbortRef.current = null;
        }
        if (
          !isMountedRef.current ||
          controller.signal.aborted ||
          statusRequestIdRef.current !== requestId
        ) {
          return;
        }
        if (!silent) {
          setIsStatusLoading(false);
        }
      }
    },
    [locale, projectId, isSample]
  );

  const startReportJob = useCallback(
    async () => {
      if (isSample || isStartingReport) {
        return;
      }
      setIsStartingReport(true);
      setStatusErrorMessage(null);
      try {
        const contextVersion =
          reportStatus?.contextVersion ??
          (await fetchProjectContext(projectId)).contextVersion;
        const result = await confirmStage({
          projectId,
          stage: "report",
          clientContextVersion: contextVersion,
          outputLocale: locale,
        });
        if (result.reportJobStatus) {
          setReportStatus(result.reportJobStatus);
        } else {
          await loadReportStatus({ silent: true });
        }
      } catch (error) {
        if (isMountedRef.current) {
          setStatusErrorMessage(getReportErrorMessage(error));
        }
      } finally {
        if (isMountedRef.current) {
          setIsStartingReport(false);
        }
      }
    },
    [
      isSample,
      isStartingReport,
      loadReportStatus,
      locale,
      projectId,
      reportStatus?.contextVersion,
    ]
  );

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }
      if (statusAbortRef.current) {
        statusAbortRef.current.abort();
        statusAbortRef.current = null;
      }
      if (verificationAbortRef.current) {
        verificationAbortRef.current.abort();
        verificationAbortRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    let isActive = true;
    if (isSample) {
      setCanViewMessages(false);
      return () => {
        isActive = false;
      };
    }
    setCanViewMessages(null);
    fetchProjectPermissions(projectId)
      .then((permissions) => {
        if (!isActive) {
          return;
        }
        setCanViewMessages(permissions.can_view_messages);
      })
      .catch(() => {
        if (!isActive) {
          return;
        }
        setCanViewMessages(false);
      });

    return () => {
      isActive = false;
    };
  }, [projectId, isSample]);

  useEffect(() => {
    if (isSample) {
      const sampleSnapshot = reportOverride ?? null;
      setReport(sampleSnapshot);
      setIsLoading(false);
      setIsRefreshing(false);
      setIsStatusLoading(false);
      setIsStartingReport(false);
      setErrorMessage(null);
      setStatusErrorMessage(null);
      setReportStatus(null);
      setVerificationSnapshot(buildSampleVerificationSnapshot(sampleSnapshot));
      setVerificationError(null);
      setIsVerificationLoading(false);
      return;
    }
    setReport(null);
    setReportStatus(null);
    startReportAttemptedRef.current = false;
    setIsLoading(true);
    setIsRefreshing(false);
    setIsStatusLoading(true);
    setIsStartingReport(false);
    setErrorMessage(null);
    setStatusErrorMessage(null);
    setVerificationSnapshot(null);
    setVerificationError(null);
    setIsVerificationLoading(true);
    void loadReportStatus();
    void loadVerification({ silent: true });
  }, [
    isSample,
    loadReport,
    loadReportStatus,
    loadVerification,
    projectId,
    reportOverride,
  ]);

  const handleRefresh = useCallback(() => {
    if (isSample || isLoading || isRefreshing) {
      return;
    }
    void loadReport({ silent: true });
    void loadReportStatus({ silent: true });
    void loadVerification({ silent: true });
  }, [
    isSample,
    isLoading,
    isRefreshing,
    loadReport,
    loadReportStatus,
    loadVerification,
  ]);

  useEffect(() => {
    if (isSample || report) {
      return;
    }
    const status = reportStatus?.status;
    if (!status) {
      return;
    }

    if (status === "ready") {
      void loadReport({ silent: true });
      return;
    }

    if (status === "queued" || status === "running" || status === "finalizing") {
      const timeoutId = setTimeout(() => {
        void loadReportStatus({ silent: true });
      }, reportStatus.nextPollMs);
      return () => clearTimeout(timeoutId);
    }

    const canStart =
      autoStartReport &&
      status === "not_started" &&
      reportStatus.retryable &&
      reportStatus.currentStage?.trim().toLowerCase() === "report";
    if (canStart && !startReportAttemptedRef.current) {
      startReportAttemptedRef.current = true;
      void startReportJob();
    }
  }, [
    isSample,
    loadReport,
    loadReportStatus,
    report,
    reportStatus,
    startReportJob,
    autoStartReport,
  ]);

  const handleExportJson = useCallback(() => {
    if (!report || isEmpty || isSample) {
      return;
    }
    exportJson(report, buildReportFilename(report.projectId, "json"));
  }, [isEmpty, report, isSample]);

  const handleExportMarkdown = useCallback(() => {
    if (!report || isEmpty || isSample) {
      return;
    }
    exportMarkdown(
      reportMarkdown,
      buildReportFilename(report.projectId, "md")
    );
  }, [isEmpty, report, reportMarkdown, isSample]);

  const handlePrint = useCallback(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.print();
  }, []);

  const handleStartReport = useCallback(() => {
    startReportAttemptedRef.current = true;
    void startReportJob();
  }, [startReportJob]);

  const exportDisabled = !report || isEmpty || isSample;
  const refreshDisabled = isSample || isLoading || isRefreshing;
  const shouldShowReportFetchError = Boolean(
    errorMessage && !report && activeReportStatus === "ready"
  );
  const shouldShowReportJobStatus =
    !report &&
    !isSample &&
    !shouldShowReportFetchError &&
    (isStatusLoading ||
      isReportJobPreparing ||
      Boolean(activeReportStatus) ||
      Boolean(statusErrorMessage));
  const subtitle = isSample
    ? messages.shell.sampleSubtitle
    : messages.shell.liveSubtitle;

  return (
    <ReportViewerSurface
      projectId={projectId}
      isSample={isSample}
      isZh={isZh}
      locale={locale}
      messages={messages}
      subtitle={subtitle}
      canViewMessages={canViewMessages}
      report={report}
      reportStatus={reportStatus}
      activeReportStatus={activeReportStatus}
      reportLocaleLabel={reportLocaleLabel}
      reportLocaleMismatch={reportLocaleMismatch}
      decisionBand={decisionBand}
      decisionVariant={decisionVariant}
      totalScore={totalScore}
      riskCount={riskCount}
      overallSummary={overallSummary}
      currentStageLabel={currentStageLabel}
      stageSummaries={stageSummaries}
      confirmedStages={confirmedStages}
      isEmpty={isEmpty}
      isLoading={isLoading}
      isRefreshing={isRefreshing}
      isStatusLoading={isStatusLoading}
      isStartingReport={isStartingReport}
      isReportJobPreparing={isReportJobPreparing}
      exportDisabled={exportDisabled}
      refreshDisabled={refreshDisabled}
      errorMessage={errorMessage}
      statusErrorMessage={statusErrorMessage}
      shouldShowReportJobStatus={shouldShowReportJobStatus}
      isVerificationLoading={isVerificationLoading}
      verificationError={verificationError}
      verificationSnapshot={verificationSnapshot}
      interpolate={interpolate}
      onRefresh={handleRefresh}
      onRetryLoad={() => void loadReport()}
      onRetryRefresh={handleRefresh}
      onStartReport={handleStartReport}
      onPrint={handlePrint}
      onExportJson={handleExportJson}
      onExportMarkdown={handleExportMarkdown}
    />
  );
}
