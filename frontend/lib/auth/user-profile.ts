export type UserProfile = {
  label: string;
  email: string | null;
  initials: string;
};

type UserProfileSource = {
  displayName?: string | null;
  name?: string | null;
  email?: string | null;
};

const normalizeString = (value: string | null | undefined): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const buildInitials = (name: string | null, email: string | null): string => {
  const source = (name || "").trim() || (email || "").split("@")[0] || "";
  const normalized = source
    .replace(/[^a-zA-Z0-9]+/g, " ")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (normalized.length === 0) {
    return "U";
  }
  if (normalized.length === 1) {
    const chars = Array.from(normalized[0]);
    if (chars.length === 1) {
      return chars[0].toUpperCase();
    }
    return `${chars[0]}${chars[1]}`.toUpperCase();
  }
  return `${normalized[0][0]}${normalized[1][0]}`.toUpperCase();
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

const parseTokenPayload = (
  token: string | null
): Record<string, unknown> | null => {
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
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
};

export const getUserProfile = ({
  displayName,
  name,
  email,
}: UserProfileSource): UserProfile => {
  const normalizedDisplayName = normalizeString(displayName);
  const normalizedName = normalizeString(name);
  const normalizedEmail = normalizeString(email);
  const label =
    normalizedDisplayName || normalizedName || normalizedEmail || "User";
  return {
    label,
    email: normalizedEmail,
    initials: buildInitials(
      normalizedDisplayName || normalizedName,
      normalizedEmail
    ),
  };
};

export const getUserProfileFromToken = (token: string | null): UserProfile => {
  const payload = parseTokenPayload(token);
  return getUserProfile({
    email: typeof payload?.email === "string" ? payload.email : null,
    displayName:
      typeof payload?.display_name === "string" ? payload.display_name : null,
    name: typeof payload?.name === "string" ? payload.name : null,
  });
};
