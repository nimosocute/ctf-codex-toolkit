#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const childProcess = require("node:child_process");

const ROOT = path.resolve(__dirname, "..");
const PAYLOAD = path.join(ROOT, "payload");
const DEFAULT_DISTRO = process.env.CTF_CODEX_WSL_DISTRO || "kali-linux";
const DEFAULT_SKILLS_SOURCE = "https://github.com/ljagiello/ctf-skills.git";
const CONFIG_PATH = path.join(os.homedir(), ".ctf-codex-toolkit.json");

function usage() {
  console.log(`ctf-codex-toolkit

Usage:
  ctf-codex-toolkit setup [--distro kali-linux] [--ctf-root <path>] [--no-browser-arm] [--skip-health]
  ctf-codex-toolkit install [--distro kali-linux] [--ctf-root <path>] [--no-browser-arm]
  ctf-codex-toolkit health [--distro kali-linux]
  ctf-codex-toolkit update-skills [--distro kali-linux] [--source https://github.com/ljagiello/ctf-skills.git]
  ctf-codex-toolkit install-launchers
  ctf-codex-toolkit <challenge> [-Resume] [--distro kali-linux] [--ctf-root <path>]

Aliases:
  ctf-codex-workflow
  ctf-codex-wsl
  ctf-codex

Examples:
  npm exec --yes --package github:nimosocute/ctf-codex-toolkit -- ctf-codex-toolkit setup
  ctf-codex-toolkit setup
  ctf-codex-toolkit <challenge_name>
  ctf-codex-toolkit <challenge_name> -Resume
`);
}

function fail(message) {
  console.error(`[!] ${message}`);
  process.exit(1);
}

function hasFlag(args, flag) {
  return args.includes(flag);
}

function getOption(args, name, fallback) {
  const idx = args.indexOf(name);
  if (idx >= 0 && idx + 1 < args.length) return args[idx + 1];
  const prefix = `${name}=`;
  const match = args.find((arg) => arg.startsWith(prefix));
  return match ? match.slice(prefix.length) : fallback;
}

function removeOptions(args, names) {
  const out = [];
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    const matched = names.find((name) => arg === name || arg.startsWith(`${name}=`));
    if (!matched) {
      out.push(arg);
      continue;
    }
    if (arg === matched) i += 1;
  }
  return out;
}

function removeFlags(args, names) {
  return args.filter((arg) => !names.some((name) => arg === name || arg.startsWith(`${name}=`)));
}

function readConfig() {
  try {
    return JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
  } catch {
    return {};
  }
}

function writeConfig(config) {
  fs.writeFileSync(CONFIG_PATH, `${JSON.stringify(config, null, 2)}\n`, "utf8");
  console.log(`[+] wrote ${CONFIG_PATH}`);
}

function promptLine(question, fallback) {
  fs.writeSync(1, `${question}${fallback ? ` [${fallback}]` : ""}: `);
  const buffer = Buffer.alloc(4096);
  const bytes = fs.readSync(0, buffer, 0, buffer.length, null);
  const answer = buffer.toString("utf8", 0, bytes).trim();
  return answer || fallback;
}

function defaultCtfRoot() {
  return path.join(os.homedir(), "ctf-workspaces");
}

function resolveCtfRoot(args, options = {}) {
  const explicit = getOption(args, "--ctf-root", "");
  const envRoot = process.env.CTF_CODEX_ROOT || process.env.CTF_ROOT || "";
  const config = readConfig();
  let ctfRoot = explicit || envRoot || config.ctfRoot || "";
  if (!ctfRoot && options.prompt) {
    ctfRoot = promptLine("CTF workspace root on Windows", defaultCtfRoot());
  }
  if (!ctfRoot) return "";
  return path.resolve(ctfRoot);
}

