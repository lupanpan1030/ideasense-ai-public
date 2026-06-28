"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { buttonClassNames } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api/client";
import {
  getVisibleAdminQuickActions,
  type AdminNavItemKey,
} from "@/features/admin/admin-route-config";
import { useAdminSession } from "@/features/admin/admin-session-context";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";

type MetricTone = "primary" | "success" | "warning";
type TrendTone = "success" | "warning" | "info";

type OverviewMetric = {
  label: string;
  value: string;
  delta: string;
  tone: MetricTone;
  series: number[];
};

type EnrollmentTrend = {
  label: string;
  sublabel: string;
  total: string;
  change: string;
  tone: TrendTone;
  series: number[];
};

type CohortProgressItem = {
  id: string;
  name: string;
  progress: number;
  meta: string;
};

type PendingAction = {
  title: string;
  detail: string;
  tone: MetricTone;
};

type UpcomingDeadline = {
  title: string;
  due_at: string | null;
};

type ActivityItem = {
  title: string;
  detail: string;
  created_at: string;
};

type InsightHighlight = {
  title: string;
  detail: string;
};

type AdminOverviewResponse = {
  overview_metrics: OverviewMetric[];
  enrollment_trend: EnrollmentTrend;
  cohort_progress: CohortProgressItem[];
  pending_actions: PendingAction[];
  upcoming_deadlines: UpcomingDeadline[];
  activity_feed: ActivityItem[];
  insight_highlights: InsightHighlight[];
};

const fetchOverview = async (locale: string): Promise<AdminOverviewResponse> =>
  apiClient.fetchJson<AdminOverviewResponse>(
    `/admin-api/overview?output_locale=${encodeURIComponent(locale)}`
  );

const EMPTY_METRICS: OverviewMetric[] = [];
const EMPTY_COHORTS: CohortProgressItem[] = [];
const EMPTY_PENDING: PendingAction[] = [];
const EMPTY_DEADLINES: UpcomingDeadline[] = [];
const EMPTY_ACTIVITY: ActivityItem[] = [];
const EMPTY_INSIGHTS: InsightHighlight[] = [];

const resolveIntlLocale = (locale: string): string =>
  locale.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";

const getOverviewErrorMessage = (
  error: unknown,
  messages: ReturnType<typeof useAppMessages>["adminOverview"]
): string => {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return messages.error.expiredSession;
    }
    if (error.status === 403) {
      return messages.error.noAccess;
    }
    if (error.status >= 500) {
      return messages.error.unavailable;
    }
  }
  return messages.error.loadFailed;
};

