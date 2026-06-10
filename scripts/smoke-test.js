#!/usr/bin/env node
const fs = require("node:fs");
const path = require("node:path");
const childProcess = require("node:child_process");
const os = require("node:os");

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
if (!windowsLauncher.includes('$LauncherVersion = "') || !windowsLauncher.includes("Invoke-ToolkitUpdateCheck -Distro $WSL_DISTRO -LauncherVersion $LauncherVersion")) {
  console.error("Windows launcher must compare its embedded launcher version during update checks");
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
if (
  !windowsLauncher.includes("\":Users\"") ||
  !windowsLauncher.includes("$normalizedPath = Resolve-WindowsFullPath $WindowsPath") ||
  !windowsLauncher.includes("/mnt/$drive/$tail")
) {
  console.error("Windows launcher path repair/fallback markers are missing");
  process.exit(1);
}
if (
  !windowsLauncher.includes("find_linux_codex()") ||
  !windowsLauncher.includes("WINDOWS_CODEX_PATH") ||
  !windowsLauncher.includes("npm install -g @openai/codex")
) {
  console.error("Windows launcher must fallback-search Linux Codex and explain WSL install steps");
  process.exit(1);
}
if (!windowsLauncher.includes("preflight-codex.sh") || !windowsLauncher.includes("Codex exited successfully but too quickly")) {
  console.error("Windows launcher must preflight Codex and diagnose quick successful exits");
  process.exit(1);
}
if (
  !windowsLauncher.includes('exec "`$CODEX_EXE"') ||
  !windowsLauncher.includes('launch-codex.sh') ||
  !windowsLauncher.includes('"--exec", "bash", "-li", $LaunchScriptWsl')
) {
  console.error("Windows launcher must exec Codex through an interactive WSL shell script");
  process.exit(1);
}
if (windowsLauncher.includes('"--exec", "bash", "-li", "-c"')) {
  console.error("Windows launcher must not pass long launch scripts through bash -li -c");
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

const python = process.env.PYTHON || "python";
const hookPath = path.join(root, "payload/opt-hooks/ctf_pre_tool_guard.py");
const guardTmp = fs.mkdtempSync(path.join(os.tmpdir(), "ctf-guard-"));
const ctfRoot = path.join(guardTmp, "ctf");
const challengeRoot = path.join(ctfRoot, "_work", "chal");
fs.mkdirSync(challengeRoot, { recursive: true });

function runGuard(event) {
  return childProcess.spawnSync(python, [hookPath], {
    cwd: challengeRoot,
    env: {
      ...process.env,
      CTF_ROOT: ctfRoot,
      CTF_WORK_ROOT: path.join(ctfRoot, "_work")
    },
    input: JSON.stringify(event),
    encoding: "utf8"
  });
}

const traversalPatch = runGuard({
  tool_name: "apply_patch",
  cwd: challengeRoot,
  tool_input: {
    command: "*** Begin Patch\n*** Add File: foo/../../outside\n+bad\n*** End Patch\n"
  }
});
if (traversalPatch.status === 0 || !`${traversalPatch.stderr}${traversalPatch.stdout}`.includes("outside current challenge workspace")) {
  console.error("pre-tool guard must reject normalized apply_patch path traversal");
  console.error(traversalPatch.stdout);
  console.error(traversalPatch.stderr);
  process.exit(1);
}

const safePatch = runGuard({
  tool_name: "apply_patch",
  cwd: challengeRoot,
  tool_input: {
    command: "*** Begin Patch\n*** Add File: work/note.txt\n+ok\n*** End Patch\n"
  }
});
if (safePatch.status !== 0) {
  console.error("pre-tool guard rejected a safe workspace patch");
  console.error(safePatch.stdout);
  console.error(safePatch.stderr);
  process.exit(1);
}

fs.rmSync(guardTmp, { recursive: true, force: true });

const browserServer = fs.readFileSync(path.join(root, "payload/home-codex/tools/browser_arm/browser_server.py"), "utf8");
const browserClient = fs.readFileSync(path.join(root, "payload/home-codex/tools/browser_arm/browser_client.py"), "utf8");
if (!browserServer.includes("BROWSER_TOKEN") || !browserServer.includes("Unauthorized browser control request") || !browserClient.includes("load_token")) {
  console.error("Browser Arm client/server must enforce a local shared token");
  process.exit(1);
}

console.log("smoke ok");