function run(command, args, options = {}) {
  const result = childProcess.spawnSync(command, args, {
    stdio: options.capture ? ["ignore", "pipe", "pipe"] : "inherit",
    encoding: "utf8",
    shell: false,
    ...options
  });
  if (result.error) {
    fail(`${command} failed: ${result.error.message}`);
  }
  if (options.capture) {
    if (result.status !== 0) {
      fail(`${command} ${args.join(" ")} failed:\n${result.stderr || result.stdout}`);
    }
    return result.stdout.trim();
  }
  if (result.status !== 0) {
    process.exit(result.status || 1);
  }
  return "";
}

function wslArgs(distro, user, commandArgs) {
  const args = ["-d", distro];
  if (user) args.push("-u", user);
  args.push("--", ...commandArgs);
  return args;
}

function runWsl(distro, commandArgs, options = {}) {
  return run("wsl.exe", wslArgs(distro, options.user, commandArgs), options);
}

function shellQuote(value) {
  return `'${String(value).replace(/'/g, "'\\''")}'`;
}

function psQuote(value) {
  return `'${String(value).replace(/'/g, "''")}'`;
}

function toWslPath(distro, winPath) {
  if (process.platform !== "win32") {
    return winPath;
  }
  return runWsl(distro, ["wslpath", "-a", winPath], { capture: true });
}

function ensureWindows() {
  if (process.platform !== "win32") {
    fail("This launcher is intended to be run from Windows with WSL installed.");
  }
}

function findPowerShell() {
  for (const exe of ["pwsh.exe", "powershell.exe"]) {
    const result = childProcess.spawnSync("where", [exe], { stdio: "ignore", shell: false });
    if (result.status === 0) return exe;
  }
  fail("Cannot find pwsh.exe or powershell.exe.");
}

function copyWindowsLaunchers(ctfRoot = "") {
  ensureWindows();
  const sourceDir = path.join(PAYLOAD, "windows-launchers");
  const cmdLauncher = path.join(os.homedir(), "ctf-codex-wsl.cmd");
  const targets = [
    ["ctf-codex-wsl.ps1", path.join(os.homedir(), "ctf-codex-wsl.ps1")],
    ["ctf-codex-wsl.cmd", cmdLauncher]
  ];
  for (const [name, target] of targets) {
    fs.copyFileSync(path.join(sourceDir, name), target);
    console.log(`[+] wrote ${target}`);
  }
  createDesktopShortcut(cmdLauncher);
  if (ctfRoot) {
    const config = { ...readConfig(), ctfRoot };
    writeConfig(config);
  }
}

function createDesktopShortcut(cmdLauncher) {
  const ps = findPowerShell();
  const script = [
    "$desktop = [Environment]::GetFolderPath('Desktop')",
    "if (-not $desktop) { throw 'Cannot resolve Desktop path.' }",
    "$shortcutPath = Join-Path $desktop 'CTF Codex WSL.lnk'",
    "$shell = New-Object -ComObject WScript.Shell",
    "$shortcut = $shell.CreateShortcut($shortcutPath)",
    `$shortcut.TargetPath = ${psQuote(cmdLauncher)}`,
    "$shortcut.WorkingDirectory = [Environment]::GetFolderPath('UserProfile')",
    "$shortcut.Description = 'Launch CTF Codex Toolkit for Kali WSL'",
    "$shortcut.Save()",
    "Write-Output $shortcutPath"
  ].join("; ");
  const shortcutPath = run(ps, ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script], { capture: true });
  console.log(`[+] wrote ${shortcutPath}`);
}

