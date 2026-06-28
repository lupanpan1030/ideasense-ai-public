export const CURRENT_ORG_STORAGE_KEY = "ideasense.org.current";

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export type OrgStorage = {
  getOrgId: () => string | null;
  setOrgId: (orgId: string) => void;
  clearOrgId: () => void;
};

const resolveStorage = (storage?: StorageLike | null): StorageLike | null => {
  if (storage) {
    return storage;
  }
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
};

const normalizeOrgId = (value: string | null): string | null => {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

export function createOrgStorage(storage?: StorageLike | null): OrgStorage {
  const resolvedStorage = resolveStorage(storage);

  return {
    getOrgId() {
      if (!resolvedStorage) {
        return null;
      }
      try {
        return normalizeOrgId(resolvedStorage.getItem(CURRENT_ORG_STORAGE_KEY));
      } catch {
        return null;
      }
    },
    setOrgId(orgId: string) {
      if (!resolvedStorage) {
        return;
      }
      const normalized = normalizeOrgId(orgId);
      if (!normalized) {
        return;
      }
      try {
        resolvedStorage.setItem(CURRENT_ORG_STORAGE_KEY, normalized);
      } catch {
        return;
      }
    },
    clearOrgId() {
      if (!resolvedStorage) {
        return;
      }
      try {
        resolvedStorage.removeItem(CURRENT_ORG_STORAGE_KEY);
      } catch {
        return;
      }
    },
  };
}

export const orgStorage = createOrgStorage();
