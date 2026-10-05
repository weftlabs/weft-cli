import assert from "node:assert/strict";
import test from "node:test";

import { plan } from "./sdk-follow.mjs";

const day = 24 * 60 * 60_000;
const old = { publishedAt: 0, now: 2 * day, minAgeMinutes: 1440 };

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
    { changed: true, sdk: "0.30.0", cli: "0.30.0" },
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
    { changed: true, sdk: "0.30.1", cli: "0.30.2" },
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

test("rejects prerelease versions", () => {
  assert.throws(() =>
    plan({
      sdkRange: "^0.30.0",
      cliVersion: "0.30.0",
      sdkLatest: "0.31.0-rc.1",
      ...old,
    }),
  );
});
