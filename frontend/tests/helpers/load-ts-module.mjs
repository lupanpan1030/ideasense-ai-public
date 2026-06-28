import { readFileSync } from "node:fs";
import path from "node:path";
import { Module } from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const helperDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(helperDir, "..", "..");

let hookInstalled = false;
let originalResolveFilename = null;

const transpileTs = (source, filename) =>
  ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2017,
      jsx: ts.JsxEmit.ReactJSX,
    },
    fileName: filename,
  }).outputText;

const compileTsModule = (module, filename) => {
  const source = readFileSync(filename, "utf8");
  const outputText = transpileTs(source, filename);
  module._compile(outputText, filename);
};

const resolveAlias = (request) => {
  if (request.startsWith("@/")) {
    return path.join(frontendRoot, request.slice(2));
  }
  return request;
};

const installTsHook = () => {
  if (hookInstalled) {
    return;
  }
  hookInstalled = true;

  Module._extensions[".ts"] = compileTsModule;
  Module._extensions[".tsx"] = compileTsModule;

  originalResolveFilename = Module._resolveFilename;
  Module._resolveFilename = function (request, parent, isMain, options) {
    const mappedRequest = resolveAlias(request);
    return originalResolveFilename.call(
      this,
      mappedRequest,
      parent,
      isMain,
      options
    );
  };
};

export function loadTsModule(modulePath) {
  installTsHook();
  const cached = Module._cache[modulePath];
  if (cached) {
    return cached.exports;
  }
  const source = readFileSync(modulePath, "utf8");
  const outputText = transpileTs(source, modulePath);

  const mod = new Module(modulePath, null);
  mod.filename = modulePath;
  mod.paths = Module._nodeModulePaths(path.dirname(modulePath));
  Module._cache[modulePath] = mod;
  try {
    mod._compile(outputText, modulePath);
  } catch (error) {
    delete Module._cache[modulePath];
    throw error;
  }
  return mod.exports;
}
