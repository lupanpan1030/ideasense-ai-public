"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { RefObject } from "react";
import { subscribeToChatControl } from "@/features/chat/control-channel";
import {
  fetchStageSummaries,
  fetchStageVerification,
  refreshStageVerification,
  type ProjectVerificationSnapshot,
  type StageConfirmResult,
  type StageSummarySnapshot,
} from "@/features/assessments/api";
import {
  fetchProjectDetail,
  ProjectDetailSnapshot,
} from "@/features/projects/project-detail";
import {
  handleChatControlRefresh,
  resolvePollBackoffMs,
  shouldRunPollRefresh,
  shouldRefreshContext,
} from "./context-refresh";
import {
  fetchPendingConfirm,
  findPendingConfirmOverrides,
  flattenPendingConfirm,
  PendingConfirmSnapshot,
  resolvePendingConfirm,
  updatePendingConfirm,
} from "./pending-confirm";
import { fetchProjectContext, ProjectContextSnapshot } from "./project-context";
import {
  StageGateSnapshot,
  useStageGateState,
} from "./use-stage-gate-state";

const POLL_INTERVAL_MS = 12000;
const REFRESH_RESOURCES = [
  "context",
  "pending",
  "projectDetail",
  "summaries",
  "verification",
] as const;

type RefreshResource = (typeof REFRESH_RESOURCES)[number];

type LiveContextBoardState = {
  context: ProjectContextSnapshot | null;
  pendingConfirm: PendingConfirmSnapshot | null;
  projectDetail: ProjectDetailSnapshot | null;
  stageSummaries: StageSummarySnapshot[];
  stageVerification: ProjectVerificationSnapshot | null;
  errorMessage: string | null;
  pendingErrorMessage: string | null;
  stageSummariesError: string | null;
  stageVerificationError: string | null;
  isLoading: boolean;
  isPendingLoading: boolean;
  isSummariesLoading: boolean;
  isVerificationLoading: boolean;
  stageGateState: StageGateSnapshot | null;
  activeStageGate: StageGateSnapshot | null;
  pendingItems: ReturnType<typeof flattenPendingConfirm>;
  pendingOverridePaths: string[];
  showPendingOverrideHint: boolean;
  stageGateStageLabel: string | null;
  stageGateNextLabel: string;
  stageGateUpdatedLabel: string | null;
  pendingPanelRef: RefObject<HTMLDivElement | null>;
  handleStageGateOpen: () => void;
  handleStageGateClose: () => void;
  handleStageGateConfirmed: (result?: StageConfirmResult) => Promise<void>;
  resolvePending: (payload: {
    acceptPaths: string[];
    rejectPaths: string[];
  }) => Promise<void>;
  updatePendingValue: (path: string, value: unknown) => Promise<void>;
  refreshPendingPanelForce: () => Promise<void>;
  refreshStageVerificationData: () => Promise<void>;
  requestStageVerificationRefresh: (stage?: string) => Promise<void>;
  handlePendingEditState: (editing: boolean) => void;
  handleReviewPending: () => void;
};