function install(args) {
  ensureWindows();
  const distro = getOption(args, "--distro", DEFAULT_DISTRO);
  const ctfRoot = resolveCtfRoot(args, { prompt: true });
  const withBrowserArm = !hasFlag(args, "--no-browser-arm");
  const payloadWsl = shellQuote(toWslPath(distro, PAYLOAD));
  const ctfRootWsl = shellQuote(toWslPath(distro, ctfRoot));

  console.log(`[+] Installing CTF Codex payload into WSL distro: ${distro}`);
  console.log(`[+] CTF workspace root: ${ctfRoot}`);

  const userInstall = `
set -euo pipefail
payload=${payloadWsl}
ctf_root=${ctfRootWsl}
mkdir -p "$HOME/.codex/tools/browser_arm" "$HOME/.codex/ctf-snippets" "$HOME/.codex/skills" "$HOME/.codex/hooks"
sed "s|{{CTF_ROOT}}|$ctf_root|g" "$payload/home-codex/AGENTS.md" > "$HOME/.codex/AGENTS.md"
cp "$payload/home-codex/ctf-checklists.md" "$HOME/.codex/ctf-checklists.md"
cp "$payload/home-codex/tools_inventory.md" "$HOME/.codex/tools_inventory.md"
cp "$payload/home-codex/tools/ctf_health_check.py" "$HOME/.codex/tools/ctf_health_check.py"
cp "$payload/home-codex/tools/browser_arm/browser_server.py" "$HOME/.codex/tools/browser_arm/browser_server.py"
cp "$payload/home-codex/tools/browser_arm/browser_client.py" "$HOME/.codex/tools/browser_arm/browser_client.py"
cp -a "$payload/home-codex/ctf-snippets/." "$HOME/.codex/ctf-snippets/"
cp -a "$payload/home-codex/skills/." "$HOME/.codex/skills/"
chmod 755 "$HOME/.codex/tools/ctf_health_check.py"
chmod 644 "$HOME/.codex/tools/browser_arm/browser_server.py" "$HOME/.codex/tools/browser_arm/browser_client.py"
ln -sf /opt/codex-ctf-hooks/ctf_pre_tool_guard.py "$HOME/.codex/hooks/ctf_pre_tool_guard.py"
ln -sf /opt/codex-ctf-hooks/ctf_post_tool_guard.py "$HOME/.codex/hooks/ctf_post_tool_guard.py"
ln -sf /opt/codex-ctf-hooks/ctf_stop_guard.py "$HOME/.codex/hooks/ctf_stop_guard.py"
`;
  runWsl(distro, ["bash", "-lc", userInstall]);

  const rootInstall = `
set -euo pipefail
payload=${payloadWsl}
mkdir -p /opt/codex-ctf-hooks /usr/local/bin
cp "$payload/opt-hooks/ctf_pre_tool_guard.py" /opt/codex-ctf-hooks/ctf_pre_tool_guard.py
cp "$payload/opt-hooks/ctf_post_tool_guard.py" /opt/codex-ctf-hooks/ctf_post_tool_guard.py
cp "$payload/opt-hooks/ctf_stop_guard.py" /opt/codex-ctf-hooks/ctf_stop_guard.py
cp "$payload/opt-hooks/ctf-command-guard" /opt/codex-ctf-hooks/ctf-command-guard
cp "$payload/usr-local-bin/ctf-codex" /usr/local/bin/ctf-codex
chmod 755 /opt/codex-ctf-hooks/ctf_pre_tool_guard.py /opt/codex-ctf-hooks/ctf_post_tool_guard.py /opt/codex-ctf-hooks/ctf_stop_guard.py /opt/codex-ctf-hooks/ctf-command-guard /usr/local/bin/ctf-codex
chown root:root /opt/codex-ctf-hooks/ctf_pre_tool_guard.py /opt/codex-ctf-hooks/ctf_post_tool_guard.py /opt/codex-ctf-hooks/ctf_stop_guard.py /opt/codex-ctf-hooks/ctf-command-guard /usr/local/bin/ctf-codex
`;
  runWsl(distro, ["bash", "-lc", rootInstall], { user: "root" });

  if (withBrowserArm) {
    console.log("[+] Installing Browser Arm Python dependency in isolated ~/.codex/tools/browser_arm/.venv");
    const browserInstall = `
set -euo pipefail
python3 -m venv "$HOME/.codex/tools/browser_arm/.venv"
"$HOME/.codex/tools/browser_arm/.venv/bin/python" -m pip install --upgrade pip cloakbrowser
"$HOME/.codex/tools/browser_arm/.venv/bin/python" - <<'PY'
from cloakbrowser import ensure_binary
print(ensure_binary())
PY
`;
    runWsl(distro, ["bash", "-lc", browserInstall]);
  } else {
    console.log("[=] Skipped Browser Arm venv install (--no-browser-arm).");
  }

  copyWindowsLaunchers(ctfRoot);
  console.log("[+] Install complete.");
}

