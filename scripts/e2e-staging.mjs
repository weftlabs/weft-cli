// Staging smoke for the built CLI. A missing key is a failure here. The
// workflow skips before calling this script when the secret is absent.
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const baseUrl = (
  process.env.WEFT_BASE_URL ||
  process.env.WEFT_STAGING_BASE_URL ||
  ""
).replace(/\/+$/, "");
const apiKey = process.env.WEFT_API_KEY || "";

if (!baseUrl) {
  console.error("WEFT_BASE_URL is required");
  process.exit(1);
}
if (!apiKey) {
  console.error("WEFT_API_KEY is required");
  process.exit(1);
}

const commands = [
  ["me"],
  ["balance"],
  ["search", "weather data API", "--max-results", "3"],
];

for (const args of commands) {
  let stdout = "";
  try {
    stdout = execFileSync(process.execPath, ["bin/weft.mjs", ...args], {
      cwd: root,
      encoding: "utf8",
      env: {
        ...process.env,
        WEFT_API_KEY: apiKey,
        WEFT_BASE_URL: baseUrl,
        WEFT_SKIP_SKILL_INSTALL: "1",
      },
      stdio: ["ignore", "pipe", "pipe"],
    });
  } catch (error) {
    const stderr = String(error.stderr ?? "");
    let detail = stderr.slice(0, 500);
    try {
      const parsed = JSON.parse(stderr);
      detail = `error.code=${parsed.error?.code ?? "missing"} error.message=${parsed.error?.message ?? "missing"}`;
    } catch {
      // stderr is not a CLI JSON error. The slice above is the debug text.
    }
    console.error(
      `weft ${args.join(" ")} failed with exit ${error.status ?? "unknown"}: ${detail}`,
    );
    process.exit(1);
  }
  let parsed;
  try {
    parsed = JSON.parse(stdout);
  } catch {
    console.error(`weft ${args[0]} did not print JSON`);
    process.exit(1);
  }
  if (parsed.ok !== true) {
    console.error(`weft ${args[0]} returned ok: ${String(parsed.ok)}`);
    process.exit(1);
  }
  console.log(`weft ${args[0]}: ok`);
}
