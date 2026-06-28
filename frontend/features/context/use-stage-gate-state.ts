"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MutableRefObject } from "react";
import {
  StageGateSignal,
  subscribeToStageGate,
} from "@/features/assessments/stage-gate-channel";
import type { StageConfirmResult } from "@/features/assessments/api";
import { emitChatControl } from "@/features/chat/control-channel";
import {
  formatUpdatedAt,
  NEXT_STAGE_MAP,
  STAGE_LABELS,
} from "@/features/assessments/components/stage-gate-utils";
import { ProjectDetailSnapshot } from "@/features/projects/project-detail";
import { ProjectContextSnapshot } from "./project-context";

export type StageGateSnapshot = {
  stage: string;
  nextStage: string | null;
  contextVersion: number | null;
  contextUpdatedAt: string | null;
};

type UseStageGateStateArgs = {
  projectId: string;
  context: ProjectContextSnapshot | null;
  projectDetail: ProjectDetailSnapshot | null;
  latestContextVersionRef: MutableRefObject<number | null>;
  refreshProjectDetail: () => Promise<void>;
  refreshStageGateDependencies: () => Promise<void>;
  refreshPendingConfirm: () => Promise<void>;
  schedulePanelRefresh: () => void;
};

const normalizeStageStatus = (
  value: string | null | undefined
): string | null => {
  if (!value) {
    return null;
  }
  const trimmed = value.trim().toLowerCase();
  return trimmed ? trimmed : null;
};

const resolveLatestContextVersion = (
  ...candidates: Array<number | null | undefined>
): number | null => {
  const values = candidates.filter(
    (value): value is number => typeof value === "number" && Number.isFinite(value)
  );
  if (!values.length) {
    return null;
  }
  return Math.max(...values);
};

const resolveContextUpdatedAt = ({
  resolvedContextVersion,
  stageGateSignal,
  context,
  projectDetail,
}: {
  resolvedContextVersion: number | null;
  stageGateSignal: StageGateSignal | null;
  context: ProjectContextSnapshot | null;
  projectDetail: ProjectDetailSnapshot | null;
}): string | null => {
  if (resolvedContextVersion !== null) {
    if (context?.contextVersion === resolvedContextVersion) {
      return (
        context.updatedAt ??
        stageGateSignal?.contextUpdatedAt ??
        projectDetail?.updatedAt ??
        null
      );
    }
    if (stageGateSignal?.contextVersion === resolvedContextVersion) {
      return (
        stageGateSignal.contextUpdatedAt ??
        context?.updatedAt ??
        projectDetail?.updatedAt ??
        null
      );
    }
  }
  return (
    stageGateSignal?.contextUpdatedAt ??
    context?.updatedAt ??
    projectDetail?.updatedAt ??
    null
  );
};

