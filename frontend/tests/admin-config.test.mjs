import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadTsModule } from "./helpers/load-ts-module.mjs";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const adminConfigModulePath = path.join(frontendRoot, "lib", "admin-config.ts");
const platformSettingsModulePath = path.join(
  frontendRoot,
  "features",
  "admin",
  "platform-settings.ts"
);
const adminGuardModulePath = path.join(
  frontendRoot,
  "features",
  "admin",
  "admin-guard.tsx"
);
const adminRouteConfigModulePath = path.join(
  frontendRoot,
  "features",
  "admin",
  "admin-route-config.ts"
);
const clientModulePath = path.join(frontendRoot, "lib", "api", "client.ts");

const { resolveAdminUiEnabled } = loadTsModule(adminConfigModulePath);
const { getPlatformSettingsErrorMessage } = loadTsModule(platformSettingsModulePath);
const { resolveAdminGuardErrorMessage } = loadTsModule(adminGuardModulePath);
const {
  ADMIN_NAV_ITEMS,
  canAccessAdminNavItem,
  findAdminRouteRule,
  getAdminNavItem,
  getVisibleAdminNavGroups,
  hasAdminRouteAccess,
  isAdminNavItemActive,
} = loadTsModule(adminRouteConfigModulePath);
const { ApiError } = loadTsModule(clientModulePath);

test("admin UI defaults off in production", () => {
  assert.equal(resolveAdminUiEnabled({ NODE_ENV: "production" }), false);
});

test("admin UI requires explicit enable in production", () => {
  assert.equal(
    resolveAdminUiEnabled({
      NODE_ENV: "production",
      NEXT_PUBLIC_ADMIN_ENABLED: "1",
    }),
    true
  );
});

test("admin UI remains enabled by default outside production", () => {
  assert.equal(resolveAdminUiEnabled({ NODE_ENV: "development" }), true);
});

test("admin UI can be disabled outside production", () => {
  assert.equal(
    resolveAdminUiEnabled({
      NODE_ENV: "development",
      NEXT_PUBLIC_ADMIN_ENABLED: "0",
    }),
    false
  );
});

test("platform settings errors use provided localized fallbacks", () => {
  const messages = {
    accessDenied: "没有权限。",
    default: "无法更新平台设置。",
    sessionExpired: "登录过期。",
    unavailable: "服务不可用。",
  };

  assert.equal(
    getPlatformSettingsErrorMessage(
      new ApiError({ status: 400, message: "Backend validation detail." }),
      messages
    ),
    messages.default
  );
  assert.equal(
    getPlatformSettingsErrorMessage(new Error("Unexpected token }"), messages),
    messages.default
  );
  assert.equal(
    getPlatformSettingsErrorMessage(
      new ApiError({ status: 401, message: "Unauthorized." }),
      messages
    ),
    messages.sessionExpired
  );
  assert.equal(
    getPlatformSettingsErrorMessage(
      new ApiError({ status: 403, message: "Forbidden." }),
      messages
    ),
    messages.accessDenied
  );
  assert.equal(
    getPlatformSettingsErrorMessage(
      new ApiError({ status: 503, message: "Service unavailable." }),
      messages
    ),
    messages.unavailable
  );
});

test("admin guard errors use provided localized fallbacks", () => {
  const messages = {
    errors: {
      denied: "没有权限。",
      loadFailed: "无法加载管理会话。",
      unauthorized: "未登录。",
      unavailable: "管理服务不可用。",
    },
  };

  assert.equal(
    resolveAdminGuardErrorMessage(
      new ApiError({ status: 400, message: "Backend validation detail." }),
      messages
    ),
    messages.errors.loadFailed
  );
  assert.equal(
    resolveAdminGuardErrorMessage(new Error("Failed to fetch"), messages),
    messages.errors.loadFailed
  );
  assert.equal(
    resolveAdminGuardErrorMessage(
      new ApiError({ status: 401, message: "Unauthorized." }),
      messages
    ),
    messages.errors.unauthorized
  );
  assert.equal(
    resolveAdminGuardErrorMessage(
      new ApiError({ status: 403, message: "Forbidden." }),
      messages
    ),
    messages.errors.denied
  );
  assert.equal(
    resolveAdminGuardErrorMessage(
      new ApiError({ status: 503, message: "Service unavailable." }),
      messages
    ),
    messages.errors.unavailable
  );
});

