type AdminConfigEnv = {
  NEXT_PUBLIC_ADMIN_ENABLED?: string;
  NODE_ENV?: string;
};

const truthyValues = new Set(["1", "true", "yes", "on"]);
const falseyValues = new Set(["0", "false", "no", "off", ""]);

export function resolveAdminUiEnabled(env: AdminConfigEnv): boolean {
  const raw = env.NEXT_PUBLIC_ADMIN_ENABLED?.trim().toLowerCase();
  if (env.NODE_ENV === "production") {
    return raw !== undefined && truthyValues.has(raw);
  }
  if (raw === undefined) {
    return true;
  }
  return !falseyValues.has(raw);
}

export const adminUiEnabled = resolveAdminUiEnabled(process.env);