function health(args) {
  ensureWindows();
  const distro = getOption(args, "--distro", DEFAULT_DISTRO);
  runWsl(distro, ["bash", "-lc", "python3 ~/.codex/tools/ctf_health_check.py"]);
}

function updateSkills(args) {
  ensureWindows();
  const distro = getOption(args, "--distro", DEFAULT_DISTRO);
  const source = getOption(args, "--source", DEFAULT_SKILLS_SOURCE);

  if (!/^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(?:\.git)?$/.test(source)) {
    fail("Refusing unsupported skill source URL. Use an HTTPS GitHub repository URL.");
  }

  console.log(`[+] Updating CTF skills in WSL distro: ${distro}`);
  console.log(`[+] Source: ${source}`);

  const updateScript = `
set -euo pipefail
source_url=${shellQuote(source)}
tmp="$(mktemp -d)"
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT
git clone --depth 1 "$source_url" "$tmp/src"
mkdir -p "$HOME/.codex/skills"
count=0
while IFS= read -r skill_file; do
  skill_dir="$(dirname "$skill_file")"
  name="$(basename "$skill_dir")"
  case "$name" in
    ctf-*|solve-challenge|ctf-writeup)
      rm -rf "$HOME/.codex/skills/$name"
      cp -a "$skill_dir" "$HOME/.codex/skills/$name"
      count=$((count + 1))
      printf '[+] updated skill: %s\\n' "$name"
      ;;
  esac
done < <(find "$tmp/src" -mindepth 1 -maxdepth 3 -name SKILL.md -type f | sort)
if [ "$count" -eq 0 ]; then
  echo "[!] No matching CTF skill directories found in source repository." >&2
  exit 1
fi
printf '[+] Updated %s skill directories.\\n' "$count"
`;
  runWsl(distro, ["bash", "-lc", updateScript]);
}

function setup(args) {
  const installArgs = removeFlags(args, ["--skip-health"]);
  const skipHealth = hasFlag(args, "--skip-health");

  install(installArgs);
  if (skipHealth) {
    console.log("[=] Skipped health check (--skip-health).");
    return;
  }

  console.log("[+] Running health check");
  health(installArgs);
}

function launch(args) {
  ensureWindows();
  const ps = findPowerShell();
  const launcher = path.join(PAYLOAD, "windows-launchers", "ctf-codex-wsl.ps1");
  const distro = getOption(args, "--distro", "");
  const ctfRoot = resolveCtfRoot(args);
  const psArgs = removeOptions(args, ["--distro", "--ctf-root"]);
  if (distro) psArgs.push("-Distro", distro);
  if (ctfRoot) psArgs.push("-CtfRoot", ctfRoot);
  run(ps, ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", launcher, ...psArgs]);
}

function main() {
  const args = process.argv.slice(2);
  if (args.length === 0 || args[0] === "--help" || args[0] === "-h") {
    usage();
    return;
  }

  const [cmd, ...rest] = args;
  if (cmd === "setup") return setup(rest);
  if (cmd === "install") return install(rest);
  if (cmd === "health") return health(rest);
  if (cmd === "update-skills") return updateSkills(rest);
  if (cmd === "install-launchers") return copyWindowsLaunchers(resolveCtfRoot(rest, { prompt: true }));
  if (cmd === "version" || cmd === "--version") {
    const pkg = require(path.join(ROOT, "package.json"));
    console.log(pkg.version);
    return;
  }
  launch(args);
}

main();
