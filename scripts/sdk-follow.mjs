// Decide whether the CLI must follow a newer @weftlabs/sdk release.
// Prints GitHub Actions outputs. The workflow opens a pull request.
// It does not push to main and it does not create a tag.
import { spawnSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const plain = /^(\d+)\.(\d+)\.(\d+)$/;

const parse = (v) => {
  const match = plain.exec(v);
  if (!match) throw new Error(`Not a plain semver version: ${v}`);
  return match.slice(1).map(Number);
};

const compare = (a, b) => {
  const [left, right] = [parse(a), parse(b)];
  for (let i = 0; i < 3; i += 1) {
    if (left[i] !== right[i]) return left[i] - right[i];
  }
  return 0;
};

// A major change is breaking. A minor change is breaking only while the SDK
// is still 0.x. That matches the caret range the CLI already uses.
export function isBreakingSdkLine(current, latest) {
  const [currentMajor, currentMinor] = parse(current);
  const [latestMajor, latestMinor] = parse(latest);
  if (latestMajor !== currentMajor) return true;
  return currentMajor === 0 && latestMinor !== currentMinor;
}

export function assertCandidateTagFree({ cli, tagExists }) {
  if (tagExists) {
    throw new Error(
      `Tag v${cli} already exists. Refusing to open a bump pull request for that version.`,
    );
  }
}

// The current package.json version is already tagged, but npm does not have
// it. Dispatch release.yml again. The publish script skips identical bytes.
export function recovery({ cliVersion, tagExists, npmHasVersion }) {
  if (!plain.test(cliVersion)) {
    throw new Error(`Not a plain semver version: ${cliVersion}`);
  }
  if (tagExists && !npmHasVersion) {
    return { recover: true, tag: `v${cliVersion}` };
  }
  return { recover: false };
}

// The CLI shares the SDK version. If the CLI is already at or past it (a
// CLI-only release happened), take the next CLI patch instead. A release
// younger than pnpm's minimumReleaseAge waits for a later run.
export function plan({
  sdkRange,
  cliVersion,
  sdkLatest,
  publishedAt,
  now,
  minAgeMinutes,
}) {
  if (!plain.test(sdkLatest)) {
    if (/^\d+\.\d+\.\d+[-+]/.test(sdkLatest)) {
      throw new Error(
        `Operator action: @weftlabs/sdk latest is a prerelease (${sdkLatest}). This workflow follows only a plain X.Y.Z latest. Publish a stable release, or move the latest dist-tag off the prerelease. The hourly job stays red until latest is a plain version.`,
      );
    }
    throw new Error(`Not a plain semver version: ${sdkLatest}`);
  }
  const sdkCurrent = sdkRange.replace(/^\^/, "");
  if (compare(sdkLatest, sdkCurrent) <= 0) return { changed: false };
  if (now - publishedAt < minAgeMinutes * 60_000) {
    return { changed: false, waiting: sdkLatest };
  }
  const [major, minor, patch] = parse(cliVersion);
  const cli =
    compare(sdkLatest, cliVersion) > 0
      ? sdkLatest
      : `${major}.${minor}.${patch + 1}`;
  return {
    changed: true,
    sdk: sdkLatest,
    cli,
    breaking: isBreakingSdkLine(sdkCurrent, sdkLatest),
  };
}

function gitTagExists(version) {
  const result = spawnSync(
    "git",
    ["ls-remote", "--exit-code", "--tags", "origin", `refs/tags/v${version}`],
    { encoding: "utf8" },
  );
  if (result.status === 0) return true;
  if (result.status === 2) return false;
  throw new Error(
    `git ls-remote failed (${result.status}): ${result.stderr || result.stdout}`,
  );
}

async function npmHasVersion(name, version) {
  const response = await fetch(
    `https://registry.npmjs.org/${encodeURIComponent(name)}/${version}`,
    {
      signal: AbortSignal.timeout(30_000),
      headers: { "cache-control": "no-cache" },
    },
  );
  if (response.status === 404) return false;
  if (!response.ok) {
    throw new Error(
      `npm registry returned ${response.status} for ${name}@${version}`,
    );
  }
  return true;
}

function printOutputs(result) {
  for (const [key, value] of Object.entries(result)) {
    console.log(`${key}=${value}`);
  }
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(resolve(process.argv[1])).href
) {
  const manifest = JSON.parse(await readFile("package.json", "utf8"));
  if (process.argv[2] === "recovery") {
    const result = recovery({
      cliVersion: manifest.version,
      tagExists: gitTagExists(manifest.version),
      npmHasVersion: await npmHasVersion("@weftlabs/cli", manifest.version),
    });
    console.log(`recover=${result.recover}`);
    if (result.tag) console.log(`recover_tag=${result.tag}`);
  } else {
    const workspace = await readFile("pnpm-workspace.yaml", "utf8");
    const minAge = /^minimumReleaseAge:\s*(\d+)/m.exec(workspace);
    const response = await fetch("https://registry.npmjs.org/@weftlabs%2fsdk", {
      signal: AbortSignal.timeout(30_000),
      headers: { "cache-control": "no-cache" },
    });
    if (!response.ok) {
      throw new Error(`npm registry returned ${response.status}`);
    }
    const packument = await response.json();
    const latest = packument["dist-tags"].latest;
    const result = plan({
      sdkRange: manifest.dependencies["@weftlabs/sdk"],
      cliVersion: manifest.version,
      sdkLatest: latest,
      publishedAt: Date.parse(packument.time[latest]),
      now: Date.now(),
      minAgeMinutes: minAge ? Number(minAge[1]) : 0,
    });
    if (result.changed) {
      assertCandidateTagFree({
        cli: result.cli,
        tagExists: gitTagExists(result.cli),
      });
    }
    printOutputs(result);
  }
}
