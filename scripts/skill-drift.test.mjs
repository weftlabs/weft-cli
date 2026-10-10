import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";

// The push trigger keeps the same path list. Split the triggers before
// asserting, or a whole-file search cannot tell which event owns `paths`.
const workflowPath = fileURLToPath(
  new URL("../.github/workflows/skill-drift.yml", import.meta.url),
);

function block(text, key, indent) {
  const lines = text.split("\n");
  const prefix = `${" ".repeat(indent)}${key}:`;
  const index = lines.findIndex(
    (line) => line === prefix || line.startsWith(`${prefix} `),
  );
  assert.notEqual(index, -1, `${key} missing from skill-drift.yml`);
  const body = [];
  for (const line of lines.slice(index + 1)) {
    if (line.trim() === "") {
      body.push(line);
      continue;
    }
    if (line.match(/^ */)[0].length <= indent) break;
    body.push(line);
  }
  while (body.length > 0 && body[body.length - 1].trim() === "") {
    body.pop();
  }
  return { header: lines[index], body: body.join("\n") };
}

function assertOrderedCode(body, snippets) {
  let from = 0;
  for (const snippet of snippets) {
    const at = body.indexOf(snippet, from);
    assert.notEqual(at, -1, `pinned Skill comparison missing: ${snippet}`);
    const lineStart = body.lastIndexOf("\n", at) + 1;
    const lineEnd = body.indexOf("\n", at);
    const line = body.slice(lineStart, lineEnd === -1 ? body.length : lineEnd);
    assert.equal(
      line.trimStart().startsWith("#"),
      false,
      `pinned Skill comparison is commented out: ${snippet}`,
    );
    from = at + snippet.length;
  }
}

test("every pull request runs the read-only pinned Skill drift check", () => {
  const text = readFileSync(workflowPath, "utf8").replaceAll("\r\n", "\n");
  const on = block(text, "on", 0);
  const pullRequest = block(`${on.header}\n${on.body}`, "pull_request", 2);
  const push = block(`${on.header}\n${on.body}`, "push", 2);
  const jobs = block(text, "jobs", 0);
  const drift = block(`${jobs.header}\n${jobs.body}`, "drift", 2);
  const permissions = block(text, "permissions", 0);
  const concurrency = block(text, "concurrency", 0);

  assert.equal(drift.header, "  drift:");
  assert.match(drift.body, /^ {4}timeout-minutes: 5$/m);
  assert.equal(permissions.body, "  contents: read");
  assert.doesNotMatch(text, /:\s*write\b/);
  assert.equal(
    concurrency.body,
    [
      "  group: ci-${{ github.workflow }}-${{ github.ref }}",
      "  cancel-in-progress: true",
    ].join("\n"),
  );
  assert.equal(
    push.body,
    [
      '    branches: ["main"]',
      "    paths:",
      '      - "skills/**"',
      '      - ".github/workflows/skill-drift.yml"',
    ].join("\n"),
  );
  assertOrderedCode(drift.body, [
    "ref=\"$(tr -d '[:space:]' < skills/SKILLS_REF)\"",
    '[[ "$ref" =~ ^[0-9a-f]{40}$ ]]',
    "git init -q canonical",
    "git -C canonical remote add origin https://github.com/weftlabs/skills.git",
    'git -C canonical fetch -q --depth 1 origin "$ref"',
    "git -C canonical checkout -q FETCH_HEAD",
    "diff -r canonical/skills/weft skills/weft",
  ]);
  assert.doesNotMatch(drift.body, /\bexit 0\b|\|\|\s*true\b/);

  assert.equal(pullRequest.header, "  pull_request:");
  assert.equal(
    pullRequest.body,
    "",
    `pull_request must be unconditional; a path filter skips the required drift check:\n${pullRequest.body}`,
  );
});
