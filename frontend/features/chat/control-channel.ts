export type ChatControlPayload = {
  type?: string;
  project_id?: string;
  context_version?: number;
  context_updated_at?: string;
  [key: string]: unknown;
};

type ControlListener = (payload: ChatControlPayload) => void;

const CONTROL_EVENT = "ideasense:chat-control";

export const subscribeToChatControl = (listener: ControlListener): (() => void) => {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  const handler = (event: Event) => {
    const detail = (event as CustomEvent).detail;
    if (detail && typeof detail === "object") {
      listener(detail as ChatControlPayload);
    }
  };

  window.addEventListener(CONTROL_EVENT, handler as EventListener);
  return () => window.removeEventListener(CONTROL_EVENT, handler as EventListener);
};

export const emitChatControl = (payload: ChatControlPayload): void => {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new CustomEvent(CONTROL_EVENT, { detail: payload }));
};
