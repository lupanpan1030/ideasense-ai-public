"use client";

import type { ComponentProps, RefObject } from "react";
import { StageGateModal } from "@/features/assessments/components/StageGateModal";
import { DiagnosisView } from "./live-context-diagnosis-view";
import { LiveDraftView } from "./live-context-draft-view";
import { StageInsightView } from "./live-context-insight-view";
import { PendingConfirmPanel } from "./pending-confirm-panel";
import {
  LiveContextBoardHeader,
  LiveContextReviewCta,
  LiveContextReviewPanel,
} from "./live-context-review-panels";
import type { ViewMode } from "./live-context-formatters";

type LiveContextBoardSurfaceProps = {
  stageSummariesNotice: string | null;
  panelNotice: string | null;
  isReviewing: boolean;
  isReviewHighlight: boolean;
  contextPanelRef: RefObject<HTMLDivElement | null>;
  contextBodyRef: RefObject<HTMLDivElement | null>;
  headerProps: ComponentProps<typeof LiveContextBoardHeader>;
  viewMode: ViewMode;
  reviewCtaProps: ComponentProps<typeof LiveContextReviewCta>;
  reviewPanelProps: ComponentProps<typeof LiveContextReviewPanel>;
  draftViewProps: ComponentProps<typeof LiveDraftView>;
  diagnosisViewProps: ComponentProps<typeof DiagnosisView>;
  insightViewProps: ComponentProps<typeof StageInsightView>;
  showPendingPanel: boolean;
  pendingPanelRef: RefObject<HTMLDivElement | null>;
  pendingPanelProps: ComponentProps<typeof PendingConfirmPanel>;
  reportModalProps: ComponentProps<typeof StageGateModal> | null;
};

export function LiveContextBoardSurface({
  stageSummariesNotice,
  panelNotice,
  isReviewing,
  isReviewHighlight,
  contextPanelRef,
  contextBodyRef,
  headerProps,
  viewMode,
  reviewCtaProps,
  reviewPanelProps,
  draftViewProps,
  diagnosisViewProps,
  insightViewProps,
  showPendingPanel,
  pendingPanelRef,
  pendingPanelProps,
  reportModalProps,
}: LiveContextBoardSurfaceProps) {
  return (
    <div className="workspace-panel workspace-panel--summary">
      {stageSummariesNotice ? (
        <div className="context-panel__notice">{stageSummariesNotice}</div>
      ) : null}

      <div
        className={[
          "context-panel",
          isReviewing ? "context-panel--review" : "",
          isReviewHighlight ? "context-panel--highlight" : "",
        ]
          .filter(Boolean)
          .join(" ")}
        ref={contextPanelRef}
      >
        <LiveContextBoardHeader {...headerProps} />

        <div className="context-panel__body" ref={contextBodyRef}>
          {panelNotice ? (
            <div className="context-panel__notice">{panelNotice}</div>
          ) : null}

          {isReviewing ? <LiveContextReviewCta {...reviewCtaProps} /> : null}

          <div className="context-panel__stack">
            {viewMode === "draft" ? (
              <>
                {isReviewing ? (
                  <LiveContextReviewPanel {...reviewPanelProps} />
                ) : null}
                <LiveDraftView {...draftViewProps} />
              </>
            ) : viewMode === "diagnosis" ? (
              <DiagnosisView {...diagnosisViewProps} />
            ) : (
              <StageInsightView {...insightViewProps} />
            )}

            {showPendingPanel ? (
              <div
                ref={pendingPanelRef}
                tabIndex={-1}
                className="context-panel__section"
              >
                <PendingConfirmPanel {...pendingPanelProps} />
              </div>
            ) : null}
          </div>
        </div>
      </div>

      {reportModalProps ? <StageGateModal {...reportModalProps} /> : null}
    </div>
  );
}
