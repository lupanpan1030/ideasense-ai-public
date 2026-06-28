import { Badge } from "@/components/ui/badge";
import type {
  ContextCard,
  DiagnosisEntry,
  EvidenceGapEntry,
  ValidationPlanItem,
} from "./diagnosis-types";
import { hasContextCardContent } from "./diagnosis-types";
import type { AppMessages } from "@/lib/i18n/messages";

type DiagnosisMessages = AppMessages["liveContext"]["diagnosis"];

type ContextCardSummaryProps = {
  card: ContextCard | null | undefined;
  messages: DiagnosisMessages;
  emptyLabel?: string;
};

const renderEntryMeta = (
  entry: DiagnosisEntry,
  messages: DiagnosisMessages
) => (
  <div className="cluster-tight text-muted">
    <Badge variant="outline">
      {messages.labels.evidenceLevel}: {entry.evidenceLevel}
    </Badge>
    <Badge variant="secondary">
      {messages.labels.status}: {entry.resolutionStatus}
    </Badge>
    <span>
      {messages.labels.source}: {entry.source}
    </span>
  </div>
);

const EntryList = ({
  entries,
  title,
  messages,
}: {
  entries: DiagnosisEntry[];
  title: string;
  messages: DiagnosisMessages;
}) => (
  <div className="stack-sm">
    <span className="eyebrow">{title}</span>
    {entries.length ? (
      <ul className="context-value__list">
        {entries.map((entry, index) => (
          <li key={`${entry.path ?? entry.label}-${entry.value}-${index}`}>
            <div className="stack-sm">
              <strong>{entry.label}</strong>
              <span>{entry.value}</span>
              {renderEntryMeta(entry, messages)}
              {entry.note ? <span className="text-muted">{entry.note}</span> : null}
            </div>
          </li>
        ))}
      </ul>
    ) : (
      <p className="text-muted">{messages.emptyBucket}</p>
    )}
  </div>
);

const GapList = ({
  entries,
  title,
  messages,
}: {
  entries: EvidenceGapEntry[];
  title: string;
  messages: DiagnosisMessages;
}) => (
  <div className="stack-sm">
    <span className="eyebrow">{title}</span>
    {entries.length ? (
      <ul className="context-value__list">
        {entries.map((entry, index) => (
          <li key={`${entry.path ?? entry.label}-${entry.reason}-${index}`}>
            <div className="stack-sm">
              <strong>{entry.label}</strong>
              <span>{entry.reason}</span>
              <Badge variant="warning">
                {messages.labels.evidenceLevel}: {entry.evidenceLevel}
              </Badge>
            </div>
          </li>
        ))}
      </ul>
    ) : (
      <p className="text-muted">{messages.emptyBucket}</p>
    )}
  </div>
);

export function ContextCardSummary({
  card,
  messages,
  emptyLabel,
}: ContextCardSummaryProps) {
  if (!hasContextCardContent(card)) {
    return <p className="text-muted">{emptyLabel ?? messages.empty}</p>;
  }

  const verification = card?.verificationSummary;
  return (
    <div className="stack-md">
      <EntryList
        entries={card?.userConfirmedInputs ?? []}
        title={messages.buckets.confirmedInputs}
        messages={messages}
      />
      <EntryList
        entries={card?.founderAssumptions ?? []}
        title={messages.buckets.founderAssumptions}
        messages={messages}
      />
      <EntryList
        entries={card?.aiInferences ?? []}
        title={messages.buckets.aiInferences}
        messages={messages}
      />
      <EntryList
        entries={card?.unknowns ?? []}
        title={messages.buckets.unknowns}
        messages={messages}
      />
      <GapList
        entries={card?.evidenceGaps ?? []}
        title={messages.buckets.evidenceGaps}
        messages={messages}
      />
      {verification ? (
        <div className="stack-sm">
          <span className="eyebrow">{messages.labels.verification}</span>
          <div className="cluster-tight text-muted">
            <span>
              {messages.labels.supported}: {verification.supportedClaims}
            </span>
            <span>
              {messages.labels.unsupported}: {verification.unsupportedClaims}
            </span>
            <span>
              {messages.labels.uncertain}: {verification.uncertainClaims}
            </span>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function ValidationPlanList({
  plan,
  messages,
  emptyLabel,
}: {
  plan: ValidationPlanItem[];
  messages: DiagnosisMessages;
  emptyLabel?: string;
}) {
  if (!plan.length) {
    return <p className="text-muted">{emptyLabel ?? messages.noValidationPlan}</p>;
  }

  return (
    <ol className="context-value__list">
      {plan.map((item) => (
        <li key={item.action}>
          <div className="stack-sm">
            <strong>{item.action}</strong>
            <div className="cluster-tight text-muted">
              {item.priority ? (
                <Badge variant="info">
                  {messages.labels.priority}: {item.priority}
                </Badge>
              ) : null}
              {item.target ? (
                <span>
                  {messages.labels.target}: {item.target}
                </span>
              ) : null}
            </div>
            {item.successSignal ? (
              <span>
                {messages.labels.successSignal}: {item.successSignal}
              </span>
            ) : null}
            {item.linkedRisk ? (
              <span className="text-muted">
                {messages.labels.linkedRisk}: {item.linkedRisk}
              </span>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
}
