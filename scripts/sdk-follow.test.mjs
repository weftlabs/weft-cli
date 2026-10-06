import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import {
  assertCandidateTagFree,
  isBreakingSdkLine,
  plan,
  recovery,
} from "./sdk-follow.mjs";

const day = 24 * 60 * 60_000;
const old = { publishedAt: 0, now: 2 * day, minAgeMinutes: 1440 };
const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function workflowJob(file, name) {
  const text = readFileSync(join(root, file), "utf8");
  const start = text.indexOf(`\n  ${name}:\n`);
  assert.notEqual(start, -1, `${name} job missing from ${file}`);
  const rest = text.slice(start + 1);
  const next = rest.slice(1).search(/\n  [a-z0-9-]+:\n/);
  return next === -1 ? rest : rest.slice(0, next + 1);
}

test("does nothing when the SDK has no newer release", () => {
  assert.deepEqual(
    plan({
      sdkRange: "^0.30.0",
      cliVersion: "0.30.0",
      sdkLatest: "0.30.0",
      ...old,
    }),
    { changed: false },
  );
});

test("takes the SDK version when the SDK is ahead", () => {
  assert.deepEqual(
    plan({
      sdkRange: "^0.29.0",
      cliVersion: "0.29.0",
      sdkLatest: "0.30.0",
      ...old,
    }),
    { changed: true, sdk: "0.30.0", cli: "0.30.0", breaking: true },
  );
});

test("waits while the SDK release is younger than minimumReleaseAge", () => {
  assert.deepEqual(
    plan({
      sdkRange: "^0.29.0",
      cliVersion: "0.29.0",
      sdkLatest: "0.30.0",
      publishedAt: 0,
      now: day - 1,
      minAgeMinutes: 1440,
    }),
    { changed: false, waiting: "0.30.0" },
  );
});

test("takes the next CLI patch after a CLI-only release", () => {
  assert.deepEqual(
    plan({
      sdkRange: "^0.30.0",
      cliVersion: "0.30.1",
      sdkLatest: "0.30.1",
      ...old,
    }),
    { changed: true, sdk: "0.30.1", cli: "0.30.2", breaking: false },
  );
});

test("compares versions numerically, not as text", () => {
  assert.equal(
    plan({
      sdkRange: "^0.9.0",
      cliVersion: "0.9.0",
      sdkLatest: "0.10.0",
      ...old,
    }).cli,
    "0.10.0",
  );
});

test("a 0.x minor and a major are breaking; a 1.x minor is not", () => {
  assert.equal(isBreakingSdkLine("0.29.0", "0.30.0"), true);
  assert.equal(isBreakingSdkLine("0.9.0", "1.0.0"), true);
  assert.equal(isBreakingSdkLine("1.2.0", "2.0.0"), true);
  assert.equal(isBreakingSdkLine("0.29.0", "0.29.1"), false);
  assert.equal(isBreakingSdkLine("1.2.0", "1.3.0"), false);
});

test("rejects a prerelease on latest with an operator action", () => {
  assert.throws(
    () =>
      plan({
        sdkRange: "^0.30.0",
        cliVersion: "0.30.0",
        sdkLatest: "0.31.0-rc.1",
        ...old,
      }),
    /Operator action:.*prerelease \(0\.31\.0-rc\.1\).*dist-tag/,
  );
});

test("recovers only when the tag exists and npm does not have the version", () => {
  assert.deepEqual(
    recovery({
      cliVersion: "0.29.0",
      tagExists: true,
      npmHasVersion: false,
    }),
    { recover: true, tag: "v0.29.0" },
  );
  assert.deepEqual(
    recovery({
      cliVersion: "0.29.0",
      tagExists: true,
      npmHasVersion: true,
    }),
    { recover: false },
  );
  assert.deepEqual(
    recovery({
      cliVersion: "0.29.0",
      tagExists: false,
      npmHasVersion: false,
    }),
    { recover: false },
  );
});

test("refuses a bump whose release tag already exists", () => {
  assert.throws(
    () => assertCandidateTagFree({ cli: "0.30.0", tagExists: true }),
    /Tag v0\.30\.0 already exists/,
  );
  assert.doesNotThrow(() =>
    assertCandidateTagFree({ cli: "0.30.0", tagExists: false }),
  );
});

test("the install job is read-only and the pull-request job does not push main", () => {
  const workflow = readFileSync(
    join(root, ".github/workflows/sdk-follow.yml"),
    "utf8",
  );
  const prepare = workflowJob(".github/workflows/sdk-follow.yml", "prepare");
  const openPr = workflowJob(".github/workflows/sdk-follow.yml", "open-pr");
  const recover = workflowJob(".github/workflows/sdk-follow.yml", "recover");

  assert.match(prepare, /contents: read/);
  assert.doesNotMatch(prepare, /actions: write/);
  assert.doesNotMatch(prepare, /contents: write/);
  assert.match(prepare, /pnpm add/);
  assert.match(openPr, /core\.hooksPath=\/dev\/null/);
  assert.match(openPr, /refs\/heads\/\$\{branch\}/);
  assert.doesNotMatch(openPr, /pnpm add|pnpm install|pnpm run/);
  assert.doesNotMatch(openPr, /actions: write/);
  assert.doesNotMatch(workflow, /git push[^\n]*\bmain\b/);
  assert.doesNotMatch(workflow, /HEAD:refs\/heads\/main/);
  assert.match(recover, /actions: write/);
  assert.doesNotMatch(recover, /pnpm|node /);
  assert.match(recover, /workflow run release\.yml/);
  assert.match(workflow, /60 days/);
  assert.doesNotMatch(
    readFileSync(join(root, ".github/workflows/release.yml"), "utf8"),
    /sdk-follow\.yml pushes tags/,
  );
});
