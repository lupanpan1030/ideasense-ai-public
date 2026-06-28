import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  statSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(frontendRoot, "..");

const frontendNextDir = path.join(frontendRoot, ".next");
const repoNextDir = path.join(repoRoot, ".next");
const frontendNodeModules = path.join(frontendRoot, "node_modules");
const repoNodeModules = path.join(repoRoot, "node_modules");

if (!existsSync(frontendNextDir)) {
  console.warn(
    "[vercel-build] .next was not generated; skipping root manifest mirror."
  );
  process.exit(0);
}

const buildMetadataFiles = new Set();
const nftManifestFiles = new Set();

const isInsideDirectory = (directory, target) => {
  const relative = path.relative(directory, target);
  return (
    Boolean(relative) &&
    !relative.startsWith("..") &&
    !path.isAbsolute(relative)
  );
};

const collectDirectFiles = (directory) => {
  if (!existsSync(directory)) {
    return;
  }

  for (const entry of readdirSync(directory)) {
    const source = path.join(directory, entry);
    if (statSync(source).isFile()) {
      buildMetadataFiles.add(source);
    }
  }
};

const collectRuntimeFiles = (directory) => {
  if (!existsSync(directory)) {
    return;
  }

  for (const entry of readdirSync(directory)) {
    const source = path.join(directory, entry);
    if (statSync(source).isDirectory()) {
      collectRuntimeFiles(source);
      continue;
    }
    buildMetadataFiles.add(source);
  }
};

const collectBuildMetadataFiles = (directory) => {
  for (const entry of readdirSync(directory)) {
    const source = path.join(directory, entry);
    const stats = statSync(source);
    if (stats.isDirectory()) {
      collectBuildMetadataFiles(source);
      continue;
    }
    if (
      entry.includes("manifest") &&
      (entry.endsWith(".json") || entry.endsWith(".js"))
    ) {
      buildMetadataFiles.add(source);
    }
    if (entry.endsWith(".nft.json")) {
      nftManifestFiles.add(source);
      buildMetadataFiles.add(source);
    }
  }
};

const collectTracedNextFiles = (manifestFile) => {
  const manifestDir = path.dirname(manifestFile);
  const trace = JSON.parse(readFileSync(manifestFile, "utf8"));
  for (const file of trace.files ?? []) {
    const source = path.resolve(manifestDir, file);
    if (existsSync(source) && isInsideDirectory(frontendNextDir, source)) {
      buildMetadataFiles.add(source);
    }
  }
};

const copyBuildMetadataFile = (source, target) => {
  mkdirSync(path.dirname(target), { recursive: true });

  if (!source.endsWith(".nft.json")) {
    copyFileSync(source, target);
    return;
  }

  const trace = JSON.parse(readFileSync(source, "utf8"));
  const sourceDir = path.dirname(source);
  const targetDir = path.dirname(target);
  const files = trace.files ?? [];

  trace.files = files.map((file) => {
    const tracedSource = path.resolve(sourceDir, file);
    const shouldPointToFrontendSource =
      isInsideDirectory(frontendRoot, tracedSource) &&
      !isInsideDirectory(frontendNextDir, tracedSource);

    if (!shouldPointToFrontendSource) {
      return file;
    }

    return path.relative(targetDir, tracedSource);
  });

  writeFileSync(target, `${JSON.stringify(trace)}\n`);
};

collectDirectFiles(frontendNextDir);
collectRuntimeFiles(path.join(frontendNextDir, "server"));
collectBuildMetadataFiles(frontendNextDir);

for (const manifestFile of nftManifestFiles) {
  collectTracedNextFiles(manifestFile);
}

if (!existsSync(repoNodeModules) && existsSync(frontendNodeModules)) {
  try {
    symlinkSync(
      path.relative(repoRoot, frontendNodeModules),
      repoNodeModules,
      "dir"
    );
    console.log("[vercel-build] linked root node_modules for Vercel tracing.");
  } catch (error) {
    console.warn(
      `[vercel-build] could not link root node_modules for Vercel tracing: ${error.message}`
    );
  }
}

const requiredServerFilesManifest = path.join(
  frontendNextDir,
  "required-server-files.json"
);
if (existsSync(requiredServerFilesManifest)) {
  buildMetadataFiles.add(requiredServerFilesManifest);
  const requiredServerFiles = JSON.parse(
    readFileSync(requiredServerFilesManifest, "utf8")
  );
  for (const file of requiredServerFiles.files ?? []) {
    if (!file.startsWith(".next/")) {
      continue;
    }
    const source = path.join(frontendRoot, file);
    if (existsSync(source)) {
      buildMetadataFiles.add(source);
    }
  }
}

for (const source of buildMetadataFiles) {
  const relative = path.relative(frontendNextDir, source);
  const target = path.join(repoNextDir, relative);
  copyBuildMetadataFile(source, target);
}

const deterministicTarget = path.join(
  repoNextDir,
  "routes-manifest-deterministic.json"
);
if (!existsSync(deterministicTarget)) {
  const routesManifestSource = path.join(frontendNextDir, "routes-manifest.json");
  if (existsSync(routesManifestSource)) {
    copyFileSync(routesManifestSource, deterministicTarget);
  }
}

console.log(
  `[vercel-build] mirrored ${buildMetadataFiles.size} Next build metadata files for Vercel upload.`
);