export function useStageGateState({
  projectId,
  context,
  projectDetail,
  latestContextVersionRef,
  refreshProjectDetail,
  refreshStageGateDependencies,
  refreshPendingConfirm,
  schedulePanelRefresh,
}: UseStageGateStateArgs) {
  const [stageGateSignal, setStageGateSignal] = useState<StageGateSignal | null>(
    null
  );
  const [activeStageGate, setActiveStageGate] =
    useState<StageGateSnapshot | null>(null);
  const stageGateAutoOpenRef = useRef<string | null>(null);

  useEffect(() => {
    setStageGateSignal(null);
    setActiveStageGate(null);
    stageGateAutoOpenRef.current = null;
  }, [projectId]);

  useEffect(() => {
    return subscribeToStageGate((payload) => {
      if (payload.projectId && payload.projectId !== projectId) {
        return;
      }
      setStageGateSignal(payload);
      void refreshProjectDetail();
      if (payload.contextVersion !== null) {
        latestContextVersionRef.current = payload.contextVersion;
      }
      schedulePanelRefresh();
    });
  }, [projectId, refreshProjectDetail, schedulePanelRefresh, latestContextVersionRef]);

  const stageGateState = useMemo<StageGateSnapshot | null>(() => {
    const projectStatus = normalizeStageStatus(projectDetail?.stageStatus);
    const isAwaitingConfirm = projectStatus === "awaiting_confirm";
    const resolvedContextVersion = resolveLatestContextVersion(
      stageGateSignal?.contextVersion,
      latestContextVersionRef.current,
      context?.contextVersion
    );
    const resolvedContextUpdatedAt = resolveContextUpdatedAt({
      resolvedContextVersion,
      stageGateSignal,
      context,
      projectDetail,
    });

    if (stageGateSignal) {
      const signalStatus = normalizeStageStatus(stageGateSignal.stageStatus);
      if (signalStatus && signalStatus !== "awaiting_confirm") {
        return null;
      }
      if (!signalStatus && !isAwaitingConfirm) {
        return null;
      }
      const stage =
        stageGateSignal.stage ??
        context?.stage ??
        projectDetail?.currentStage ??
        null;
      if (!stage) {
        return null;
      }
      const stageKey = stage.toLowerCase();
      return {
        stage,
        nextStage:
          stageGateSignal.nextStage ?? (NEXT_STAGE_MAP[stageKey] ?? null),
        contextVersion: resolvedContextVersion,
        contextUpdatedAt: resolvedContextUpdatedAt,
      };
    }

    if (!isAwaitingConfirm) {
      return null;
    }

    const stage = context?.stage ?? projectDetail?.currentStage ?? null;
    if (!stage) {
      return null;
    }

    const stageKey = stage.toLowerCase();
    return {
      stage,
      nextStage: NEXT_STAGE_MAP[stageKey] ?? null,
      contextVersion: resolvedContextVersion,
      contextUpdatedAt: resolvedContextUpdatedAt,
    };
  }, [stageGateSignal, context, projectDetail, latestContextVersionRef]);

  useEffect(() => {
    if (!stageGateSignal) {
      stageGateAutoOpenRef.current = null;
      return;
    }
    if (activeStageGate || !stageGateState) {
      return;
    }
    if (!stageGateSignal.open) {
      return;
    }
    const key = `${stageGateSignal.stage ?? "unknown"}:${
      stageGateSignal.contextVersion ?? "unknown"
    }`;
    if (stageGateAutoOpenRef.current === key) {
      return;
    }
    stageGateAutoOpenRef.current = key;
    setActiveStageGate(stageGateState);
  }, [activeStageGate, stageGateSignal, stageGateState]);

  useEffect(() => {
    if (!activeStageGate || !stageGateState) {
      return;
    }
    if (
      activeStageGate.contextVersion !== stageGateState.contextVersion ||
      activeStageGate.contextUpdatedAt !== stageGateState.contextUpdatedAt ||
      activeStageGate.stage !== stageGateState.stage
    ) {
      setActiveStageGate(stageGateState);
    }
  }, [activeStageGate, stageGateState]);

  const stageGateStageLabel = useMemo(() => {
    if (!stageGateState) {
      return null;
    }
    const key = stageGateState.stage.toLowerCase();
    return STAGE_LABELS[key] ?? stageGateState.stage;
  }, [stageGateState]);

  const stageGateNextLabel = useMemo(() => {
    if (!stageGateState?.nextStage) {
      return "Next stage";
    }
    const key = stageGateState.nextStage.toLowerCase();
    return STAGE_LABELS[key] ?? stageGateState.nextStage;
  }, [stageGateState]);

  const stageGateUpdatedLabel = useMemo(() => {
    return stageGateState
      ? formatUpdatedAt(stageGateState.contextUpdatedAt)
      : null;
  }, [stageGateState]);

  const handleStageGateOpen = useCallback(() => {
    if (stageGateState) {
      setActiveStageGate(stageGateState);
    }
  }, [stageGateState]);

  const handleStageGateClose = useCallback(() => {
    setActiveStageGate(null);
  }, []);

  const handleStageGateConfirmed = useCallback(async (result?: StageConfirmResult) => {
    try {
      await refreshStageGateDependencies();
    } finally {
      await refreshPendingConfirm();
      setStageGateSignal(null);
      emitChatControl({
        type: "stage_confirmed",
        project_id: projectId,
        next_stage: result?.nextStage ?? stageGateState?.nextStage ?? undefined,
        stage_status: result?.stageStatus ?? undefined,
        context_version: stageGateState?.contextVersion ?? undefined,
        report_job_status: result?.reportJobStatus ?? undefined,
      });
    }
  }, [
    projectId,
    refreshPendingConfirm,
    refreshStageGateDependencies,
    stageGateState,
  ]);

  return {
    stageGateState,
    activeStageGate,
    stageGateStageLabel,
    stageGateNextLabel,
    stageGateUpdatedLabel,
    handleStageGateOpen,
    handleStageGateClose,
    handleStageGateConfirmed,
  };
}
