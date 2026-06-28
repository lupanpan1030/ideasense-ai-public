import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadTsModule } from "./helpers/load-ts-module.mjs";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const pendingModulePath = path.join(
  frontendRoot,
  "features",
  "context",
  "pending-confirm.ts"
);
const apiClientPath = path.join(frontendRoot, "lib", "api", "client.ts");

const {
  flattenPendingConfirm,
  findPendingConfirmOverrides,
  getPendingConfirmErrorDetails,
  shouldRequirePendingOverrideConfirmation,
} = loadTsModule(pendingModulePath);
const { ApiError } = loadTsModule(apiClientPath);

test("flattenPendingConfirm sorts by priority and created_at", () => {
  const pending = {
    beta: {
      value: "B",
      priority: 1,
      created_at: "2024-04-03T10:00:00Z",
    },
    alpha: {
      value: "A",
      priority: 2,
      created_at: "2024-04-04T10:00:00Z",
    },
    gamma: { value: "C", created_at: "2024-04-05T10:00:00Z" },
    epsilon: { value: "E", created_at: "2024-03-01T10:00:00Z" },
    delta: "D",
  };

  const items = flattenPendingConfirm(pending);

  assert.deepEqual(
    items.map((item) => item.path),
    ["beta", "alpha", "gamma", "epsilon", "delta"]
  );
  assert.equal(items[0].priority, 1);
  assert.equal(items[0].value, "B");
});

test("getPendingConfirmErrorDetails maps 409 conflicts for UI", () => {
  const error = new ApiError({
    status: 409,
    message: "Context updated",
    url: "/api/v1/projects/123/context/pending/resolve",
  });

  const details = getPendingConfirmErrorDetails(error);

  assert.equal(details.type, "conflict");
  assert.equal(details.message, "Context updated, please refresh.");
});

test("findPendingConfirmOverrides compares meta suggested values", () => {
  const pending = {
    target_user: {
      value: "designers",
      source: "model_inferred",
      created_at: "2024-03-01T10:00:00Z",
    },
  };
  const mergedSame = { target_user: "designers" };
  const mergedDifferent = { target_user: "engineers" };

  assert.deepEqual(
    findPendingConfirmOverrides(pending, mergedSame, ["target_user"]),
    []
  );
  assert.deepEqual(
    findPendingConfirmOverrides(pending, mergedDifferent, ["target_user"]),
    ["target_user"]
  );
});

test("shouldRequirePendingOverrideConfirmation skips when acknowledged", () => {
  assert.equal(
    shouldRequirePendingOverrideConfirmation(
      "accept",
      ["target_user"],
      { overridesAcknowledged: true }
    ),
    false
  );
});
