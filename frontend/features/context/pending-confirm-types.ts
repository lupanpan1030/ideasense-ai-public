export type PendingConfirmSnapshot = {
  projectId: string;
  pendingConfirm: Record<string, unknown>;
  updatedAt: string;
  contextVersion: number;
};

export type PendingConfirmItem = {
  path: string;
  value: unknown;
  source: string | null;
  createdAt: string | null;
  priority: number | null;
  currentValue: unknown;
};

export type PendingConfirmResolveOptions = {
  overridesAcknowledged?: boolean;
};

export type PendingConfirmErrorDetails = {
  type: "conflict" | "error";
  message: string;
};
