// Install the packed CLI into an empty project and resolve @weftlabs/sdk
// from the public registry. This replaces the weft-sdk workspace acceptance
// that installed a file: SDK next to a file: CLI.
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
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const temp = await mkdtemp(join(tmpdir(), "weft-cli-pack-"));

function run(command, args, options = {}) {
  return execFileSync(command, args, {
    cwd: options.cwd ?? root,
    encoding: "utf8",
    env: options.env ?? process.env,
    stdio: options.stdio ?? ["ignore", "pipe", "pipe"],
  });
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

  const stdout = run(
    join(consumer, "node_modules", ".bin", "weft"),
    ["--help"],
    {
      cwd: consumer,
      env: {
        ...process.env,
        HOME: join(temp, "home"),
        USERPROFILE: "",
        WEFT_SKIP_SKILL_INSTALL: "1",
      },
    },
  );
  const help = JSON.parse(stdout);
  assert.equal(help.ok, true);
  assert.equal(help.command, "help");
  console.log(
    `Packed artifact acceptance passed for ${installedCli.name}@${installedCli.version} with ${sdkRange} resolved to ${sdkVersion} from the public registry`,
  );
} finally {
  await rm(temp, { recursive: true, force: true });
}
