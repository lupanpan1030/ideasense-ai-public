export const INVITE_TOKEN_STORAGE_KEY = "invite_token";

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export type InviteTokenStorage = {
  getToken: () => string | null;
  setToken: (token: string) => void;
  clearToken: () => void;
};

const resolveStorage = (storage?: StorageLike | null): StorageLike | null => {
  if (storage) {
    return storage;
  }
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.localStorage;
  } catch {
    return null;
  }
};

const normalizeToken = (value: string | null): string | null => {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

export function createInviteTokenStorage(
  storage?: StorageLike | null
): InviteTokenStorage {
  const resolvedStorage = resolveStorage(storage);

  return {
    getToken() {
      if (!resolvedStorage) {
        return null;
      }
      try {
        return normalizeToken(resolvedStorage.getItem(INVITE_TOKEN_STORAGE_KEY));
      } catch {
        return null;
      }
    },
    setToken(token: string) {
      if (!resolvedStorage) {
        return;
      }
      const normalized = normalizeToken(token);
      if (!normalized) {
        return;
      }
      try {
        resolvedStorage.setItem(INVITE_TOKEN_STORAGE_KEY, normalized);
      } catch {
        return;
      }
    },
    clearToken() {
      if (!resolvedStorage) {
        return;
      }
      try {
        resolvedStorage.removeItem(INVITE_TOKEN_STORAGE_KEY);
      } catch {
        return;
      }
    },
  };
}

export const inviteTokenStorage = createInviteTokenStorage();

export const getInviteToken = () => inviteTokenStorage.getToken();
export const setInviteToken = (token: string) =>
  inviteTokenStorage.setToken(token);
export const clearInviteToken = () => inviteTokenStorage.clearToken();
