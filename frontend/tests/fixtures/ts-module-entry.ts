import { aliasValue } from "@/tests/fixtures/ts-module-alias";
import { helperValue } from "./ts-module-helper";

export const loaded = aliasValue === "alias-ok" && helperValue === 42;
