"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  fetchReportQualityObservation,
  fetchReportQualityObservations,
  fetchReportQualitySummary,
  getReportQualityErrorMessage,
  type ReportQualityObservation,
  type ReportQualityObservationDetail,
  type ReportQualityStatus,
  type ReportQualitySummary,
} from "@/features/admin/report-quality";
import { useAppLocale } from "@/lib/i18n/provider";
import { ReportQualityDashboardSurface } from "./report-quality-dashboard-surface";
import {
  REPORT_QUALITY_MESSAGES,
  type StatusFilter,
} from "./report-quality-dashboard-messages";

type LoadState = "idle" | "loading" | "ready" | "error";

const getStatusCount = (
  summary: ReportQualitySummary | null,
  status: ReportQualityStatus
): number =>
  summary?.statusCounts.find((item) => item.status === status)?.count ?? 0;

export function ReportQualityDashboard() {
  const locale = useAppLocale();
  const messages = REPORT_QUALITY_MESSAGES[locale];
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [summary, setSummary] = useState<ReportQualitySummary | null>(null);
  const [observations, setObservations] = useState<ReportQualityObservation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] =
    useState<ReportQualityObservationDetail | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [refreshToken, setRefreshToken] = useState(0);

  const loadDetail = useCallback(
    async (observationId: string) => {
      setIsDetailLoading(true);
      setDetailError(null);
      try {
        const detail = await fetchReportQualityObservation(observationId);
        setSelectedDetail(detail);
        setSelectedId(observationId);
      } catch (error) {
        setDetailError(getReportQualityErrorMessage(error, messages.errors));
      } finally {
        setIsDetailLoading(false);
      }
    },
    [messages.errors]
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedQuery(query.trim());
    }, 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    let isActive = true;
    const loadDashboard = async () => {
      setLoadState("loading");
      setLoadError(null);
      const filters = {
        status: statusFilter,
        q: debouncedQuery,
        limit: 20,
        offset: 0,
      };
      try {
        const [nextSummary, nextList] = await Promise.all([
          fetchReportQualitySummary(filters),
          fetchReportQualityObservations(filters),
        ]);
        if (!isActive) {
          return;
        }
        setSummary(nextSummary);
        setObservations(nextList.observations);
        setLoadState("ready");
        const nextSelected = nextList.observations[0]?.id ?? null;
        setSelectedId(nextSelected);
        if (nextSelected) {
          await loadDetail(nextSelected);
        } else {
          setSelectedDetail(null);
        }
      } catch (error) {
        if (!isActive) {
          return;
        }
        setLoadError(getReportQualityErrorMessage(error, messages.errors));
        setLoadState("error");
      }
    };
    loadDashboard();
    return () => {
      isActive = false;
    };
  }, [
    debouncedQuery,
    loadDetail,
    messages.errors,
    refreshToken,
    statusFilter,
  ]);

  const statusCounts = useMemo(
    () => ({
      pass: getStatusCount(summary, "pass"),
      warn: getStatusCount(summary, "warn"),
      fail: getStatusCount(summary, "fail"),
    }),
    [summary]
  );

  return (
    <ReportQualityDashboardSurface
      detail={selectedDetail}
      detailError={detailError}
      hasLoadedData={Boolean(summary) || observations.length > 0}
      isDetailLoading={isDetailLoading}
      loadError={loadError}
      loadState={loadState}
      locale={locale}
      messages={messages}
      observations={observations}
      onQueryChange={setQuery}
      onRefresh={() => setRefreshToken((value) => value + 1)}
      onSelectObservation={loadDetail}
      onStatusFilterChange={setStatusFilter}
      query={query}
      selectedId={selectedId}
      statusCounts={statusCounts}
      statusFilter={statusFilter}
      total={summary?.total ?? 0}
    />
  );
}
