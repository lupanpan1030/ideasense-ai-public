import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { renderMarkdown } from "@/features/assessments/components/stage-gate-utils";
import type { ReportSnapshot } from "./reports-normalize";
import { MermaidDiagram } from "./mermaid-diagram";
import { formatNarrativeMarkdown } from "./report-viewer-helpers";
import { useAppMessages } from "@/lib/i18n/provider";

type KeyRisksCardProps = {
  report: ReportSnapshot;
  className?: string;
};

export function KeyRisksCard({ report, className = "" }: KeyRisksCardProps) {
  const messages = useAppMessages().reportViewer;
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{messages.risks.title}</CardTitle>
        <CardDescription>{messages.risks.description}</CardDescription>
      </CardHeader>
      <CardContent className="stack-sm">
        {report.keyRisks.length ? (
          report.keyRisks.map((risk) => (
            <div key={risk.risk} className="stack-sm">
              <strong>{risk.risk}</strong>
              <div className="cluster-tight text-muted">
                <Badge variant="warning">{risk.severity}</Badge>
                <Badge variant="info">{risk.likelihood}</Badge>
                <Badge>{risk.category}</Badge>
              </div>
              {risk.mitigationSuggestion ? (
                <p className="text-muted">
                  {messages.risks.mitigationPrefix}: {risk.mitigationSuggestion}
                </p>
              ) : null}
            </div>
          ))
        ) : (
          <p className="text-muted">{messages.risks.empty}</p>
        )}
      </CardContent>
    </Card>
  );
}

type ArchitectureDiagramCardProps = {
  report: ReportSnapshot;
  className?: string;
  showSource?: boolean;
};

export function ArchitectureDiagramCard({
  report,
  className = "",
  showSource = true,
}: ArchitectureDiagramCardProps) {
  const messages = useAppMessages().reportViewer;
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{messages.architecture.title}</CardTitle>
        <CardDescription>{messages.architecture.description}</CardDescription>
      </CardHeader>
      <CardContent>
        {report.architectureDiagram?.code ? (
          <div className="stack-sm">
            <MermaidDiagram code={report.architectureDiagram.code} />
            {showSource ? (
              <details className="report-details">
                <summary>{messages.architecture.mermaidSource}</summary>
                <pre className="text-muted">{report.architectureDiagram.code}</pre>
              </details>
            ) : null}
          </div>
        ) : (
          <p className="text-muted">{messages.architecture.empty}</p>
        )}
      </CardContent>
    </Card>
  );
}

type OverallSummaryCardProps = {
  report: ReportSnapshot;
  className?: string;
};

export function OverallSummaryCard({
  report,
  className = "",
}: OverallSummaryCardProps) {
  const messages = useAppMessages().reportViewer;
  const summary = report.overallSummary?.trim() ?? "";
  if (!summary) {
    return null;
  }
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{messages.overallSummary.title}</CardTitle>
        <CardDescription>{messages.overallSummary.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div
          className="markdown-preview"
          dangerouslySetInnerHTML={{
            __html: renderMarkdown(formatNarrativeMarkdown(summary)),
          }}
        />
      </CardContent>
    </Card>
  );
}
