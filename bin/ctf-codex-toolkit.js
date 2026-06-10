#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const childProcess = require("node:child_process");

const ROOT = path.resolve(__dirname, "..");
const PAYLOAD = path.join(ROOT, "payload");
const DEFAULT_SKILLS_SOURCE = "https://github.com/ljagiello/ctf-skills.git";
const CLOAKBROWSER_VERSION = "0.3.31";
const CONFIG_PATH = path.join(os.homedir(), ".ctf-codex-toolkit.json");
const PACKAGE_VERSION = require(path.join(ROOT, "package.json")).version;
const INVENTORY_APT_PACKAGES = [
  "ca-certificates",
  "bzip2",
  "xz-utils",
  "tar",
  "unzip",
  "build-essential",
  "python3",
  "python3-venv",
  "python3-pip",
  "python3-pwntools",
  "gdb",
  "checksec",
  "python3-z3",
  "sagemath",
  "python3-angr",
  "binwalk",
  "libimage-exiftool-perl",
  "foremost",
  "tshark",
  "radare2",
  "ghidra",
  "verilator",
  "yosys",
  "fpga-icestorm",
  "bitwuzla",
  "curl",
  "ffuf",
  "golang",
  "hashcat",
  "john",
  "libnspr4",
  "libnss3",
  "libatk-bridge2.0-0",
  "libgtk-3-0",
  "libgbm1",
  "libxkbcommon0"
];

function usage() {
  console.log(`ctf-codex-toolkit

Usage:
  ctf-codex-toolkit --help
  ctf-codex-toolkit -h
  ctf-codex-toolkit --version
  ctf-codex-toolkit version
  ctf-codex-toolkit setup [--ctf-root <path>] [--no-browser-arm] [--skip-tools] [--skip-health]
  ctf-codex-toolkit install [--ctf-root <path>] [--no-browser-arm] [--skip-tools]
  ctf-codex-toolkit install-tools
  ctf-codex-toolkit health
  ctf-codex-toolkit update-skills [--source https://github.com/ljagiello/ctf-skills.git]
  ctf-codex-toolkit install-launchers
  ctf-codex-toolkit <challenge> [-Resume] [--ctf-root <path>]

Aliases:
  ctf-codex-workflow
  ctf-codex-wsl

Examples:
  npm exec --yes --package ctf-codex-toolkit -- ctf-codex-toolkit setup
  ctf-codex-toolkit setup
  ctf-codex-toolkit <challenge>
  ctf-codex-toolkit <challenge> -Resume
`);
}

function fail(message) {
  console.error(`[!] ${message}`);
  process.exit(1);
}

function ensureUnix() {
  if (process.platform === "win32") {
    fail("Run this command inside Kali Linux or Kali WSL.");
  }
}

