type TokenPayload = {
  exp?: number;
};

const decodeBase64 = (value: string): string | null => {
  if (typeof atob === "function") {
    return atob(value);
  }
  if (typeof Buffer !== "undefined") {
    return Buffer.from(value, "base64").toString("utf-8");
  }
  return null;
};

const parseTokenPayload = (token: string | null): TokenPayload | null => {
  if (!token) {
    return null;
  }
  const parts = token.split(".");
  if (parts.length < 2) {
    return null;
  }
  const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
  const padded = payload.padEnd(Math.ceil(payload.length / 4) * 4, "=");
  try {
    const json = decodeBase64(padded);
    if (!json) {
      return null;
    }
    return JSON.parse(json) as TokenPayload;
  } catch {
    return null;
  }
};

export const isTokenExpired = (token: string | null): boolean => {
  const payload = parseTokenPayload(token);
  if (!payload) {
    return true;
  }
  const exp = payload.exp;
  if (typeof exp !== "number") {
    return true;
  }
  const now = Date.now() / 1000;
  return exp <= now;
};

export const isTokenUsable = (token: string | null): boolean =>
  Boolean(token) && !isTokenExpired(token);