test("admin guard route access follows route capabilities", () => {
  const baseSession = {
    capabilities: {
      is_org_admin: true,
      can_manage_org_settings: true,
      can_manage_prompts: false,
      can_manage_members: true,
      can_manage_invites: false,
      can_manage_cohorts: true,
      can_manage_assignments: false,
      can_manage_projects: true,
      can_manage_reports: false,
      can_manage_question_bank: true,
      can_transfer_ownership: false,
    },
    is_platform_admin: false,
  };

  assert.equal(hasAdminRouteAccess("/en/admin", baseSession), true);
  assert.equal(hasAdminRouteAccess("/zh/admin/org", baseSession), true);
  assert.equal(
    hasAdminRouteAccess("/en/admin/org/question-banks", baseSession),
    true
  );
  assert.equal(
    hasAdminRouteAccess("/en/admin/org/prompts", baseSession),
    false
  );
  assert.equal(
    hasAdminRouteAccess("/en/admin/org/unknown", baseSession),
    false
  );
  assert.equal(
    hasAdminRouteAccess("/en/admin/cohorts/22222222-2222-4222-8222-222222222222", baseSession),
    true
  );
  assert.equal(
    hasAdminRouteAccess("/en/admin/projects/project-1", baseSession),
    true
  );
  assert.equal(
    hasAdminRouteAccess("/en/admin/org/prompts", baseSession),
    false
  );
  assert.equal(
    hasAdminRouteAccess("/en/admin/org/invites", baseSession),
    false
  );
  assert.equal(hasAdminRouteAccess("/en/admin/reports", baseSession), false);
  assert.equal(
    hasAdminRouteAccess("/zh/admin/assignments", baseSession),
    false
  );
  assert.equal(
    hasAdminRouteAccess("/zh/admin/memberships", baseSession),
    true
  );
  assert.equal(
    hasAdminRouteAccess("/en/admin/platform/settings", baseSession),
    false
  );
  assert.equal(
    hasAdminRouteAccess("/en/admin/platform/settings", {
      ...baseSession,
      is_platform_admin: true,
    }),
    true
  );
});

test("admin route matching uses the most specific rule", () => {
  const promptsRule = findAdminRouteRule("/en/admin/org/prompts");
  assert.equal(promptsRule?.prefix, "/admin/org/prompts");

  const orgRule = findAdminRouteRule("/en/admin/org");
  assert.equal(orgRule?.prefix, "/admin/org");
});

test("admin nav visibility stays aligned with route access", () => {
  const session = {
    capabilities: {
      is_org_admin: true,
      can_manage_org_settings: true,
      can_manage_prompts: false,
      can_manage_members: true,
      can_manage_invites: true,
      can_manage_cohorts: true,
      can_manage_assignments: false,
      can_manage_projects: true,
      can_manage_reports: true,
      can_manage_question_bank: true,
      can_transfer_ownership: false,
    },
    is_platform_admin: false,
  };

  for (const item of ADMIN_NAV_ITEMS) {
    const canSee = canAccessAdminNavItem(item, session);
    const canOpen = hasAdminRouteAccess(`/en${item.href}`, session);
    assert.equal(canOpen, canSee, item.key);
  }
});

test("admin nav groups reflect the intended admin information architecture", () => {
  const session = {
    capabilities: {
      is_org_admin: true,
      can_manage_org_settings: true,
      can_manage_prompts: true,
      can_manage_members: true,
      can_manage_invites: true,
      can_manage_cohorts: true,
      can_manage_assignments: true,
      can_manage_projects: true,
      can_manage_reports: true,
      can_manage_question_bank: true,
      can_transfer_ownership: true,
    },
    is_platform_admin: true,
  };

  const groups = getVisibleAdminNavGroups(session).map((group) => ({
    key: group.key,
    items: group.items.map((item) => item.key),
  }));

  assert.deepEqual(groups, [
    { key: "overview", items: ["overview"] },
    { key: "organization", items: ["organization", "members", "invites"] },
    {
      key: "assessmentOps",
      items: ["cohorts", "mentorAssignments", "projects", "reports"],
    },
    { key: "methodology", items: ["prompts", "questionBanks"] },
    { key: "platform", items: ["reportQuality", "platformSettings"] },
  ]);
});

test("admin nav active state does not let parent org consume child routes", () => {
  assert.equal(
    isAdminNavItemActive("/admin/org/prompts", getAdminNavItem("organization")),
    false
  );
  assert.equal(
    isAdminNavItemActive("/admin/org/prompts", getAdminNavItem("prompts")),
    true
  );
  assert.equal(
    isAdminNavItemActive(
      "/admin/projects/11111111-1111-4111-8111-111111111111",
      getAdminNavItem("projects")
    ),
    true
  );
});