function isWsl() {
  if (process.env.WSL_DISTRO_NAME || process.env.WSL_INTEROP) return true;
  try {
    const release = fs.readFileSync("/proc/sys/kernel/osrelease", "utf8").toLowerCase();
    return release.includes("microsoft") || release.includes("wsl");
  } catch {
    return false;
  }
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

function resolveCtfRoot(args, options = {}) {
  const explicit = getOption(args, "--ctf-root", "");
  const envRoot = process.env.CTF_CODEX_ROOT || process.env.CTF_ROOT || "";
  const config = readConfig();
  let ctfRoot = explicit || envRoot || config.ctfRoot || "";
  if (!ctfRoot && options.prompt) {
    ctfRoot = promptLine("CTF workspace root", path.join(os.homedir(), "ctf-workspaces"));
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
  if (result.error) fail(`${command} failed: ${result.error.message}`);
  if (options.capture) {
    if (result.status !== 0) fail(`${command} ${args.join(" ")} failed:\n${result.stderr || result.stdout}`);
    return result.stdout.trim();
  }
  if (result.status !== 0) process.exit(result.status || 1);
  return "";
}

function shellQuote(value) {
  return `'${String(value).replace(/'/g, "'\\''")}'`;
}

function psQuote(value) {
  return `'${String(value).replace(/'/g, "''")}'`;
}

function copyDir(source, target) {
  fs.mkdirSync(target, { recursive: true });
  fs.cpSync(source, target, { recursive: true, force: true });
}

function copyFile(source, target, mode) {
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(source, target);
  if (mode) fs.chmodSync(target, mode);
}

function runBash(script) {
  return run("bash", ["-lc", script]);
}

function commandExists(command) {
  const result = childProcess.spawnSync("bash", ["-lc", `command -v ${shellQuote(command)} >/dev/null 2>&1`], {
    stdio: "ignore",
    shell: false
  });
  return result.status === 0;
}

function windowsToWslPath(windowsPath) {
  return run("wslpath", ["-a", windowsPath], { capture: true });
}

function getWindowsProfilePath() {
  const output = run("cmd.exe", ["/c", "echo", "%USERPROFILE%"], { capture: true });
  return output.replace(/\r/g, "").split("\n")[0].trim();
}

function installWindowsLaunchersFromWsl() {
  if (!isWsl()) {
    console.log("[=] Native Kali detected; Windows launchers are not installed.");
    return;
  }
  if (!commandExists("powershell.exe") || !commandExists("cmd.exe") || !commandExists("wslpath")) {
    console.log("[=] WSL detected, but Windows interop tools are unavailable; skipped Windows launchers.");
    return;
  }

  const windowsProfile = getWindowsProfilePath();
  if (!windowsProfile) {
    console.log("[=] WSL detected, but Windows user profile could not be resolved; skipped Windows launchers.");
    return;
  }

  const windowsProfileWsl = windowsToWslPath(windowsProfile);
  const sourceDir = path.join(PAYLOAD, "windows-launchers");
  const ps1Target = path.join(windowsProfileWsl, "ctf-codex-wsl.ps1");
  const cmdTarget = path.join(windowsProfileWsl, "ctf-codex-wsl.cmd");

  copyFile(path.join(sourceDir, "ctf-codex-wsl.ps1"), ps1Target, 0o644);
  copyFile(path.join(sourceDir, "ctf-codex-wsl.cmd"), cmdTarget, 0o644);
  console.log(`[+] wrote ${ps1Target}`);
  console.log(`[+] wrote ${cmdTarget}`);

  const cmdTargetWin = `${windowsProfile}\\ctf-codex-wsl.cmd`;
  const shortcutArgs = `/k "${cmdTargetWin}"`;
  const shortcutScript = [
    "$desktop = [Environment]::GetFolderPath('Desktop')",
    "if (-not $desktop) { throw 'Cannot resolve Desktop path.' }",
    "$shortcutPath = Join-Path $desktop 'CTF Codex WSL.lnk'",
    "$shell = New-Object -ComObject WScript.Shell",
    "$shortcut = $shell.CreateShortcut($shortcutPath)",
    "$shortcut.TargetPath = Join-Path $env:SystemRoot 'System32\\cmd.exe'",
    `$shortcut.Arguments = ${psQuote(shortcutArgs)}`,
    "$shortcut.WorkingDirectory = [Environment]::GetFolderPath('UserProfile')",
    "$shortcut.Description = 'Launch CTF Codex Toolkit for Kali WSL'",
    "$shortcut.Save()",
    "Write-Output $shortcutPath"
  ].join("; ");

  const shortcutPath = run("powershell.exe", [
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    shortcutScript
  ], { capture: true }).replace(/\r/g, "").trim();
  console.log(`[+] wrote ${shortcutPath}`);
}

function runPrivilegedBash(script) {
  if (typeof process.getuid === "function" && process.getuid() === 0) {
    return run("bash", ["-lc", script]);
  }
  return run("sudo", ["bash", "-lc", script]);
}

function installBrowserArm() {
  console.log("[+] Installing Browser Arm Python dependency in isolated ~/.codex/tools/browser_arm/.venv");
  const browserInstall = `
set -euo pipefail
unset PYTHONPATH
export PYTHONNOUSERSITE=1
python3 -m venv "$HOME/.codex/tools/browser_arm/.venv"
"$HOME/.codex/tools/browser_arm/.venv/bin/python" -m pip install --upgrade pip "cloakbrowser==${CLOAKBROWSER_VERSION}"
"$HOME/.codex/tools/browser_arm/.venv/bin/python" - <<'PY'
from cloakbrowser import ensure_binary
print(ensure_binary())
PY
`;
  return runBash(browserInstall);
}

function installInventoryTools(args = []) {
  ensureUnix();
  const withBrowserArm = !hasFlag(args, "--no-browser-arm");
  const codexHome = path.join(os.homedir(), ".codex");
  fs.mkdirSync(path.join(codexHome, "tools", "browser_arm"), { recursive: true });
  if (!fs.existsSync(path.join(codexHome, "tools", "ctf_health_check.py"))) {
    copyFile(path.join(PAYLOAD, "home-codex", "tools", "ctf_health_check.py"), path.join(codexHome, "tools", "ctf_health_check.py"), 0o755);
  }
  if (!fs.existsSync(path.join(codexHome, "tools", "browser_arm", "browser_server.py"))) {
    copyFile(path.join(PAYLOAD, "home-codex", "tools", "browser_arm", "browser_server.py"), path.join(codexHome, "tools", "browser_arm", "browser_server.py"), 0o644);
    copyFile(path.join(PAYLOAD, "home-codex", "tools", "browser_arm", "browser_client.py"), path.join(codexHome, "tools", "browser_arm", "browser_client.py"), 0o644);
  }

  console.log("[+] Installing required CTF tools from tools_inventory.md");
  console.log("[=] This can take a while on minimal Kali, especially sagemath, ghidra, angr, and oss-cad-suite.");
  const packageList = INVENTORY_APT_PACKAGES.map((pkg) => `  ${shellQuote(pkg)}`).join("\n");
  const installScript = `
set -uo pipefail
export DEBIAN_FRONTEND=noninteractive
if ! command -v apt-get >/dev/null 2>&1; then
  echo "[!] apt-get not found; this installer currently requires Kali/Debian apt for base tool bootstrap." >&2
  exit 1
fi
echo "wireshark-common wireshark-common/install-setuid boolean false" | debconf-set-selections >/dev/null 2>&1 || true
apt-get update
packages=(
${packageList}
)
failed=()
for pkg in "\${packages[@]}"; do
  printf '[+] apt install %s\\n' "$pkg"
  if apt-get install -y "$pkg"; then
    printf '[+] installed %s\\n' "$pkg"
  else
    printf '[!] failed to install %s\\n' "$pkg" >&2
    failed+=("$pkg")
  fi
done
if [ "\${#failed[@]}" -gt 0 ]; then
  printf '[!] Some apt packages failed, fallback installers will try to cover required tools: %s\\n' "\${failed[*]}" >&2
fi

mkdir -p /opt/codex-ctf-python /opt/oss-cad-suite /usr/local/bin
cat >/etc/profile.d/ctf-codex-tools.sh <<'EOF'
export PATH="/opt/oss-cad-suite/bin:/opt/codex-ctf-python/bin:$PATH"
pyver="$(python3 - <<'PY' 2>/dev/null || true
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
if [ -n "$pyver" ] && [ -d "/opt/codex-ctf-python/lib/python$pyver/site-packages" ]; then
  export PYTHONPATH="/opt/codex-ctf-python/lib/python$pyver/site-packages:\${PYTHONPATH:-}"
fi
EOF
chmod 644 /etc/profile.d/ctf-codex-tools.sh
export PATH="/opt/oss-cad-suite/bin:/opt/codex-ctf-python/bin:$PATH"
pyver="$(python3 - <<'PY' 2>/dev/null || true
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
if [ -n "$pyver" ] && [ -d "/opt/codex-ctf-python/lib/python$pyver/site-packages" ]; then
  export PYTHONPATH="/opt/codex-ctf-python/lib/python$pyver/site-packages:\${PYTHONPATH:-}"
fi

if ! python3 -c 'import pwnlib, z3, angr' >/dev/null 2>&1 || ! command -v pwn >/dev/null 2>&1; then
  echo "[+] Installing Python CTF fallbacks into /opt/codex-ctf-python"
  python3 -m venv /opt/codex-ctf-python
  /opt/codex-ctf-python/bin/python -m pip install --upgrade pip wheel
  /opt/codex-ctf-python/bin/python -m pip install pwntools z3-solver angr
  ln -sf /opt/codex-ctf-python/bin/pwn /usr/local/bin/pwn
  pyver="$(python3 - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
  export PYTHONPATH="/opt/codex-ctf-python/lib/python$pyver/site-packages:\${PYTHONPATH:-}"
fi

if ! command -v ffuf >/dev/null 2>&1; then
  echo "[+] Installing ffuf fallback with Go"
  GOBIN=/usr/local/bin go install github.com/ffuf/ffuf/v2@latest
fi

if ! command -v yosys >/dev/null 2>&1 || ! command -v bitwuzla >/dev/null 2>&1; then
  echo "[+] Installing oss-cad-suite fallback into /opt/oss-cad-suite"
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  oss_url="$(python3 - <<'PY'
import json
import platform
import sys
import urllib.request

machine = platform.machine().lower()
if machine in {"x86_64", "amd64"}:
    platform_name = "linux-x64"
elif machine in {"aarch64", "arm64"}:
    platform_name = "linux-arm64"
else:
    raise SystemExit(f"unsupported oss-cad-suite architecture: {machine}")

with urllib.request.urlopen("https://api.github.com/repos/YosysHQ/oss-cad-suite-build/releases/latest", timeout=30) as response:
    release = json.load(response)

for asset in release.get("assets", []):
    name = asset.get("name", "")
    if name.startswith(f"oss-cad-suite-{platform_name}-") and name.endswith(".tgz"):
        print(asset["browser_download_url"])
        break
else:
    raise SystemExit(f"no oss-cad-suite asset found for {platform_name}")
PY
)"
  if [ -z "$oss_url" ]; then
    echo "[!] Could not resolve oss-cad-suite download URL." >&2
    exit 1
  fi
  curl -L --fail --retry 3 "$oss_url" -o "$tmp/oss-cad-suite.tgz"
  rm -rf /opt/oss-cad-suite
  tar -xzf "$tmp/oss-cad-suite.tgz" -C /opt
fi

if ! command -v sage >/dev/null 2>&1; then
  echo "[+] Installing SageMath fallback with micromamba into /opt/codex-ctf-sage"
  if ! command -v micromamba >/dev/null 2>&1; then
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    curl -L --fail --retry 3 https://micro.mamba.pm/api/micromamba/linux-64/latest -o "$tmp/micromamba.tar.bz2"
    tar -xjf "$tmp/micromamba.tar.bz2" -C "$tmp"
    install -m 755 "$tmp/bin/micromamba" /usr/local/bin/micromamba
  fi
  micromamba create -y -p /opt/codex-ctf-sage -c conda-forge sage
  ln -sf /opt/codex-ctf-sage/bin/sage /usr/local/bin/sage
fi
`;
  runPrivilegedBash(installScript);

  if (withBrowserArm) {
    installBrowserArm();
  } else {
    console.log("[=] Skipped Browser Arm inventory install (--no-browser-arm).");
  }

  console.log("[+] Verifying required CTF tools");
  return health();
}

function install(args) {
  ensureUnix();
  const ctfRoot = resolveCtfRoot(args, { prompt: true });
  const withBrowserArm = !hasFlag(args, "--no-browser-arm");
  const withTools = !hasFlag(args, "--skip-tools") && !hasFlag(args, "--no-tools");
  const codexHome = path.join(os.homedir(), ".codex");

  console.log("[+] Installing CTF Codex payload into this Kali environment");
  console.log(`[+] ctf-codex-toolkit version: ${PACKAGE_VERSION}`);
  console.log(`[+] CTF workspace root: ${ctfRoot}`);

  fs.mkdirSync(path.join(codexHome, "tools", "browser_arm"), { recursive: true });
  fs.mkdirSync(path.join(codexHome, "ctf-snippets"), { recursive: true });
  fs.mkdirSync(path.join(codexHome, "skills"), { recursive: true });
  fs.mkdirSync(path.join(codexHome, "hooks"), { recursive: true });

  const agents = fs.readFileSync(path.join(PAYLOAD, "home-codex", "AGENTS.md"), "utf8")
    .replaceAll("{{CTF_ROOT}}", ctfRoot);
  fs.writeFileSync(path.join(codexHome, "AGENTS.md"), agents, "utf8");
  copyFile(path.join(PAYLOAD, "home-codex", "ctf-checklists.md"), path.join(codexHome, "ctf-checklists.md"));
  copyFile(path.join(PAYLOAD, "home-codex", "tools_inventory.md"), path.join(codexHome, "tools_inventory.md"));
  copyFile(path.join(PAYLOAD, "home-codex", "tools", "ctf_health_check.py"), path.join(codexHome, "tools", "ctf_health_check.py"), 0o755);
  copyFile(path.join(PAYLOAD, "home-codex", "tools", "browser_arm", "browser_server.py"), path.join(codexHome, "tools", "browser_arm", "browser_server.py"), 0o644);
  copyFile(path.join(PAYLOAD, "home-codex", "tools", "browser_arm", "browser_client.py"), path.join(codexHome, "tools", "browser_arm", "browser_client.py"), 0o644);
  copyDir(path.join(PAYLOAD, "home-codex", "ctf-snippets"), path.join(codexHome, "ctf-snippets"));
  copyDir(path.join(PAYLOAD, "home-codex", "skills"), path.join(codexHome, "skills"));

  const rootInstall = `
set -euo pipefail
payload=${shellQuote(PAYLOAD)}
mkdir -p /opt/codex-ctf-hooks /usr/local/bin
cp "$payload/opt-hooks/ctf_pre_tool_guard.py" /opt/codex-ctf-hooks/ctf_pre_tool_guard.py
cp "$payload/opt-hooks/ctf_post_tool_guard.py" /opt/codex-ctf-hooks/ctf_post_tool_guard.py
cp "$payload/opt-hooks/ctf_stop_guard.py" /opt/codex-ctf-hooks/ctf_stop_guard.py
cp "$payload/opt-hooks/ctf-command-guard" /opt/codex-ctf-hooks/ctf-command-guard
cp "$payload/usr-local-bin/ctf-codex" /usr/local/bin/ctf-codex
chmod 755 /opt/codex-ctf-hooks/ctf_pre_tool_guard.py /opt/codex-ctf-hooks/ctf_post_tool_guard.py /opt/codex-ctf-hooks/ctf_stop_guard.py /opt/codex-ctf-hooks/ctf-command-guard /usr/local/bin/ctf-codex
chown root:root /opt/codex-ctf-hooks/ctf_pre_tool_guard.py /opt/codex-ctf-hooks/ctf_post_tool_guard.py /opt/codex-ctf-hooks/ctf_stop_guard.py /opt/codex-ctf-hooks/ctf-command-guard /usr/local/bin/ctf-codex
`;
  runPrivilegedBash(rootInstall);

  for (const [name, target] of [
    ["ctf_pre_tool_guard.py", "/opt/codex-ctf-hooks/ctf_pre_tool_guard.py"],
    ["ctf_post_tool_guard.py", "/opt/codex-ctf-hooks/ctf_post_tool_guard.py"],
    ["ctf_stop_guard.py", "/opt/codex-ctf-hooks/ctf_stop_guard.py"]
  ]) {
    const link = path.join(codexHome, "hooks", name);
    fs.rmSync(link, { force: true });
    fs.symlinkSync(target, link);
  }

  if (withTools) {
    installInventoryTools(withBrowserArm ? [] : ["--no-browser-arm"]);
  } else {
    console.log("[=] Skipped CTF inventory tool install (--skip-tools).");
    if (withBrowserArm) {
      installBrowserArm();
    } else {
      console.log("[=] Skipped Browser Arm venv install (--no-browser-arm).");
    }
  }

  writeConfig({ ...readConfig(), ctfRoot, toolkitVersion: PACKAGE_VERSION });
  installWindowsLaunchersFromWsl();
  console.log("[+] Install complete.");
}

function health() {
  ensureUnix();
  return run("python3", [path.join(os.homedir(), ".codex", "tools", "ctf_health_check.py")]);
}

function updateSkills(args) {
  ensureUnix();
  const source = getOption(args, "--source", DEFAULT_SKILLS_SOURCE);
  if (!/^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(?:\.git)?$/.test(source)) {
    fail("Refusing unsupported skill source URL. Use an HTTPS GitHub repository URL.");
  }

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
  console.log("[+] Updating CTF skills in this Kali environment");
  return runBash(updateScript);
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
  health();
}

function launch(args) {
  ensureUnix();
  const ctfRoot = resolveCtfRoot(args);
  const launchArgs = removeOptions(args, ["--ctf-root"]);
  const env = { ...process.env };
  if (ctfRoot) env.CTF_ROOT = ctfRoot;
  run("bash", [path.join(PAYLOAD, "usr-local-bin", "ctf-codex"), ...launchArgs], { env });
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
  if (cmd === "install-tools") return installInventoryTools(rest);
  if (cmd === "health") return health();
  if (cmd === "update-skills") return updateSkills(rest);
  if (cmd === "install-launchers") {
    ensureUnix();
    return installWindowsLaunchersFromWsl();
  }
  if (cmd === "version" || cmd === "--version") {
    const pkg = require(path.join(ROOT, "package.json"));
    console.log(pkg.version);
    return;
  }
  launch(args);
}

main();
