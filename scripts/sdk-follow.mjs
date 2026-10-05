// Decide whether the CLI must follow a newer @weftlabs/sdk release.
// Prints GitHub Actions outputs: changed, sdk, cli.
import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const parse = (v) => {
  const m = /^(\d+)\.(\d+)\.(\d+)$/.exec(v);
  if (!m) throw new Error(`Not a plain semver version: ${v}`);
  return m.slice(1).map(Number);
};

const compare = (a, b) => {
  const [x, y] = [parse(a), parse(b)];
  for (let i = 0; i < 3; i += 1) if (x[i] !== y[i]) return x[i] - y[i];
  return 0;
};

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
  return { changed: true, sdk: sdkLatest, cli };
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(resolve(process.argv[1])).href
) {
  const manifest = JSON.parse(await readFile("package.json", "utf8"));
  const workspace = await readFile("pnpm-workspace.yaml", "utf8");
  const minAge = /^minimumReleaseAge:\s*(\d+)/m.exec(workspace);
  const response = await fetch("https://registry.npmjs.org/@weftlabs%2fsdk", {
    signal: AbortSignal.timeout(30_000),
    headers: { "cache-control": "no-cache" },
  });
  if (!response.ok) throw new Error(`npm registry returned ${response.status}`);
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
  for (const [key, value] of Object.entries(result))
    console.log(`${key}=${value}`);
}
