import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { ReportSnapshot } from "./reports-normalize";
import { formatScore, resolveDecisionVariant } from "./report-viewer-helpers";
import { useAppMessages } from "@/lib/i18n/provider";

type ReportV2ArtifactCardProps = {
  report: ReportSnapshot;
  className?: string;
};

export function ReportV2ArtifactCard({
  report,
  className = "",
}: ReportV2ArtifactCardProps) {
  const messages = useAppMessages().reportViewer;
  const v2Messages = messages.reportV2;
  const decision = report.decisionSnapshot;
  const rationales = report.scoreRationales;
  const rationaleEntries = rationales
    ? (["desirability", "viability", "feasibility"] as const)
        .map((key) => ({
          key,
          label: messages.scoreboard.metricLabels[key],
          detail: rationales[key],
        }))
        .filter((entry) => entry.detail)
    : [];
  const evidenceCounts = Object.entries(report.evidenceIndex?.counts ?? {});
  const evidenceItems = report.evidenceIndex?.items.slice(0, 6) ?? [];
  const hasContent =
    Boolean(decision) ||
    rationaleEntries.length > 0 ||
    report.riskRegister.length > 0 ||
    report.experimentPlan.length > 0 ||
    evidenceCounts.length > 0 ||
    evidenceItems.length > 0;

  return (
    <Card
      className={["report-v2-artifact", className].filter(Boolean).join(" ")}
    >
      <CardHeader>
        <CardTitle>{v2Messages.title}</CardTitle>
        <CardDescription>{v2Messages.description}</CardDescription>
      </CardHeader>
      <CardContent className="stack-md">
        {!hasContent ? (
          <p className="text-muted">{v2Messages.empty}</p>
        ) : null}
        {decision ? (
          <div className="stack-sm">
            <span className="eyebrow">{v2Messages.decisionSnapshot}</span>
            <div className="report-v2-summary">
              <div className="report-v2-stat">
                <span className="eyebrow">{v2Messages.labels.verdict}</span>
                <Badge variant={resolveDecisionVariant(decision.verdict)}>
                  {decision.verdict ?? "-"}
                </Badge>
              </div>
              <div className="report-v2-stat">
                <span className="eyebrow">{v2Messages.labels.score}</span>
                <span className="report-v2-stat__value">
                  {formatScore(decision.totalScore)}
                </span>
              </div>
              <div className="report-v2-stat">
                <span className="eyebrow">{v2Messages.labels.confidence}</span>
                <span className="report-v2-stat__value">
                  {decision.confidence ?? "-"}
                </span>
              </div>
            </div>
            {decision.rationale ? <p>{decision.rationale}</p> : null}
            {decision.nextAction ? (
              <p className="text-muted">
                {v2Messages.labels.nextAction}: {decision.nextAction}
              </p>
            ) : null}
            {decision.topFindings.length || decision.topGaps.length ? (
              <div className="report-score-stack">
                <div className="stack-sm">
                  <span className="eyebrow">{v2Messages.labels.topFindings}</span>
                  {decision.topFindings.length ? (
                    <ul>
                      {decision.topFindings.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-muted">-</p>
                  )}
                </div>
                <div className="stack-sm">
                  <span className="eyebrow">{v2Messages.labels.topGaps}</span>
                  {decision.topGaps.length ? (
                    <ul>
                      {decision.topGaps.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-muted">-</p>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

        {rationaleEntries.length ? (
          <div className="stack-sm">
            <span className="eyebrow">{v2Messages.scoreRationales}</span>
            <div className="report-score-stack">
              {rationaleEntries.map(({ key, label, detail }) =>
                detail ? (
                  <div key={key} className="stack-sm">
                    <div className="cluster-tight">
                      <Badge variant="outline">{label}</Badge>
                      <span className="text-muted">
                        {v2Messages.labels.score}: {formatScore(detail.score)}
                      </span>
                    </div>
                    {detail.rationale ? <p>{detail.rationale}</p> : null}
                    {detail.evidenceGaps.length ? (
                      <p className="text-muted">
                        {v2Messages.labels.evidenceGaps}:{" "}
                        {detail.evidenceGaps.join("; ")}
                      </p>
                    ) : null}
                  </div>
                ) : null
              )}
            </div>
          </div>
        ) : null}

        {report.riskRegister.length ? (
          <div className="stack-sm">
            <span className="eyebrow">{v2Messages.riskRegister}</span>
            <div className="report-v2-list">
              {report.riskRegister.slice(0, 5).map((item) => (
                <div
                  className="report-v2-row"
                  key={`${item.category}-${item.risk}`}
                >
                  <div className="report-v2-row__header">
                    <strong>{item.risk}</strong>
                    <span className="text-muted">
                      {item.severity}/{item.likelihood} / {item.category}
                    </span>
                  </div>
                  {item.earlyWarningSignal ? (
                    <p className="text-muted">
                      {v2Messages.labels.earlyWarning}:{" "}
                      {item.earlyWarningSignal}
                    </p>
                  ) : null}
                  {item.mitigationSuggestion ? (
                    <p className="text-muted">
                      {v2Messages.labels.mitigation}:{" "}
                      {item.mitigationSuggestion}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {report.experimentPlan.length ? (
          <div className="stack-sm">
            <span className="eyebrow">{v2Messages.experimentPlan}</span>
            <div className="report-v2-list">
              {report.experimentPlan.slice(0, 5).map((item) => (
                <div
                  className="report-v2-row"
                  key={`${item.priority}-${item.action}`}
                >
                  <div className="report-v2-row__header">
                    <strong>{item.action}</strong>
                    <span className="text-muted">
                      {item.priority}
                      {item.timeHorizon ? ` / ${item.timeHorizon}` : ""}
                    </span>
                  </div>
                  {item.successSignal ? (
                    <p className="text-muted">
                      {v2Messages.labels.successSignal}: {item.successSignal}
                    </p>
                  ) : null}
                  {item.linkedRisk ? (
                    <p className="text-muted">
                      {v2Messages.labels.linkedRisk}: {item.linkedRisk}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {evidenceCounts.length || evidenceItems.length ? (
          <div className="stack-sm">
            <span className="eyebrow">{v2Messages.evidenceIndex}</span>
            {evidenceCounts.length ? (
              <div className="cluster-tight text-muted">
                {evidenceCounts.map(([key, value]) => (
                  <span key={key}>
                    {key}: {value}
                  </span>
                ))}
              </div>
            ) : null}
            {evidenceItems.length ? (
              <div className="report-v2-list">
                {evidenceItems.map((item, index) => (
                  <div
                    className="report-v2-row report-v2-row--compact"
                    key={`${item.path ?? item.label ?? "evidence"}-${index}`}
                  >
                    {[item.stage, item.layer, item.label ?? item.path]
                      .filter(Boolean)
                      .join(" / ")}
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
