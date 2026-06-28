import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ContextCardSummary,
  ValidationPlanList,
} from "@/features/diagnosis/diagnosis-panels";
import { hasContextCardContent } from "@/features/diagnosis/diagnosis-types";
import type { ReportSnapshot } from "./reports-normalize";
import { useAppMessages } from "@/lib/i18n/provider";

type DiagnosisCardProps = {
  report: ReportSnapshot;
  className?: string;
};

export function DiagnosisCard({ report, className = "" }: DiagnosisCardProps) {
  const messages = useAppMessages().reportViewer;
  const diagnosisMessages = messages.diagnosis;
  const cards = Object.entries(report.diagnosis.contextCards).filter(([, card]) =>
    hasContextCardContent(card)
  );

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{diagnosisMessages.title}</CardTitle>
        <CardDescription>{diagnosisMessages.description}</CardDescription>
      </CardHeader>
      <CardContent className="stack-md">
        {report.diagnosis.summary ? (
          <p>{report.diagnosis.summary}</p>
        ) : null}
        {cards.length ? (
          cards.map(([stage, card]) => (
            <details key={stage} className="verification-stage">
              <summary className="verification-stage__summary">
                <span className="eyebrow">
                  {messages.stageLabels[stage] ?? stage}
                </span>
              </summary>
              <ContextCardSummary
                card={card}
                messages={diagnosisMessages}
              />
            </details>
          ))
        ) : (
          <p className="text-muted">{diagnosisMessages.empty}</p>
        )}
      </CardContent>
    </Card>
  );
}

type ValidationPlanCardProps = {
  report: ReportSnapshot;
  className?: string;
};

export function ValidationPlanCard({
  report,
  className = "",
}: ValidationPlanCardProps) {
  const messages = useAppMessages().reportViewer.diagnosis;
  const plan = report.validationPlan.length
    ? report.validationPlan
    : report.diagnosis.nextValidationSteps;
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{messages.validationPlanTitle}</CardTitle>
        <CardDescription>{messages.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <ValidationPlanList plan={plan} messages={messages} />
      </CardContent>
    </Card>
  );
}