export function useLiveContextBoardState({
  projectId,
}: {
  projectId: string;
}): LiveContextBoardState {
  const [context, setContext] = useState<ProjectContextSnapshot | null>(null);
  const [projectDetail, setProjectDetail] =
    useState<ProjectDetailSnapshot | null>(null);
  const [pendingConfirm, setPendingConfirm] =
    useState<PendingConfirmSnapshot | null>(null);
  const [stageSummaries, setStageSummaries] = useState<StageSummarySnapshot[]>(
    []
  );
  const [stageVerification, setStageVerification] =
    useState<ProjectVerificationSnapshot | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [pendingErrorMessage, setPendingErrorMessage] = useState<string | null>(
    null
  );
  const [stageSummariesError, setStageSummariesError] = useState<string | null>(
    null
  );
  const [stageVerificationError, setStageVerificationError] = useState<string | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);
  const [isPendingLoading, setIsPendingLoading] = useState(true);
  const [isSummariesLoading, setIsSummariesLoading] = useState(true);
  const [isVerificationLoading, setIsVerificationLoading] = useState(true);
  const contextVersionRef = useRef<number | null>(null);
  const contextStageRef = useRef<string | null>(null);
  const contextUpdatedAtRef = useRef<string | null>(null);
  const latestContextVersionRef = useRef<number | null>(null);
  const pendingRefreshRef = useRef<number | null>(null);
  const pendingPanelRef = useRef<HTMLDivElement | null>(null);
  const pendingEditingRef = useRef(false);
  const inFlightRef = useRef<Record<RefreshResource, boolean>>({
    context: false,
    pending: false,
    projectDetail: false,
    summaries: false,
    verification: false,
  });
  const failureCountRef = useRef<Record<RefreshResource, number>>({
    context: 0,
    pending: 0,
    projectDetail: 0,
    summaries: 0,
    verification: 0,
  });
  const nextRetryAtRef = useRef<Record<RefreshResource, number>>({
    context: 0,
    pending: 0,
    projectDetail: 0,
    summaries: 0,
    verification: 0,
  });

  const beginRefresh = useCallback(
    (
      resource: RefreshResource,
      options: { poll?: boolean; force?: boolean } = {}
    ) => {
      if (inFlightRef.current[resource]) {
        return false;
      }
      if (options.poll && !options.force) {
        const isDocumentHidden =
          typeof document !== "undefined" ? document.hidden : false;
        if (
          !shouldRunPollRefresh({
            isDocumentHidden,
            inFlight: false,
            now: Date.now(),
            nextRetryAt: nextRetryAtRef.current[resource],
          })
        ) {
          return false;
        }
      }
      inFlightRef.current[resource] = true;
      return true;
    },
    []
  );

  const finishRefresh = useCallback(
    (
      resource: RefreshResource,
      outcome: "success" | "failure" | "aborted"
    ) => {
      inFlightRef.current[resource] = false;
      if (outcome === "success") {
        failureCountRef.current[resource] = 0;
        nextRetryAtRef.current[resource] = 0;
        return;
      }
      if (outcome === "failure") {
        const nextFailureCount = failureCountRef.current[resource] + 1;
        failureCountRef.current[resource] = nextFailureCount;
        nextRetryAtRef.current[resource] =
          Date.now() + resolvePollBackoffMs(nextFailureCount);
      }
    },
    []
  );

  useEffect(() => {
    contextVersionRef.current = null;
    contextStageRef.current = null;
    contextUpdatedAtRef.current = null;
    latestContextVersionRef.current = null;
    pendingEditingRef.current = false;
    for (const resource of REFRESH_RESOURCES) {
      inFlightRef.current[resource] = false;
      failureCountRef.current[resource] = 0;
      nextRetryAtRef.current[resource] = 0;
    }
    if (pendingRefreshRef.current) {
      window.clearTimeout(pendingRefreshRef.current);
      pendingRefreshRef.current = null;
    }
    setContext(null);
    setProjectDetail(null);
    setPendingConfirm(null);
    setStageSummaries([]);
    setStageVerification(null);
    setErrorMessage(null);
    setPendingErrorMessage(null);
    setStageSummariesError(null);
    setStageVerificationError(null);
    setIsLoading(true);
    setIsPendingLoading(true);
    setIsSummariesLoading(true);
    setIsVerificationLoading(true);
  }, [projectId]);

  useEffect(() => {
    return () => {
      if (pendingRefreshRef.current) {
        window.clearTimeout(pendingRefreshRef.current);
        pendingRefreshRef.current = null;
      }
    };
  }, []);

  const applyContextSnapshot = useCallback(
    (snapshot: ProjectContextSnapshot) => {
      const versionChanged = shouldRefreshContext(
        contextVersionRef.current,
        snapshot.contextVersion
      );
      const stageChanged = contextStageRef.current !== snapshot.stage;
      const updatedChanged = contextUpdatedAtRef.current !== snapshot.updatedAt;
      if (!versionChanged && !stageChanged && !updatedChanged) {
        return false;
      }
      contextVersionRef.current = snapshot.contextVersion;
      contextStageRef.current = snapshot.stage;
      contextUpdatedAtRef.current = snapshot.updatedAt;
      setContext(snapshot);
      return true;
    },
    []
  );

  const refreshContext = useCallback(
    async (
      signal?: AbortSignal,
      options: { poll?: boolean; force?: boolean } = {}
    ) => {
      if (!beginRefresh("context", options)) {
        return;
      }
      try {
        const snapshot = await fetchProjectContext(projectId, { signal });
        const didUpdate = applyContextSnapshot(snapshot);
        if (didUpdate) {
          setErrorMessage(null);
        }
        finishRefresh("context", "success");
      } catch {
        if (signal?.aborted) {
          finishRefresh("context", "aborted");
          return;
        }
        finishRefresh("context", "failure");
        setErrorMessage("Context service unavailable.");
      } finally {
        setIsLoading((prev) => (prev ? false : prev));
      }
    },
    [projectId, applyContextSnapshot, beginRefresh, finishRefresh]
  );

  const refreshPendingConfirm = useCallback(
    async (
      options: { signal?: AbortSignal; force?: boolean; poll?: boolean } = {}
    ) => {
      if (pendingEditingRef.current && !options.force) {
        return;
      }
      if (!beginRefresh("pending", options)) {
        return;
      }
      try {
        const snapshot = await fetchPendingConfirm(projectId, {
          signal: options.signal,
        });
        setPendingConfirm(snapshot);
        setPendingErrorMessage(null);
        finishRefresh("pending", "success");
      } catch {
        if (options.signal?.aborted) {
          finishRefresh("pending", "aborted");
          return;
        }
        finishRefresh("pending", "failure");
        setPendingErrorMessage("Pending confirm service unavailable.");
      } finally {
        setIsPendingLoading((prev) => (prev ? false : prev));
      }
    },
    [projectId, beginRefresh, finishRefresh]
  );

  const refreshProjectDetail = useCallback(
    async (
      signal?: AbortSignal,
      options: { poll?: boolean; force?: boolean } = {}
    ) => {
      if (!beginRefresh("projectDetail", options)) {
        return;
      }
      try {
        const snapshot = await fetchProjectDetail(projectId, { signal });
        setProjectDetail(snapshot);
        finishRefresh("projectDetail", "success");
      } catch {
        if (signal?.aborted) {
          finishRefresh("projectDetail", "aborted");
          return;
        }
        finishRefresh("projectDetail", "failure");
      }
    },
    [projectId, beginRefresh, finishRefresh]
  );

  const refreshStageSummaries = useCallback(
    async (
      signal?: AbortSignal,
      options: { poll?: boolean; force?: boolean } = {}
    ) => {
      if (!beginRefresh("summaries", options)) {
        return;
      }
      try {
        const summaries = await fetchStageSummaries(projectId, { signal });
        setStageSummaries(summaries);
        setStageSummariesError(null);
        finishRefresh("summaries", "success");
      } catch {
        if (signal?.aborted) {
          finishRefresh("summaries", "aborted");
          return;
        }
        finishRefresh("summaries", "failure");
        setStageSummariesError("Stage summary service unavailable.");
      } finally {
        setIsSummariesLoading((prev) => (prev ? false : prev));
      }
    },
    [projectId, beginRefresh, finishRefresh]
  );

  const refreshStageVerificationData = useCallback(
    async (
      signal?: AbortSignal,
      options: { poll?: boolean; force?: boolean } = {}
    ) => {
      if (!beginRefresh("verification", options)) {
        return;
      }
      setIsVerificationLoading(true);
      try {
        const snapshot = await fetchStageVerification(projectId, { signal });
        setStageVerification(snapshot);
        setStageVerificationError(null);
        finishRefresh("verification", "success");
      } catch {
        if (signal?.aborted) {
          finishRefresh("verification", "aborted");
          return;
        }
        finishRefresh("verification", "failure");
        setStageVerificationError("Verification service unavailable.");
      } finally {
        setIsVerificationLoading(false);
      }
    },
    [projectId, beginRefresh, finishRefresh]
  );

  const requestStageVerificationRefresh = useCallback(
    async (stage?: string) => {
      try {
        await refreshStageVerification(projectId, { stage });
        setStageVerificationError(null);
      } catch {
        setStageVerificationError("Verification refresh failed.");
      }
    },
    [projectId]
  );

  const refreshStageGateDependencies = useCallback(async () => {
    await Promise.all([
      refreshContext(),
      refreshPendingConfirm(),
      refreshProjectDetail(),
      refreshStageSummaries(),
      refreshStageVerificationData(),
    ]);
  }, [
    refreshContext,
    refreshPendingConfirm,
    refreshProjectDetail,
    refreshStageSummaries,
    refreshStageVerificationData,
  ]);

  const refreshPendingPanel = useCallback(
    async (options: { force?: boolean } = {}) => {
      await Promise.all([
        refreshContext(),
        refreshPendingConfirm({ force: options.force }),
        refreshStageSummaries(),
        refreshStageVerificationData(),
      ]);
    },
    [refreshContext, refreshPendingConfirm, refreshStageSummaries, refreshStageVerificationData]
  );

  const refreshPendingPanelForce = useCallback(async () => {
    await refreshPendingPanel({ force: true });
  }, [refreshPendingPanel]);

  const schedulePanelRefresh = useCallback(() => {
    if (pendingRefreshRef.current) {
      window.clearTimeout(pendingRefreshRef.current);
    }
    pendingRefreshRef.current = window.setTimeout(() => {
      void refreshPendingPanel();
    }, 300);
  }, [refreshPendingPanel]);

  useEffect(() => {
    const controller = new AbortController();
    void refreshContext(controller.signal);
    void refreshPendingConfirm({ signal: controller.signal });
    void refreshProjectDetail(controller.signal);
    void refreshStageSummaries(controller.signal);
    void refreshStageVerificationData(controller.signal);
    const intervalId = window.setInterval(() => {
      void refreshContext(controller.signal, { poll: true });
      void refreshPendingConfirm({ signal: controller.signal, poll: true });
      void refreshProjectDetail(controller.signal, { poll: true });
      void refreshStageSummaries(controller.signal, { poll: true });
      void refreshStageVerificationData(controller.signal, { poll: true });
    }, POLL_INTERVAL_MS);

    return () => {
      controller.abort();
      window.clearInterval(intervalId);
    };
  }, [
    projectId,
    refreshContext,
    refreshPendingConfirm,
    refreshProjectDetail,
    refreshStageSummaries,
    refreshStageVerificationData,
  ]);

  useEffect(() => {
    return subscribeToChatControl((payload) => {
      handleChatControlRefresh({
        payload,
        projectId,
        currentVersion: contextVersionRef.current,
        onRefresh: schedulePanelRefresh,
        onUpdateLatestVersion: (version) => {
          latestContextVersionRef.current = version;
        },
      });
    });
  }, [projectId, schedulePanelRefresh]);
  const {
    stageGateState,
    activeStageGate,
    stageGateStageLabel,
    stageGateNextLabel,
    stageGateUpdatedLabel,
    handleStageGateOpen,
    handleStageGateClose,
    handleStageGateConfirmed,
  } = useStageGateState({
    projectId,
    context,
    projectDetail,
    latestContextVersionRef,
    refreshProjectDetail,
    refreshStageGateDependencies,
    refreshPendingConfirm,
    schedulePanelRefresh,
  });

  const resolvePending = useCallback(
    async (payload: { acceptPaths: string[]; rejectPaths: string[] }) => {
      const clientContextVersion =
        latestContextVersionRef.current ?? pendingConfirm?.contextVersion ?? 0;
      const snapshot = await resolvePendingConfirm(projectId, {
        acceptPaths: payload.acceptPaths,
        rejectPaths: payload.rejectPaths,
        clientContextVersion,
      });
      setPendingConfirm(snapshot);
      setPendingErrorMessage(null);
      latestContextVersionRef.current = snapshot.contextVersion;
      if (payload.acceptPaths.length > 0) {
        await refreshContext();
      }
    },
    [pendingConfirm?.contextVersion, projectId, refreshContext]
  );

  const pendingItems = useMemo(
    () => flattenPendingConfirm(pendingConfirm?.pendingConfirm ?? {}),
    [pendingConfirm]
  );

  const pendingOverridePaths = useMemo(() => {
    if (!pendingItems.length || !pendingConfirm || !context?.dataRaw) {
      return [];
    }
    return findPendingConfirmOverrides(
      pendingConfirm.pendingConfirm ?? {},
      context.dataRaw,
      pendingItems.map((item) => item.path)
    );
  }, [context?.dataRaw, pendingConfirm, pendingItems]);

  const handleReviewPending = useCallback(() => {
    const element = pendingPanelRef.current;
    if (!element) {
      return;
    }
    element.scrollIntoView({ behavior: "smooth", block: "center" });
    element.focus();
  }, []);

  const showPendingOverrideHint = pendingOverridePaths.length > 0;

  const handlePendingEditState = useCallback((editing: boolean) => {
    pendingEditingRef.current = editing;
  }, []);

  const updatePendingValue = useCallback(
    async (path: string, value: unknown) => {
      const isUserUpdate =
        typeof value === "object" &&
        value !== null &&
        "source" in value &&
        (value as { source?: unknown }).source === "user";
      const clientContextVersion =
        latestContextVersionRef.current ?? pendingConfirm?.contextVersion ?? 0;
      const snapshot = await updatePendingConfirm(projectId, {
        updates: { [path]: value },
        clientContextVersion,
      });
      setPendingConfirm(snapshot);
      setPendingErrorMessage(null);
      latestContextVersionRef.current = snapshot.contextVersion;
      if (isUserUpdate) {
        await refreshContext();
      }
    },
    [pendingConfirm?.contextVersion, projectId, refreshContext]
  );

  return {
    context,
    pendingConfirm,
    projectDetail,
    stageSummaries,
    stageVerification,
    errorMessage,
    pendingErrorMessage,
    stageSummariesError,
    stageVerificationError,
    isLoading,
    isPendingLoading,
    isSummariesLoading,
    isVerificationLoading,
    stageGateState,
    activeStageGate,
    pendingItems,
    pendingOverridePaths,
    showPendingOverrideHint,
    stageGateStageLabel,
    stageGateNextLabel,
    stageGateUpdatedLabel,
    pendingPanelRef,
    handleStageGateOpen,
    handleStageGateClose,
    handleStageGateConfirmed,
    resolvePending,
    updatePendingValue,
    refreshPendingPanelForce,
    refreshStageVerificationData: () => refreshStageVerificationData(),
    requestStageVerificationRefresh,
    handlePendingEditState,
    handleReviewPending,
  };
}
