// Phase 1 auth strategy: store access tokens on the client and mirror them
// into a first-party cookie so the Next proxy can route protected pages.

export const AUTH_TOKEN_STORAGE_KEY = "ideasense.auth.token";
export const AUTH_TOKEN_COOKIE_NAME = "ideasense.auth.token";
const TOKEN_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export type TokenStorage = {
  getToken: () => string | null;
  setToken: (token: string, options?: { persist?: boolean }) => void;
  setTokenPreservingPersistence: (token: string) => void;
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

const resolveSessionStorage = (): StorageLike | null => {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
};

const readCookie = (name: string): string | null => {
  if (typeof document === "undefined") {
    return null;
  }
  const prefix = `${name}=`;
  const parts = document.cookie.split("; ");
  for (const part of parts) {
    if (part.startsWith(prefix)) {
      const value = part.slice(prefix.length);
      return value ? decodeURIComponent(value) : null;
    }
  }
  return null;
};

const setCookie = (
  name: string,
  value: string,
  options: { maxAgeSeconds?: number | null } = {}
) => {
  if (typeof document === "undefined") {
    return;
  }
  const encoded = encodeURIComponent(value);
  const secure =
    typeof window !== "undefined" && window.location.protocol === "https:";
  const maxAge =
    options.maxAgeSeconds === null
      ? ""
      : `; Max-Age=${options.maxAgeSeconds ?? TOKEN_COOKIE_MAX_AGE_SECONDS}`;
  document.cookie = `${name}=${encoded}; Path=/; SameSite=Lax${maxAge}${
    secure ? "; Secure" : ""
  }`;
};

const clearCookie = (name: string) => {
  if (typeof document === "undefined") {
    return;
  }
  const secure =
    typeof window !== "undefined" && window.location.protocol === "https:";
  document.cookie = `${name}=; Path=/; SameSite=Lax; Max-Age=0${
    secure ? "; Secure" : ""
  }`;
};

export function createTokenStorage(storage?: StorageLike | null): TokenStorage {
  const resolvedStorage = resolveStorage(storage);
  const resolvedSessionStorage = resolveSessionStorage();

  const hasSessionToken = () => {
    if (!resolvedSessionStorage) {
      return false;
    }
    try {
      return Boolean(resolvedSessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY));
    } catch {
      return false;
    }
  };

  const hasPersistentToken = () => {
    if (resolvedStorage) {
      try {
        if (resolvedStorage.getItem(AUTH_TOKEN_STORAGE_KEY)) {
          return true;
        }
      } catch {
        // fall through to cookie
      }
    }
    return Boolean(readCookie(AUTH_TOKEN_COOKIE_NAME));
  };

  const getCurrentPersistence = (): "session" | "persistent" | "none" => {
    if (hasSessionToken()) {
      return "session";
    }
    if (hasPersistentToken()) {
      return "persistent";
    }
    return "none";
  };

  const setTokenValue = (token: string, options?: { persist?: boolean }) => {
    const persist = options?.persist !== false;
    if (persist) {
      setCookie(AUTH_TOKEN_COOKIE_NAME, token);
      if (resolvedSessionStorage) {
        try {
          resolvedSessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
        } catch {
          // ignore
        }
      }
      if (!resolvedStorage) {
        return;
      }
      try {
        resolvedStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
      } catch {
        return;
      }
      return;
    }

    setCookie(AUTH_TOKEN_COOKIE_NAME, token, { maxAgeSeconds: null });
    if (resolvedStorage) {
      try {
        resolvedStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
      } catch {
        // ignore
      }
    }
    if (resolvedSessionStorage) {
      try {
        resolvedSessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
      } catch {
        return;
      }
    }
  };

  return {
    getToken() {
      if (resolvedSessionStorage) {
        try {
          const sessionToken = resolvedSessionStorage.getItem(
            AUTH_TOKEN_STORAGE_KEY
          );
          if (sessionToken) {
            return sessionToken;
          }
        } catch {
          // fall through to cookie/local storage
        }
      }
      if (!resolvedStorage) {
        return readCookie(AUTH_TOKEN_COOKIE_NAME);
      }
      try {
        const token = resolvedStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
        return token ?? readCookie(AUTH_TOKEN_COOKIE_NAME);
      } catch {
        return readCookie(AUTH_TOKEN_COOKIE_NAME);
      }
    },
    setToken(token: string, options?: { persist?: boolean }) {
      setTokenValue(token, options);
    },
    setTokenPreservingPersistence(token: string) {
      const persistence = getCurrentPersistence();
      setTokenValue(token, { persist: persistence !== "session" });
    },
    clearToken() {
      clearCookie(AUTH_TOKEN_COOKIE_NAME);
      if (!resolvedStorage) {
        if (resolvedSessionStorage) {
          try {
            resolvedSessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
          } catch {
            return;
          }
        }
        return;
      }
      try {
        resolvedStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
      } catch {
        return;
      }
      if (resolvedSessionStorage) {
        try {
          resolvedSessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
        } catch {
          return;
        }
      }
    },
  };
}

export const tokenStorage = createTokenStorage();

export const getToken = () => tokenStorage.getToken();
export const setToken = (token: string) => tokenStorage.setToken(token);
export const setTokenPreservingPersistence = (token: string) =>
  tokenStorage.setTokenPreservingPersistence(token);
export const clearToken = () => tokenStorage.clearToken();
