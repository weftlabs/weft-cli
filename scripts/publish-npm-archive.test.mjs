import assert from "node:assert/strict";
import { test } from "node:test";
import { publishArchive } from "./publish-npm-archive.mjs";

const pkg = () => ({
  archive: "cli.tgz",
  integrity: "sha512-cli",
  manifest: {
    name: "@weftlabs/cli",
    version: "0.29.0",
    dependencies: { "@weftlabs/sdk": "^0.29.0" },
  },
});

function registry({
  existing = false,
  mismatch = false,
  absent = false,
  error = false,
} = {}) {
  const published = [];
  return {
    published,
    publish: async (archive) => published.push(archive),
    get: async (path) => {
      if (error) throw new Error("registry unavailable");
      if (!path.includes("/")) return absent ? null : {};
      return existing || published.includes("cli.tgz")
        ? { dist: { integrity: mismatch ? "different" : "sha512-cli" } }
        : null;
    },
  };
}

test("publishes the tested archive and checks registry integrity", async () => {
  const api = registry();
  await publishArchive(pkg(), "v0.29.0", api);
  assert.deepEqual(api.published, ["cli.tgz"]);
});

test("recovery skips an existing version with identical bytes", async () => {
  const api = registry({ existing: true });
  await publishArchive(pkg(), "v0.29.0", api);
  assert.deepEqual(api.published, []);
});

test("waits for registry propagation without submitting another publish", async () => {
  const api = registry();
  const get = api.get;
  const reads = new Map();
  const waits = [];
  api.wait = async (ms) => waits.push(ms);
  api.get = async (path) => {
    if (path.includes("/")) {
      reads.set(path, (reads.get(path) ?? 0) + 1);
      if (reads.get(path) < 4) return null;
    }
    return get(path);
  };
  await publishArchive(pkg(), "v0.29.0", api);
  assert.deepEqual(api.published, ["cli.tgz"]);
  assert.equal(waits.length, 2);
});

test("stops after bounded readback when the published package stays absent", async () => {
  const api = registry();
  const waits = [];
  api.wait = async (ms) => waits.push(ms);
  api.get = async (path) => (path.includes("/") ? null : {});
  await assert.rejects(
    publishArchive(pkg(), "v0.29.0", api),
    /not visible on the registry yet/,
  );
  assert.deepEqual(api.published, ["cli.tgz"]);
  assert.equal(waits.length, 29);
});

for (const [label, options] of [
  ["different bytes", { existing: true, mismatch: true }],
  ["missing package bootstrap", { absent: true }],
  ["registry outage", { error: true }],
]) {
  test(`refuses publication on ${label}`, async () => {
    const api = registry(options);
    await assert.rejects(publishArchive(pkg(), "v0.29.0", api));
    assert.deepEqual(api.published, []);
  });
}

test("rejects a tag mismatch or a dependency outside the public range", async () => {
  const api = registry();
  await assert.rejects(publishArchive(pkg(), "v0.28.1", api));
  const workspace = pkg();
  workspace.manifest.dependencies = { "@weftlabs/sdk": "workspace:*" };
  await assert.rejects(publishArchive(workspace, "v0.29.0", api));
  const fileLink = pkg();
  fileLink.manifest.dependencies = { "@weftlabs/sdk": "file:../sdk" };
  await assert.rejects(publishArchive(fileLink, "v0.29.0", api));
  const renamed = pkg();
  renamed.manifest.dependencies = { "@weft-labs/sdk": "^0.29.0" };
  await assert.rejects(publishArchive(renamed, "v0.29.0", api));
  assert.deepEqual(api.published, []);
});