const buildSparklinePaths = (
  points: number[],
  width: number,
  height: number
) => {
  const safePoints = points.length ? points : [0, 0];
  const min = Math.min(...safePoints);
  const max = Math.max(...safePoints);
  const range = max - min || 1;
  const step = width / Math.max(safePoints.length - 1, 1);

  const coords = safePoints.map((value, index) => {
    const x = index * step;
    const y = height - ((value - min) / range) * height;
    return { x, y };
  });

  const line = coords
    .map((point, index) => {
      const command = index === 0 ? "M" : "L";
      return `${command} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`;
    })
    .join(" ");

  const area =
    `M 0 ${height} ` +
    coords.map((point) => `L ${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(" ") +
    ` L ${width} ${height} Z`;

  return { line, area };
};

const Sparkline = ({
  points,
  width,
  height,
  tone = "primary",
  label,
}: {
  points: number[];
  width: number;
  height: number;
  tone?: MetricTone;
  label: string;
}) => {
  const { line, area } = buildSparklinePaths(points, width, height);
  return (
    <svg
      className={`admin-sparkline admin-sparkline--${tone}`}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={label}
    >
      <path className="admin-sparkline__area" d={area} />
      <path className="admin-sparkline__line" d={line} />
    </svg>
  );
};

const formatRelativeTimeWithLocale = (value: string, locale: string): string => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "--";
  }
  const diffMs = parsed.getTime() - Date.now();
  const diffSeconds = Math.round(diffMs / 1000);
  const rtf = new Intl.RelativeTimeFormat(resolveIntlLocale(locale), {
    numeric: "auto",
  });
  const absSeconds = Math.abs(diffSeconds);

  if (absSeconds < 60) {
    return rtf.format(diffSeconds, "second");
  }

  const diffMinutes = Math.round(diffSeconds / 60);
  if (Math.abs(diffMinutes) < 60) {
    return rtf.format(diffMinutes, "minute");
  }

  const diffHours = Math.round(diffMinutes / 60);
  if (Math.abs(diffHours) < 24) {
    return rtf.format(diffHours, "hour");
  }

  const diffDays = Math.round(diffHours / 24);
  if (Math.abs(diffDays) < 30) {
    return rtf.format(diffDays, "day");
  }

  const diffMonths = Math.round(diffDays / 30);
  if (Math.abs(diffMonths) < 12) {
    return rtf.format(diffMonths, "month");
  }

  const diffYears = Math.round(diffDays / 365);
  return rtf.format(diffYears, "year");
};

const formatDeadlineWithLocale = (value: string | null, locale: string): string => {
  if (!value) {
    return "--";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "--";
  }
  const dateLabel = new Intl.DateTimeFormat(resolveIntlLocale(locale), {
    month: "short",
    day: "numeric",
  }).format(parsed);
  return `${dateLabel} (${formatRelativeTimeWithLocale(value, locale)})`;
};

const resolveTrendVariant = (tone: TrendTone) => {
  if (tone === "success") {
    return "success";
  }
  if (tone === "warning") {
    return "warning";
  }
  return "info";
};

const getQuickActionLabel = (
  key: AdminNavItemKey,
  messages: ReturnType<typeof useAppMessages>["adminOverview"]
): string | null => {
  switch (key) {
    case "organization":
      return messages.quickActions.organization;
    case "members":
      return messages.quickActions.members;
    case "cohorts":
      return messages.quickActions.cohorts;
    case "mentorAssignments":
      return messages.quickActions.assignments;
    case "reports":
      return messages.quickActions.reports;
    case "prompts":
      return messages.quickActions.prompts;
    case "questionBanks":
      return messages.quickActions.questionBanks;
    case "reportQuality":
      return messages.quickActions.reportQuality;
    case "platformSettings":
      return messages.quickActions.platformSettings;
    default:
      return null;
  }
};

export function AdminOverviewClient() {
  const locale = useAppLocale();
  const messages = useAppMessages().adminOverview;
  const session = useAdminSession();
  const quickActions = getVisibleAdminQuickActions(session).flatMap((item) => {
    const label = getQuickActionLabel(item.key, messages);
    return label ? [{ ...item, label }] : [];
  });
  const [data, setData] = useState<AdminOverviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;
    fetchOverview(locale)
      .then((response) => {
        if (!isActive) {
          return;
        }
        setData(response);
        setIsLoading(false);
      })
      .catch((err) => {
        if (!isActive) {
          return;
        }
        setError(getOverviewErrorMessage(err, messages));
        setIsLoading(false);
      });

    return () => {
      isActive = false;
    };
  }, [locale, messages]);

  const overviewMetrics = data?.overview_metrics ?? EMPTY_METRICS;
  const enrollmentTrend = data?.enrollment_trend;
  const cohortProgress = data?.cohort_progress ?? EMPTY_COHORTS;
  const pendingActions = data?.pending_actions ?? EMPTY_PENDING;
  const upcomingDeadlines = data?.upcoming_deadlines ?? EMPTY_DEADLINES;
  const activityFeed = data?.activity_feed ?? EMPTY_ACTIVITY;
  const insightHighlights = data?.insight_highlights ?? EMPTY_INSIGHTS;

  if (isLoading && !data) {
    return (
      <div className="admin-dashboard">
        <Card className="admin-bento-card">
          <CardHeader className="stack-sm">
            <CardTitle>{messages.loading.title}</CardTitle>
            <CardDescription>{messages.loading.description}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="admin-dashboard">
        <Card className="admin-bento-card">
          <CardHeader className="stack-sm">
            <CardTitle>{messages.error.title}</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="admin-dashboard">
      <section className="admin-metrics-grid">
        {overviewMetrics.length === 0 ? (
          <Card className="admin-metric-card">
            <CardContent className="admin-metric">
              <div className="admin-metric__label">{messages.metrics.empty}</div>
            </CardContent>
          </Card>
        ) : (
          overviewMetrics.map((metric) => (
            <Card key={metric.label} className="admin-metric-card">
              <CardContent className="admin-metric">
                <div className="admin-metric__header">
                  <span className="admin-metric__label">{metric.label}</span>
                  <span
                    className={`admin-metric__delta admin-metric__delta--${metric.tone}`}
                  >
                    {metric.delta}
                  </span>
                </div>
                <div className="admin-metric__value">{metric.value}</div>
                <Sparkline
                  points={metric.series}
                  width={120}
                  height={36}
                  tone={metric.tone}
                  label={messages.metrics.sparklineAriaLabel.replace(
                    "{label}",
                    metric.label
                  )}
                />
              </CardContent>
            </Card>
          ))
        )}
      </section>

      <section className="admin-bento-grid">
        <Card className="admin-bento-card admin-bento-card--trend">
          <CardHeader className="stack-sm">
            <CardTitle>
              {enrollmentTrend?.label ?? messages.trend.fallbackTitle}
            </CardTitle>
            <CardDescription>
              {enrollmentTrend?.sublabel ?? messages.trend.fallbackDescription}
            </CardDescription>
          </CardHeader>
          <CardContent className="admin-trend-card__content">
            <div className="admin-trend-card__summary">
              <div>
                <p className="admin-metric__label">{messages.trend.newMembers}</p>
                <p className="admin-trend-card__value">
                  {enrollmentTrend?.total ?? "--"}
                </p>
              </div>
              <Badge
                variant={resolveTrendVariant(enrollmentTrend?.tone ?? "info")}
              >
                {enrollmentTrend?.change ?? ""}
              </Badge>
            </div>
            <Sparkline
              points={enrollmentTrend?.series ?? []}
              width={520}
              height={160}
              tone="primary"
              label={messages.trend.chartAriaLabel}
            />
          </CardContent>
        </Card>

        <Card className="admin-bento-card admin-bento-card--activity">
          <CardHeader className="stack-sm">
            <CardTitle>{messages.sections.recentActivityTitle}</CardTitle>
            <CardDescription>
              {messages.sections.recentActivityDescription}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {activityFeed.length === 0 ? (
              <div className="admin-activity-item">
                {messages.states.noRecentActivity}
              </div>
            ) : (
              <ul className="admin-activity-list">
                {activityFeed.map((item) => (
                  <li key={`${item.title}-${item.created_at}`} className="admin-activity-item">
                    <div>
                      <p className="admin-activity-item__title">{item.title}</p>
                      <p className="admin-activity-item__detail">{item.detail}</p>
                    </div>
                    <span className="admin-activity-item__time">
                      {formatRelativeTimeWithLocale(item.created_at, locale)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="admin-bento-card admin-bento-card--cohorts">
          <CardHeader className="stack-sm">
            <CardTitle>{messages.sections.activeCohortsTitle}</CardTitle>
            <CardDescription>
              {messages.sections.activeCohortsDescription}
            </CardDescription>
          </CardHeader>
          <CardContent className="admin-progress-list">
            {cohortProgress.length === 0 ? (
              <div className="admin-progress-item">
                {messages.states.noActiveCohorts}
              </div>
            ) : (
              cohortProgress.map((cohort) => (
                <div key={cohort.id} className="admin-progress-item">
                  <div className="admin-progress-item__header">
                    <span>{cohort.name}</span>
                    <span>{cohort.progress}%</span>
                  </div>
                  <div className="admin-progress-item__meta">{cohort.meta}</div>
                  <div className="admin-progress-bar">
                    <span style={{ width: `${cohort.progress}%` }} />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="admin-bento-card admin-bento-card--pending">
          <CardHeader className="stack-sm">
            <CardTitle>{messages.sections.pendingActionsTitle}</CardTitle>
            <CardDescription>
              {messages.sections.pendingActionsDescription}
            </CardDescription>
          </CardHeader>
          <CardContent className="admin-list">
            {pendingActions.length === 0 ? (
              <div className="admin-list-item">
                <div>
                  <p className="admin-list-item__title">
                    {messages.states.allCaughtUpTitle}
                  </p>
                  <p className="admin-list-item__detail">
                    {messages.states.allCaughtUpDescription}
                  </p>
                </div>
              </div>
            ) : (
              pendingActions.map((item) => (
                <div key={item.title} className="admin-list-item">
                  <div>
                    <p className="admin-list-item__title">{item.title}</p>
                    <p className="admin-list-item__detail">{item.detail}</p>
                  </div>
                  <Badge variant={item.tone === "warning" ? "warning" : "info"}>
                    {item.tone === "warning"
                      ? messages.badges.priority
                      : messages.badges.active}
                  </Badge>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="admin-bento-card admin-bento-card--deadlines">
          <CardHeader className="stack-sm">
            <CardTitle>{messages.sections.upcomingDeadlinesTitle}</CardTitle>
            <CardDescription>
              {messages.sections.upcomingDeadlinesDescription}
            </CardDescription>
          </CardHeader>
          <CardContent className="admin-list">
            {upcomingDeadlines.length === 0 ? (
              <div className="admin-list-item admin-list-item--tight">
                <div>
                  <p className="admin-list-item__title">
                    {messages.states.noUpcomingDeadlines}
                  </p>
                  <p className="admin-list-item__detail">
                    {messages.states.noCohortDates}
                  </p>
                </div>
              </div>
            ) : (
              upcomingDeadlines.map((deadline) => (
                <div key={deadline.title} className="admin-list-item admin-list-item--tight">
                  <div>
                    <p className="admin-list-item__title">{deadline.title}</p>
                    <p className="admin-list-item__detail">
                      {formatDeadlineWithLocale(deadline.due_at, locale)}
                    </p>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="admin-bento-card admin-bento-card--insights">
          <CardHeader className="stack-sm">
            <CardTitle>{messages.sections.insightsTitle}</CardTitle>
            <CardDescription>{messages.sections.insightsDescription}</CardDescription>
          </CardHeader>
          <CardContent className="admin-insight-list">
            {insightHighlights.length === 0 ? (
              <div className="admin-insight-item">{messages.states.noInsights}</div>
            ) : (
              insightHighlights.map((insight) => (
                <div key={insight.title} className="admin-insight-item">
                  <p className="admin-insight-item__title">{insight.title}</p>
                  <p className="admin-insight-item__detail">{insight.detail}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="admin-bento-card admin-bento-card--actions">
          <CardHeader className="stack-sm">
            <CardTitle>{messages.sections.quickActionsTitle}</CardTitle>
            <CardDescription>{messages.sections.quickActionsDescription}</CardDescription>
          </CardHeader>
          <CardContent className="admin-actions-grid">
            {quickActions.map((item) => (
              <Link
                key={item.key}
                className={buttonClassNames({ variant: "secondary", size: "sm" })}
                href={buildLocalePath(locale, item.href)}
              >
                {item.label}
              </Link>
            ))}
            <Link
              className={buttonClassNames({ variant: "ghost", size: "sm" })}
              href={buildLocalePath(locale, "/projects")}
            >
              {messages.quickActions.backToWorkspace}
            </Link>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
