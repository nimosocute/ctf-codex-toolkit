#!/usr/bin/env node
const fs = require("node:fs");
const path = require("node:path");
const childProcess = require("node:child_process");

const root = path.resolve(__dirname, "..");
const required = [
  "bin/ctf-codex-toolkit.js",
  ".github/workflows/ci.yml",
  "CONTRIBUTING.md",
  "THIRD_PARTY_NOTICES.md",
  "payload/home-codex/AGENTS.md",
  "payload/home-codex/ctf-checklists.md",
  "payload/home-codex/tools_inventory.md",
  "payload/home-codex/tools/ctf_health_check.py",
  "payload/home-codex/tools/browser_arm/browser_server.py",
  "payload/opt-hooks/ctf_pre_tool_guard.py",
  "payload/opt-hooks/ctf_post_tool_guard.py",
  "payload/opt-hooks/ctf_stop_guard.py",
  "payload/opt-hooks/ctf-command-guard",
  "payload/usr-local-bin/ctf-codex",
  "payload/windows-launchers/ctf-codex-wsl.ps1",
  "payload/windows-launchers/ctf-codex-wsl.cmd"
];

const forbiddenPathParts = [
  ".venv",
  ".git",
  "__pycache__",
  "sessions",
  "history",
  "logs"
];

const forbiddenText = [
  ["127.0.0.1", ":", "20128"].join(""),
  ["cx", "/", "gpt"].join(""),
  ["gpt-", "5.5"].join("")
];

const forbiddenRegex = [
  /\/home\/[A-Za-z0-9_-]+\/\.codex/,
  /9\s*router/i,
  /sk-(?=[A-Za-z0-9_-]{20,})(?=[A-Za-z0-9_-]*[A-Z0-9_])[A-Za-z0-9_-]+/,
  /Bearer\s+[A-Za-z0-9._-]{20,}/
];

for (const rel of required) {
  const full = path.join(root, rel);
  if (!fs.existsSync(full)) {
    console.error(`missing ${rel}`);
    process.exit(1);
  }
}

function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    const rel = path.relative(root, full).replaceAll(path.sep, "/");
    if (forbiddenPathParts.some((part) => rel.split("/").includes(part))) {
      console.error(`forbidden package path ${rel}`);
      process.exit(1);
    }
    if (rel.endsWith(".pyc")) {
      console.error(`forbidden bytecode file ${rel}`);
      process.exit(1);
    }
    if (entry.isDirectory()) {
      walk(full);
      continue;
    }
    const text = fs.readFileSync(full, "utf8");
    for (const needle of forbiddenText) {
      if (text.includes(needle)) {
        console.error(`forbidden text ${needle} in ${rel}`);
        process.exit(1);
      }
    }
    if (!rel.endsWith(".md")) {
      for (const pattern of forbiddenRegex) {
        if (pattern.test(text)) {
          console.error(`forbidden token-like text ${pattern} in ${rel}`);
          process.exit(1);
        }
      }
    }
  }
}

walk(path.join(root, "payload"));

for (const rel of ["README.md", "package.json", "bin/ctf-codex-toolkit.js"]) {
  const text = fs.readFileSync(path.join(root, rel), "utf8");
  for (const needle of forbiddenText) {
    if (text.includes(needle)) {
      console.error(`forbidden text ${needle} in ${rel}`);
      process.exit(1);
    }
  }
  for (const pattern of forbiddenRegex) {
    if (pattern.test(text)) {
      console.error(`forbidden token-like text ${pattern} in ${rel}`);
      process.exit(1);
    }
  }
}

const windowsLauncher = fs.readFileSync(path.join(root, "payload/windows-launchers/ctf-codex-wsl.ps1"), "utf8");
if (!windowsLauncher.includes("$CTF_ROOT  = Resolve-WindowsFullPath $CtfRoot")) {
  console.error("Windows launcher must resolve CTF root to an absolute path before deriving _work paths");
  process.exit(1);
}
if (!windowsLauncher.includes("function Quote-BashArgument") || !windowsLauncher.includes("Quote-BashArgument $GuardPathWsl")) {
  console.error("Windows launcher must bash-quote WSL guard paths before chmod");
  process.exit(1);
}
if (!windowsLauncher.includes("function Repair-CompactWindowsPath") || !windowsLauncher.includes("function ConvertTo-WslPath")) {
  console.error("Windows launcher must repair compact Windows paths and fallback-convert WSL paths");
  process.exit(1);
}
if (!windowsLauncher.includes("\":Users\"") || !windowsLauncher.includes("/mnt/$drive/$tail")) {
  console.error("Windows launcher path repair/fallback markers are missing");
  process.exit(1);
}

const help = childProcess.spawnSync(process.execPath, [path.join(root, "bin/ctf-codex-toolkit.js"), "--help"], {
  encoding: "utf8"
});
if (
  help.status !== 0 ||
  !help.stdout.includes("ctf-codex-toolkit setup") ||
  !help.stdout.includes("ctf-codex-toolkit install")
) {
  console.error(help.stdout);
  console.error(help.stderr);
  process.exit(1);
}

console.log("smoke ok");
