import {
  ContextCardSummary,
  ValidationPlanList,
} from "@/features/diagnosis/diagnosis-panels";
import type {
  ContextCard,
  ValidationPlanItem,
} from "@/features/diagnosis/diagnosis-types";
import type { AppMessages } from "@/lib/i18n/messages";

type LiveContextMessages = AppMessages["liveContext"];

type DiagnosisViewProps = {
  contextCard: ContextCard | null | undefined;
  validationPlan: ValidationPlanItem[];
  messages: LiveContextMessages;
};

export function DiagnosisView({
  contextCard,
  validationPlan,
  messages,
}: DiagnosisViewProps) {
  return (
    <div className="context-panel__section">
      <div className="context-panel__section-header">
        <p className="sidebar-label">{messages.diagnosis.title}</p>
      </div>
      <p className="context-panel__meta">{messages.diagnosis.description}</p>
      <div className="context-panel__sections">
        <section className="context-panel__section">
          <ContextCardSummary
            card={contextCard}
            messages={messages.diagnosis}
          />
        </section>
        <section className="context-panel__section">
          <div className="context-panel__section-header">
            <p className="sidebar-label">
              {messages.diagnosis.validationPlanTitle}
            </p>
          </div>
          <ValidationPlanList
            plan={validationPlan}
            messages={messages.diagnosis}
          />
        </section>
      </div>
    </div>
  );
}
