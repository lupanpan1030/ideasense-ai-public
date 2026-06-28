type StreamHandlerOptions = {
  appendToken: (delta: string) => void;
  updateStatus?: (label: string | null) => void;
  refreshHistory: () => void;
  markDone?: (payload: unknown) => void;
  reportError?: (payload: unknown) => void;
  onQuestionMeta?: (payload: Record<string, unknown>) => void;
};

type ChatStreamHandlerSet = {
  onToken?: (delta: string) => void;
  onStatus?: (payload: Record<string, unknown>) => void;
  onDone?: (payload: unknown) => void;
  onError?: (payload: unknown) => void;
  onQuestionMeta?: (payload: Record<string, unknown>) => void;
};

export const createChatStreamHandlers = (options: StreamHandlerOptions) => {
  let didReceiveDone = false;

  const handlers: ChatStreamHandlerSet = {
    onToken: (delta) => {
      if (delta) {
        options.updateStatus?.(null);
        options.appendToken(delta);
      }
    },
    onStatus: (payload) => {
      const label = typeof payload.label === "string" ? payload.label.trim() : "";
      options.updateStatus?.(label || null);
    },
    onDone: (payload) => {
      didReceiveDone = true;
      options.updateStatus?.(null);
      options.markDone?.(payload);
      options.refreshHistory();
    },
    onError: (payload) => {
      options.updateStatus?.(null);
      options.reportError?.(payload);
    },
    onQuestionMeta: (payload) => {
      options.onQuestionMeta?.(payload);
    },
  };

  return {
    handlers,
    didReceiveDone: () => didReceiveDone,
  };
};
