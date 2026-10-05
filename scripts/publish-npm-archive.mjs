// Publish the one tested CLI archive. Fail closed on registry errors or byte
// mismatches. A rerun skips only when the published bytes match.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFile, readdir } from "node:fs/promises";
import { resolve } from "node:path";
import { setTimeout } from "node:timers/promises";
import { pathToFileURL } from "node:url";

const registry = "https://registry.npmjs.org";

async function registryGet(path) {
  const response = await fetch(`${registry}/${path}`, {
    signal: AbortSignal.timeout(30_000),
    headers: { "cache-control": "no-cache" },
  });
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new Error(`npm registry returned ${response.status} for ${path}`);
  }
  return response.json();
}

function assertCliManifest(manifest, tag) {
  assert.equal(manifest.name, "@weftlabs/cli");
  assert.match(manifest.version, /^\d+\.\d+\.\d+$/);
  assert.equal(
    tag,
    `v${manifest.version}`,
    "Release tag must match the tested archive",
  );
  assert.deepEqual(Object.keys(manifest.dependencies ?? {}), ["@weftlabs/sdk"]);
  assert.match(
    manifest.dependencies["@weftlabs/sdk"],
    /^\^\d+\.\d+\.\d+$/,
    "@weftlabs/sdk must be a public semver range",
  );
}

export async function publishArchive(
  pkg,
  tag,
  {
    get = registryGet,
    wait = setTimeout,
    publish = (archive) =>
      execFileSync(
        "npm",
        [
          "publish",
          archive,
          "--provenance",
          "--access",
          "public",
          "--ignore-scripts",
          "--registry",
          registry,
        ],
        { stdio: "inherit" },
      ),
  } = {},
) {
  assertCliManifest(pkg.manifest, tag);
  assert.ok(
    await get(encodeURIComponent(pkg.manifest.name)),
    `${pkg.manifest.name} must be bootstrapped and configured for trusted publishing`,
  );
  const path = `${encodeURIComponent(pkg.manifest.name)}/${pkg.manifest.version}`;
  let existing = await get(path);
  if (!existing) {
    await publish(pkg.archive);
    // npm can briefly return 404 after accepting a publish. Retry only the
    // read; never submit another publish after an uncertain result.
    for (let attempt = 0; attempt < 6; attempt += 1) {
      existing = await get(path);
      if (existing) break;
      if (attempt < 5) await wait(2_000);
    }
  }
  assert.equal(
    existing?.dist?.integrity,
    pkg.integrity,
    `${pkg.manifest.name}@${pkg.manifest.version}: registry bytes differ from the tested archive`,
  );
  console.log(
    `${pkg.manifest.name}@${pkg.manifest.version}: registry integrity verified`,
  );
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(resolve(process.argv[1])).href
) {
  const directory = resolve(process.argv[2]);
  const names = (await readdir(directory)).filter((name) =>
    name.endsWith(".tgz"),
  );
  assert.equal(names.length, 1, "Expected one tested CLI archive");
  const archive = resolve(directory, names[0]);
  const manifest = JSON.parse(
    execFileSync("tar", ["-xOf", archive, "package/package.json"], {
      encoding: "utf8",
    }),
  );
  const integrity = `sha512-${createHash("sha512")
    .update(await readFile(archive))
    .digest("base64")}`;
  await publishArchive(
    { archive, manifest, integrity },
    process.env.GITHUB_REF_NAME,
  );
}
