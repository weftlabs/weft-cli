// Install the packed CLI into an empty project and resolve @weftlabs/sdk
// from the public registry. This replaces the weft-sdk workspace acceptance
// that installed a file: SDK next to a file: CLI.
//
// The installed binary must also install the bundled Skill into a temporary
// detected agent home. Compare those bytes with the installed archive, never
// the source mirror. Help keeps the install opt-out and a separate home so a
// background install cannot hide a missing bundle or installer.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import {
  access,
  mkdir,
  mkdtemp,
  readFile,
  rm,
  writeFile,
} from "node:fs/promises";
import { homedir, tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const temp = await mkdtemp(join(tmpdir(), "weft-cli-pack-"));
const skillFiles = ["SKILL.md", "rules/cli.md"];
const detectedHost = ".agents";
const installedSkillDir = ".agents/skills/weft";

function run(command, args, options = {}) {
  return execFileSync(command, args, {
    cwd: options.cwd ?? root,
    encoding: "utf8",
    env: options.env ?? process.env,
    stdio: options.stdio ?? ["ignore", "pipe", "pipe"],
  });
}

function isolatedEnv(home, { skipSkillInstall }) {
  const env = {
    ...process.env,
    HOME: home,
    USERPROFILE: home,
  };
  delete env.WEFT_API_KEY;
  delete env.WEFT_BASE_URL;
  if (skipSkillInstall) {
    env.WEFT_SKIP_SKILL_INSTALL = "1";
  } else {
    delete env.WEFT_SKIP_SKILL_INSTALL;
  }
  return env;
}

function assertTempHome(home) {
  assert.ok(
    home.startsWith(`${temp}/`),
    `Refusing agent home outside the temporary directory: ${home}`,
  );
  assert.notEqual(home, homedir());
  if (process.env.HOME) assert.notEqual(home, process.env.HOME);
  if (process.env.USERPROFILE) assert.notEqual(home, process.env.USERPROFILE);
}

async function readRequired(path, label) {
  try {
    return await readFile(path);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Skill acceptance failed: missing ${label}: ${message}`, {
      cause: error,
    });
  }
}

async function acceptInstalledSkill(consumer) {
  const home = join(temp, "skill-home");
  assertTempHome(home);
  // Create the host only for this command. An earlier background install must
  // not already have written the files this command is required to install.
  await mkdir(join(home, detectedHost), { recursive: true });

  const binary = join(consumer, "node_modules", ".bin", "weft");
  let stdout;
  try {
    stdout = run(binary, ["skill", "install"], {
      cwd: consumer,
      env: isolatedEnv(home, { skipSkillInstall: false }),
    });
  } catch (error) {
    const status = error?.status ?? "unknown";
    const stderr = error?.stderr?.toString?.() ?? "";
    throw new Error(
      `Skill acceptance failed: weft skill install exited ${status}. ${stderr}`.trim(),
      { cause: error },
    );
  }

  let result;
  try {
    result = JSON.parse(stdout);
  } catch (error) {
    throw new Error(
      `Skill acceptance failed: weft skill install did not print JSON: ${stdout}`,
      { cause: error },
    );
  }

  assert.equal(result.ok, true, "Skill acceptance failed: command was not ok");
  assert.equal(result.command, "skill");
  assert.equal(
    result.data?.status,
    "ok",
    `Skill acceptance failed: installer status ${result.data?.status ?? "missing"} reason ${result.data?.reason ?? "none"}`,
  );
  assert.equal(
    result.data?.installed,
    1,
    "Skill acceptance failed: expected the command to install one newly detected host",
  );
  assert.deepEqual(result.data?.hosts, [installedSkillDir]);
  assert.equal(result.data?.reason, undefined);
  assert.equal(result.data?.warnings, undefined);

  const packageRoot = join(consumer, "node_modules", "@weftlabs", "cli");
  const counts = [];
  for (const file of skillFiles) {
    const archived = await readRequired(
      join(packageRoot, "dist", "weft-skill", file),
      `archive ${file}`,
    );
    const installed = await readRequired(
      join(home, installedSkillDir, file),
      `installed ${file}`,
    );
    assert.ok(
      archived.length > 0,
      `Skill acceptance failed: archive ${file} is empty`,
    );
    assert.deepEqual(
      installed,
      archived,
      `Skill acceptance failed: installed ${file} does not match archive content`,
    );
    counts.push(`${file} (${archived.length} bytes)`);
  }
  return counts.join(" and ");
}

const givenTarball = process.argv[2];

try {
  let tarball;
  if (givenTarball) {
    tarball = givenTarball.startsWith("/")
      ? givenTarball
      : join(process.cwd(), givenTarball);
    await access(tarball);
  } else {
    await access(join(root, "dist", "cli.js"));
    const packed = run("pnpm", ["pack", "--pack-destination", temp]).trim();
    const printed = packed.split("\n").at(-1) ?? "";
    assert.ok(
      printed.endsWith(".tgz"),
      `pnpm pack did not name a tarball: ${packed}`,
    );
    tarball = printed.startsWith("/") ? printed : join(temp, printed);
  }

  const consumer = join(temp, "consumer");
  await mkdir(consumer);
  await writeFile(
    join(consumer, "package.json"),
    JSON.stringify({ name: "weft-cli-consumer", private: true }),
  );
  run("pnpm", ["add", tarball, "--store-dir", join(temp, "store")], {
    cwd: consumer,
    stdio: "inherit",
  });

  const installedCli = JSON.parse(
    await readFile(
      join(consumer, "node_modules", "@weftlabs", "cli", "package.json"),
      "utf8",
    ),
  );
  const sdkRange = installedCli.dependencies?.["@weftlabs/sdk"];
  assert.match(
    sdkRange ?? "",
    /^\^\d+\.\d+\.\d+$/,
    `Packed CLI must depend on a public @weftlabs/sdk range, got ${sdkRange}`,
  );
  assert.equal(installedCli.bin?.weft, "./bin/weft.mjs");

  const lockfile = await readFile(join(consumer, "pnpm-lock.yaml"), "utf8");
  const sdkVersion = lockfile.match(/'@weftlabs\/sdk@(\d+\.\d+\.\d+)':/)?.[1];
  assert.ok(
    sdkVersion,
    "The empty project did not resolve a public @weftlabs/sdk version",
  );
  assert.doesNotMatch(lockfile, /@weftlabs\/sdk@(?:file|workspace|link):/);
  // pnpm 10 omits the default-registry tarball URL. Compare the lockfile
  // integrity with the public registry so a local or workspace copy cannot pass.
  const registryResponse = await fetch(
    `https://registry.npmjs.org/@weftlabs/sdk/${sdkVersion}`,
    { headers: { accept: "application/json" } },
  );
  assert.equal(registryResponse.ok, true);
  const registryPackage = await registryResponse.json();
  assert.equal(typeof registryPackage.dist?.integrity, "string");
  assert.equal(lockfile.includes(registryPackage.dist.integrity), true);

  const helpHome = join(temp, "help-home");
  assertTempHome(helpHome);
  await mkdir(helpHome);
  const stdout = run(
    join(consumer, "node_modules", ".bin", "weft"),
    ["--help"],
    {
      cwd: consumer,
      env: isolatedEnv(helpHome, { skipSkillInstall: true }),
    },
  );
  const help = JSON.parse(stdout);
  assert.equal(help.ok, true);
  assert.equal(help.command, "help");
  await assert.rejects(
    access(join(helpHome, installedSkillDir, "SKILL.md")),
    (error) => error?.code === "ENOENT",
  );

  const installedSkill = await acceptInstalledSkill(consumer);
  console.log(
    `Packed artifact acceptance passed for ${installedCli.name}@${installedCli.version} with ${sdkRange} resolved to ${sdkVersion} from the public registry; installed ${installedSkill} into a temporary detected agent home`,
  );
} finally {
  await rm(temp, { recursive: true, force: true });
}
