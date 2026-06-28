import {
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Search,
  ShieldAlert,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type {
  ReportQualityObservation,
  ReportQualityObservationDetail,
  ReportQualityStatus,
} from "@/features/admin/report-quality";
import type {
  ReportQualityMessages,
  StatusFilter,
} from "./report-quality-dashboard-messages";

type LoadState = "idle" | "loading" | "ready" | "error";

type ReportQualityDashboardSurfaceProps = {
  detail: ReportQualityObservationDetail | null;
  detailError: string | null;
  hasLoadedData: boolean;
  isDetailLoading: boolean;
  loadError: string | null;
  loadState: LoadState;
  locale: string;
  messages: ReportQualityMessages;
  observations: ReportQualityObservation[];
  onQueryChange: (value: string) => void;
  onRefresh: () => void;
  onSelectObservation: (observationId: string) => void;
  onStatusFilterChange: (value: StatusFilter) => void;
  query: string;
  selectedId: string | null;
  statusCounts: Record<ReportQualityStatus, number>;
  statusFilter: StatusFilter;
  total: number;
};

const STATUS_VARIANTS: Record<
  ReportQualityStatus,
  "success" | "warning" | "danger"
> = {
  pass: "success",
  warn: "warning",
  fail: "danger",
};

const STATUS_ICONS = {
  pass: CheckCircle2,
  warn: AlertTriangle,
  fail: ShieldAlert,
} as const;

const resolveIntlLocale = (locale: string): string =>
  locale.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";

const formatTimestamp = (value: string | null, locale: string): string => {
  if (!value) {
    return "--";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "--";
  }
  return new Intl.DateTimeFormat(resolveIntlLocale(locale), {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
};

const interpolate = (
  template: string,
  values: Record<string, string | number>
): string =>
  Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template
  );

const getNumber = (
  value: Record<string, unknown>,
  key: string
): number | null => {
  const raw = value[key];
  if (typeof raw === "number" && Number.isFinite(raw)) {
    return raw;
  }
  if (typeof raw === "string") {
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const formatScore = (value: unknown): string => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Number.isInteger(value) ? String(value) : value.toFixed(1);
  }
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  return "--";
};

const asRecord = (value: unknown): Record<string, unknown> =>
  typeof value === "object" && value !== null ? (value as Record<string, unknown>) : {};

const asList = (value: unknown): unknown[] =>
  Array.isArray(value) ? value : [];

const asString = (value: unknown): string | null =>
  typeof value === "string" && value.trim() ? value.trim() : null;

export function ReportQualityDashboardSurface({
  detail,
  detailError,
  hasLoadedData,
  isDetailLoading,
  loadError,
  loadState,
  locale,
  messages,
  observations,
  onQueryChange,
  onRefresh,
  onSelectObservation,
  onStatusFilterChange,
  query,
  selectedId,
  statusCounts,
  statusFilter,
  total,
}: ReportQualityDashboardSurfaceProps) {
return (
  <div className="page">
    <div className="page-header">
      <div className="stack-sm">
        <p className="eyebrow">{messages.page.eyebrow}</p>
        <h1 className="page-title">{messages.page.title}</h1>
        <p className="page-subtitle">{messages.page.subtitle}</p>
      </div>
      <Button
        variant="secondary"
        onClick={onRefresh}
        disabled={loadState === "loading"}
      >
        <RefreshCw aria-hidden="true" />
        {loadState === "loading"
          ? messages.actions.refreshing
          : messages.actions.refresh}
      </Button>
    </div>

    {loadError ? (
      <Card variant="alert" role="alert">
        <CardHeader>
          <CardTitle>{messages.alerts.loadFailed}</CardTitle>
          <CardDescription>{loadError}</CardDescription>
        </CardHeader>
      </Card>
    ) : null}

    {loadState === "error" && !hasLoadedData ? null : (
      <section className="admin-dashboard" aria-label={messages.page.title}>
        <div className="admin-metrics-grid">
          <StatusMetric
            label={messages.metrics.total}
            value={total}
            tone="total"
          />
          <StatusMetric
            label={messages.metrics.fail}
            value={statusCounts.fail}
            tone="fail"
          />
          <StatusMetric
            label={messages.metrics.warn}
            value={statusCounts.warn}
            tone="warn"
          />
          <StatusMetric
            label={messages.metrics.pass}
            value={statusCounts.pass}
            tone="pass"
          />
        </div>

      <Card>
        <CardContent className="report-quality-filters">
          <label className="field">
            <span className="field__label">{messages.filters.search}</span>
            <span className="report-quality-search">
              <Search aria-hidden="true" />
              <input
                className="input"
                value={query}
                onChange={(event) => onQueryChange(event.target.value)}
                placeholder={messages.filters.searchPlaceholder}
              />
            </span>
          </label>
          <label className="field report-quality-status-filter">
            <span className="field__label">{messages.filters.status}</span>
            <select
              className="input"
              value={statusFilter}
              onChange={(event) => onStatusFilterChange(event.target.value as StatusFilter)}
            >
              <option value="all">{messages.filters.all}</option>
              <option value="fail">{messages.filters.fail}</option>
              <option value="warn">{messages.filters.warn}</option>
              <option value="pass">{messages.filters.pass}</option>
            </select>
          </label>
        </CardContent>
      </Card>

      <div className="report-quality-grid">
        <Card className="report-quality-table-card">
          <CardHeader>
            <CardTitle>{messages.page.title}</CardTitle>
            <CardDescription>
              {loadState === "loading" ? messages.actions.refreshing : null}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="report-quality-table-wrap">
              <table className="report-quality-table">
                <thead>
                  <tr>
                    <th scope="col">{messages.table.project}</th>
                    <th scope="col">{messages.table.report}</th>
                    <th scope="col">{messages.table.score}</th>
                    <th scope="col">{messages.table.evidence}</th>
                    <th scope="col">{messages.table.invariants}</th>
                    <th scope="col">{messages.table.observed}</th>
                    <th scope="col">{messages.table.actions}</th>
                  </tr>
                </thead>
                <tbody>
                  {observations.map((observation) => (
                    <ObservationRow
                      key={observation.id}
                      observation={observation}
                      isSelected={observation.id === selectedId}
                      locale={locale}
                      messages={messages}
                      onSelect={() => onSelectObservation(observation.id)}
                    />
                  ))}
                  {!observations.length ? (
                    <tr>
                      <td colSpan={7} className="report-quality-empty">
                        {messages.table.empty}
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <ObservationDetailPanel
          detail={detail}
          error={detailError}
          isLoading={isDetailLoading}
          messages={messages}
        />
      </div>
      </section>
    )}
  </div>
);
}

function StatusMetric({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: ReportQualityStatus | "total";
}) {
  const Icon =
    tone === "total"
      ? CheckCircle2
      : STATUS_ICONS[tone as ReportQualityStatus];
  return (
    <Card className={`admin-metric-card report-quality-metric--${tone}`}>
      <CardContent className="admin-metric">
        <div className="admin-metric__header">
          <span className="admin-metric__label">{label}</span>
          <Icon aria-hidden="true" />
        </div>
        <strong className="admin-metric__value">{value}</strong>
      </CardContent>
    </Card>
  );
}

function ObservationRow({
  observation,
  isSelected,
  locale,
  messages,
  onSelect,
}: {
  observation: ReportQualityObservation;
  isSelected: boolean;
  locale: string;
  messages: ReportQualityMessages;
  onSelect: () => void;
}) {
  const totalScore =
    observation.scoreSnapshot.total_score ?? observation.scoreSnapshot.totalScore;
  const unknowns = getNumber(observation.evidenceCounts, "unknowns") ?? 0;
  const gaps = getNumber(observation.evidenceCounts, "evidence_gaps") ?? 0;
  return (
    <tr className={isSelected ? "report-quality-row--selected" : undefined}>
      <td>
        <div className="stack-xs">
          <strong>{observation.projectTitle ?? messages.table.unknownProject}</strong>
          <span className="text-muted">
            {observation.orgName ?? messages.table.unknownOrg} ·{" "}
            {observation.orgSlug ?? observation.orgId}
          </span>
          <span className="text-muted text-mono">{observation.projectId}</span>
        </div>
      </td>
      <td>
        <div className="stack-xs">
          <Badge variant={STATUS_VARIANTS[observation.status]}>
            {messages.statusLabels[observation.status]}
          </Badge>
          <span>
            {interpolate(messages.table.reportVersion, {
              version: observation.reportVersion,
            })}
          </span>
          <span className="text-muted">
            {interpolate(messages.table.stateVersion, {
              version: observation.generatedFromStateVersion,
            })}
          </span>
        </div>
      </td>
      <td>
        <span className="report-quality-score">
          {messages.table.totalScore}: {formatScore(totalScore)}
        </span>
      </td>
      <td>
        <div className="stack-xs">
          <span>
            {messages.table.unknowns}: {unknowns}
          </span>
          <span>
            {messages.table.gaps}: {gaps}
          </span>
        </div>
      </td>
      <td>
        <InvariantStack
          failed={observation.failedInvariants}
          warnings={observation.warningInvariants}
          cleanLabel={messages.table.clean}
        />
      </td>
      <td>{formatTimestamp(observation.observedAt, locale)}</td>
      <td>
        <Button variant="ghost" size="sm" onClick={onSelect}>
          {messages.actions.inspect}
        </Button>
      </td>
    </tr>
  );
}

function InvariantStack({
  failed,
  warnings,
  cleanLabel,
}: {
  failed: string[];
  warnings: string[];
  cleanLabel: string;
}) {
  return (
    <div className="report-quality-invariants">
      {failed.slice(0, 2).map((item) => (
        <Badge key={`fail-${item}`} variant="danger">
          {item}
        </Badge>
      ))}
      {warnings.slice(0, 2).map((item) => (
        <Badge key={`warn-${item}`} variant="warning">
          {item}
        </Badge>
      ))}
      {!failed.length && !warnings.length ? (
        <Badge variant="success">{cleanLabel}</Badge>
      ) : null}
    </div>
  );
}

function ObservationDetailPanel({
  detail,
  error,
  isLoading,
  messages,
}: {
  detail: ReportQualityObservationDetail | null;
  error: string | null;
  isLoading: boolean;
  messages: ReportQualityMessages;
}) {
  const observation = asRecord(detail?.observation);
  const evidence = asRecord(observation.evidence);
  const evidenceCounts = asRecord(evidence.counts);
  const unknowns = asRecord(observation.unknowns);
  const topGaps = asList(unknowns.top_gaps);
  const unknownItems = asList(unknowns.items);
  const canonical = asRecord(observation.canonical_boundaries);
  const nearestCase = asRecord(canonical.nearest_case);
  const withinBoundary = canonical.within_any_score_boundary === true;

  return (
    <Card className="report-quality-detail-card">
      <CardHeader>
        <CardTitle>{messages.detail.title}</CardTitle>
        <CardDescription>
          {detail?.reportId ??
            (isLoading ? messages.actions.refreshing : messages.detail.empty)}
        </CardDescription>
      </CardHeader>
      <CardContent className="report-quality-detail">
        {error ? (
          <p className="field__error" role="alert">
            {error}
          </p>
        ) : null}
        {!detail ? (
          <p className="text-muted">{messages.detail.empty}</p>
        ) : (
          <>
            <DetailSection
              title={messages.detail.failed}
              items={detail.failedInvariants}
              empty={messages.detail.noItems}
              variant="danger"
            />
            <DetailSection
              title={messages.detail.warnings}
              items={detail.warningInvariants}
              empty={messages.detail.noItems}
              variant="warning"
            />

            <div className="report-quality-detail-section">
              <h3>{messages.detail.evidence}</h3>
              <dl className="report-quality-kv-grid">
                {Object.entries(evidenceCounts).map(([key, value]) => (
                  <div key={key}>
                    <dt>{key}</dt>
                    <dd>{formatScore(value)}</dd>
                  </div>
                ))}
              </dl>
            </div>

            <div className="report-quality-detail-section">
              <h3>{messages.detail.canonical}</h3>
              <Badge variant={withinBoundary ? "success" : "warning"}>
                {withinBoundary
                  ? messages.detail.withinBoundary
                  : messages.detail.outsideBoundary}
              </Badge>
              <p className="text-muted">
                {messages.detail.nearestCase}:{" "}
                {asString(nearestCase.id) ?? messages.detail.noNearestCase}
              </p>
            </div>

            <div className="report-quality-detail-section">
              <h3>{messages.detail.unknowns}</h3>
              <ul className="report-quality-detail-list">
                {[...topGaps, ...unknownItems].slice(0, 6).map((item, index) => {
                  const row = asRecord(item);
                  const label =
                    asString(row.label) ||
                    asString(row.path) ||
                    asString(item) ||
                    messages.detail.noItems;
                  return <li key={`${label}-${index}`}>{label}</li>;
                })}
                {!topGaps.length && !unknownItems.length ? (
                  <li>{messages.detail.noItems}</li>
                ) : null}
              </ul>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function DetailSection({
  title,
  items,
  empty,
  variant,
}: {
  title: string;
  items: string[];
  empty: string;
  variant: "danger" | "warning";
}) {
  return (
    <div className="report-quality-detail-section">
      <h3>{title}</h3>
      <div className="report-quality-pill-list">
        {items.length ? (
          items.map((item) => (
            <Badge key={item} variant={variant}>
              {item}
            </Badge>
          ))
        ) : (
          <span className="text-muted">{empty}</span>
        )}
      </div>
    </div>
  );
}
