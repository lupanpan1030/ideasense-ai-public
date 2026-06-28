import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadTsModule } from "./helpers/load-ts-module.mjs";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const modulePath = path.join(frontendRoot, "components", "ui", "modal-focus.ts");

const { getModalFocusableElements } = loadTsModule(modulePath);

const makeElement = ({ disabled = false, hidden = false } = {}) => ({
  hasAttribute(name) {
    return name === "disabled" ? disabled : false;
  },
  getAttribute(name) {
    if (name === "aria-hidden") {
      return hidden ? "true" : null;
    }
    return null;
  },
});

test("getModalFocusableElements filters disabled and aria-hidden targets", () => {
  const enabled = makeElement();
  const disabled = makeElement({ disabled: true });
  const hidden = makeElement({ hidden: true });
  const dialog = {
    querySelectorAll() {
      return [enabled, disabled, hidden];
    },
  };

  assert.deepEqual(getModalFocusableElements(dialog), [enabled]);
});
