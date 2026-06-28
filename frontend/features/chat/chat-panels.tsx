"use client";

/* eslint-disable react-hooks/set-state-in-effect */

import { useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";
import { ResizableSplitView } from "@/components/layout/resizable-split-view";
import { LiveContextBoard } from "@/features/context/live-context-board";
import { useShellLayout } from "@/components/layout/shell-layout-context";
import { fetchProjectDetail } from "@/features/projects/project-detail";
import { subscribeToChatControl } from "@/features/chat/control-channel";
import { useAppLocale } from "@/lib/i18n/provider";
import { ChatThread } from "./chat-thread";
import { resolveWorkflowSteps } from "../../content/workflow-steps";

type ChatPanelsProps = {
  projectId: string;
};

export function ChatPanels({ projectId }: ChatPanelsProps) {
  const locale = useAppLocale();
  const [latestMessageAt, setLatestMessageAt] = useState<string | null>(null);
  const [currentStage, setCurrentStage] = useState<string | null>(null);
  const [stageStatus, setStageStatus] = useState<string | null>(null);
  const { setSummaryVisible } = useShellLayout();
  const workflowSteps = useMemo(
    () => resolveWorkflowSteps(locale),
    [locale]
  );

  useEffect(() => {
    setLatestMessageAt(null);
  }, [projectId]);

  const refreshStage = useCallback(
    (signal?: AbortSignal) => {
      fetchProjectDetail(projectId, { signal })
        .then((snapshot) => {
          if (signal?.aborted) {
            return;
          }
          setCurrentStage(snapshot.currentStage);
          setStageStatus(snapshot.stageStatus);
        })
        .catch(() => {
          if (signal?.aborted) {
            return;
          }
          setCurrentStage(null);
          setStageStatus(null);
        });
    },
    [projectId]
  );

  useEffect(() => {
    const controller = new AbortController();
    refreshStage(controller.signal);
    return () => controller.abort();
  }, [refreshStage]);

  useEffect(() => {
    return subscribeToChatControl((payload) => {
      if (payload.project_id && payload.project_id !== projectId) {
        return;
      }
      const type =
        typeof payload.type === "string" ? payload.type.trim().toLowerCase() : "";
      if (type === "stage_confirmed") {
        refreshStage();
      }
    });
  }, [projectId, refreshStage]);

  const activeStage = useMemo(
    () => currentStage?.toLowerCase() ?? null,
    [currentStage]
  );
  const activeIndex = useMemo(
    () => workflowSteps.findIndex((step) => step.key === activeStage),
    [activeStage, workflowSteps]
  );
  const progress = useMemo(() => {
    if (activeIndex < 0 || workflowSteps.length < 2) {
      return 0;
    }
    return (activeIndex / (workflowSteps.length - 1)) * 100;
  }, [activeIndex, workflowSteps]);
  const frameStyle = useMemo(
    () => ({ "--frame-progress": `${progress}%` }) as CSSProperties,
    [progress]
  );
  const frameOverlay = (
    <div className="workflow-frame" aria-hidden="true">
      <span className="workflow-frame__progress" />
      <span className="workflow-frame__sweep" />
    </div>
  );

  const centerPanel = (
    <div className="chat-surface">
      <ChatThread
        projectId={projectId}
        currentStage={currentStage}
        stageStatus={stageStatus}
        onLatestMessageAt={setLatestMessageAt}
      />
    </div>
  );

  const rightPanel = (
    <LiveContextBoard projectId={projectId} lastMessageAt={latestMessageAt} />
  );
  const layoutClassName = "resizable-split-view--chat";

  useEffect(() => {
    setSummaryVisible(true);
    return () => {
      setSummaryVisible(false);
    };
  }, [setSummaryVisible]);

  return (
    <ResizableSplitView
      className={layoutClassName}
      center={centerPanel}
      right={rightPanel}
      overlay={frameOverlay}
      style={frameStyle}
      dataStage={activeStage ?? "unknown"}
      initialCenterRatio={0.6}
      minCenterRatio={0.35}
      maxCenterRatio={0.75}
    />
  );
}
