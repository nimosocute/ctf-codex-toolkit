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
  "payload/home-codex/ctf-snippets/raw_http_socket.py",
  "payload/home-codex/ctf-snippets/binary_sample_triage.py",
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

const packageJson = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
if (packageJson.bin && Object.prototype.hasOwnProperty.call(packageJson.bin, "ctf-codex")) {
  console.error("npm package must not install a ctf-codex bin; setup owns /usr/local/bin/ctf-codex");
  process.exit(1);
}
const cliSource = fs.readFileSync(path.join(root, "bin/ctf-codex-toolkit.js"), "utf8");
if (
  !cliSource.includes("function uninstall(") ||
  !cliSource.includes('cmd === "uninstall"') ||
  !cliSource.includes("--remove-workspaces") ||
  !cliSource.includes(".ctf-codex-toolkit.json") ||
  !cliSource.includes("function windowsUninstallScript(") ||
  !cliSource.includes('.join("\\n")') ||
  !cliSource.includes("Preserved ~/.codex/auth.json")
) {
  console.error("CLI must expose a safe uninstall command that preserves Codex auth/session state");
  process.exit(1);
}

const windowsLauncher = fs.readFileSync(path.join(root, "payload/windows-launchers/ctf-codex-wsl.ps1"), "utf8");
const agentsPolicy = fs.readFileSync(path.join(root, "payload/home-codex/AGENTS.md"), "utf8");
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
const updateCheckCall = windowsLauncher.indexOf("Invoke-ToolkitUpdateCheck -Distro");
const rootPrompt = windowsLauncher.indexOf("CTF workspace root on Windows");
const challengePrompt = windowsLauncher.indexOf("Challenge name (folder under _work)");
if (updateCheckCall < 0 || rootPrompt < 0 || challengePrompt < 0 || updateCheckCall > rootPrompt || updateCheckCall > challengePrompt) {
  console.error("Windows launcher update prompt must run before root/challenge folder prompts");
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
if (!windowsLauncher.includes("work/exploit.py") || !windowsLauncher.includes("base64 < path")) {
  console.error("Windows launcher workspace AGENTS must enforce file-based exploit execution and base64-first file inspection");
  process.exit(1);
}
if (!agentsPolicy.includes("work/exploit.py") || !agentsPolicy.includes("Base64/Hex")) {
  console.error("Global AGENTS policy must mention file-based exploit execution and Base64/Hex handling");
  process.exit(1);
}
if (!agentsPolicy.includes("contextual fuzzing") || !agentsPolicy.includes("rabbit hole")) {
  console.error("Global AGENTS policy must mention contextual fuzzing and rabbit-hole handling");
  process.exit(1);
}
if (!agentsPolicy.includes("CTF_STRICT_SCOPE=1") || !agentsPolicy.includes("tools that are not available in apt")) {
  console.error("Global AGENTS policy must allow default internet access, strict scope opt-in, and non-apt local tools");
  process.exit(1);
}
if (!windowsLauncher.includes("CTF_STRICT_SCOPE=1") || !windowsLauncher.includes("tools not available in apt")) {
  console.error("Windows launcher workspace AGENTS must allow default internet access and non-apt local tools");
  process.exit(1);
}

const help = childProcess.spawnSync(process.execPath, [path.join(root, "bin/ctf-codex-toolkit.js"), "--help"], {
  encoding: "utf8"
});
if (
  help.status !== 0 ||
  !help.stdout.includes("ctf-codex-toolkit setup") ||
  !help.stdout.includes("ctf-codex-toolkit install") ||
  !help.stdout.includes("ctf-codex-toolkit uninstall")
) {
  console.error(help.stdout);
  console.error(help.stderr);
  process.exit(1);
}

const python = process.env.PYTHON || "python";
const hookPath = path.join(root, "payload/opt-hooks/ctf_pre_tool_guard.py");
const stopHookPath = path.join(root, "payload/opt-hooks/ctf_stop_guard.py");
const guardTmp = fs.mkdtempSync(path.join(os.tmpdir(), "ctf-guard-"));
const ctfRoot = path.join(guardTmp, "ctf");
const challengeRoot = path.join(ctfRoot, "_work", "chal");
fs.mkdirSync(challengeRoot, { recursive: true });

function runGuard(event, extraEnv = {}) {
  return childProcess.spawnSync(python, [hookPath], {
    cwd: challengeRoot,
    env: {
      ...process.env,
      CTF_ROOT: ctfRoot,
      CTF_WORK_ROOT: path.join(ctfRoot, "_work"),
      ...extraEnv
    },
    input: JSON.stringify(event),
    encoding: "utf8"
  });
}

function runStopHook(cwd) {
  return childProcess.spawnSync(python, [stopHookPath], {
    cwd,
    env: {
      ...process.env,
      CTF_ROOT: ctfRoot,
      CTF_WORK_ROOT: path.join(ctfRoot, "_work"),
      HOME: path.join(guardTmp, "home"),
      USERPROFILE: path.join(guardTmp, "home")
    },
    input: JSON.stringify({ cwd }),
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

const wslCaseMismatchPatch = runGuard({
  tool_name: "apply_patch",
  cwd: "/mnt/d/CTF/_work/chal",
  tool_input: {
    command: "*** Begin Patch\n*** Add File: work/case-note.txt\n+ok\n*** End Patch\n"
  }
}, {
  CTF_ROOT: "/mnt/d/ctf",
  CTF_WORK_ROOT: "/mnt/d/ctf/_work"
});
if (wslCaseMismatchPatch.status !== 0) {
  console.error("pre-tool guard should tolerate casing differences on WSL Windows mounts such as /mnt/d/ctf vs /mnt/d/CTF");
  console.error(wslCaseMismatchPatch.stdout);
  console.error(wslCaseMismatchPatch.stderr);
  process.exit(1);
}

const inlineCurlPayload = runGuard({
  tool_name: "Bash",
  cwd: challengeRoot,
  tool_input: {
    command: "curl -s -H 'X-Test: payload' 'http://127.0.0.1:8000/'"
  }
});
if (inlineCurlPayload.status === 0 || !`${inlineCurlPayload.stderr}${inlineCurlPayload.stdout}`.includes("inline HTTP payload request")) {
  console.error("pre-tool guard must reject inline curl payload requests");
  console.error(inlineCurlPayload.stdout);
  console.error(inlineCurlPayload.stderr);
  process.exit(1);
}

const inlinePythonExploit = runGuard({
  tool_name: "Bash",
  cwd: challengeRoot,
  tool_input: {
    command: "timeout 10s python3 -c \"import requests; requests.get('http://127.0.0.1:8000/')\""
  }
});
if (inlinePythonExploit.status === 0 || !`${inlinePythonExploit.stderr}${inlinePythonExploit.stdout}`.includes("work/exploit.py")) {
  console.error("pre-tool guard must reject inline interpreter exploit code");
  console.error(inlinePythonExploit.stdout);
  console.error(inlinePythonExploit.stderr);
  process.exit(1);
}

const directSensitiveRead = runGuard({
  tool_name: "Bash",
  cwd: challengeRoot,
  tool_input: {
    command: "cat /etc/passwd"
  }
});
if (directSensitiveRead.status === 0 || !`${directSensitiveRead.stderr}${directSensitiveRead.stdout}`.includes("Encode the output first")) {
  console.error("pre-tool guard must reject direct sensitive local file reads");
  console.error(directSensitiveRead.stdout);
  console.error(directSensitiveRead.stderr);
  process.exit(1);
}

const encodedSensitiveRead = runGuard({
  tool_name: "Bash",
  cwd: challengeRoot,
  tool_input: {
    command: "cat /etc/passwd | base64"
  }
});
if (encodedSensitiveRead.status !== 0) {
  console.error("pre-tool guard should allow encoded sensitive file reads");
  console.error(encodedSensitiveRead.stdout);
  console.error(encodedSensitiveRead.stderr);
  process.exit(1);
}

const unscopedNetworkAllowed = runGuard({
  tool_name: "Bash",
  cwd: challengeRoot,
  tool_input: {
    command: "curl -s https://raw.githubusercontent.com/nimosocute/ctf-codex-toolkit/main/README.md"
  }
});
if (unscopedNetworkAllowed.status !== 0) {
  console.error("pre-tool guard should allow internet access by default without declared scope");
  console.error(unscopedNetworkAllowed.stdout);
  console.error(unscopedNetworkAllowed.stderr);
  process.exit(1);
}

const strictUnscopedNetwork = runGuard({
  tool_name: "Bash",
  cwd: challengeRoot,
  tool_input: {
    command: "curl -s https://raw.githubusercontent.com/nimosocute/ctf-codex-toolkit/main/README.md"
  }
}, { CTF_STRICT_SCOPE: "1" });
if (strictUnscopedNetwork.status === 0 || !`${strictUnscopedNetwork.stderr}${strictUnscopedNetwork.stdout}`.includes("CTF_STRICT_SCOPE=1")) {
  console.error("pre-tool guard should enforce declared scope only when CTF_STRICT_SCOPE=1");
  console.error(strictUnscopedNetwork.stdout);
  console.error(strictUnscopedNetwork.stderr);
  process.exit(1);
}

const scopedInlineNetwork = runGuard({
  tool_name: "Bash",
  cwd: challengeRoot,
  tool_input: {
    command: "CTF_STRICT_SCOPE=1 CTF_SCOPE=raw.githubusercontent.com curl -s https://raw.githubusercontent.com/nimosocute/ctf-codex-toolkit/main/README.md"
  }
});
if (scopedInlineNetwork.status !== 0) {
  console.error("pre-tool guard should allow one-shot CTF_SCOPE under strict scope mode");
  console.error(scopedInlineNetwork.stdout);
  console.error(scopedInlineNetwork.stderr);
  process.exit(1);
}

const nestedWorkDir = path.join(challengeRoot, "work");
fs.mkdirSync(nestedWorkDir, { recursive: true });
fs.writeFileSync(path.join(challengeRoot, "scope.txt"), "raw.githubusercontent.com\n");
const rootScopeFromNestedCwd = runGuard({
  tool_name: "Bash",
  cwd: nestedWorkDir,
  tool_input: {
    command: "curl -s https://raw.githubusercontent.com/nimosocute/ctf-codex-toolkit/main/README.md"
  }
}, { CTF_STRICT_SCOPE: "1" });
if (rootScopeFromNestedCwd.status !== 0) {
  console.error("pre-tool guard should load root workspace scope.txt from nested working directories under strict scope mode");
  console.error(rootScopeFromNestedCwd.stdout);
  console.error(rootScopeFromNestedCwd.stderr);
  process.exit(1);
}

const waitingLog = [
  "# solve_log",
  "## Known facts",
  "- Blocker: no artifact, no URL, no host, and no port provided yet.",
  "## Hypotheses",
  "| id | surface | hypothesis | next test | finding | status |",
  "| H1 | input | user must provide challenge artifact or URL | ask user for input | no target available | STUCK |",
  "## Failed paths / Do Not Repeat",
  "- Do not fabricate target scope or scan unrelated hosts.",
  "## Next best test",
  "- Waiting for user input."
].join("\n");
fs.writeFileSync(path.join(challengeRoot, "solve_log.md"), waitingLog + "\n");
for (let i = 0; i < 4; i += 1) {
  const waitingResult = runStopHook(challengeRoot);
  if (waitingResult.status !== 0 || `${waitingResult.stdout}${waitingResult.stderr}`.includes("findings/hypothesis signal has not changed")) {
    console.error("stop hook should not block repeated stops when solve_log records a real missing-input blocker");
    console.error(waitingResult.stdout);
    console.error(waitingResult.stderr);
    process.exit(1);
  }
}

const staleRoot = path.join(ctfRoot, "_work", "stale");
fs.mkdirSync(staleRoot, { recursive: true });
const staleLog = [
  "# solve_log",
  "## Known facts",
  "- Endpoint responds, but current hypothesis has not changed.",
  "## Hypotheses",
  "| id | surface | hypothesis | next test | finding | status |",
  "| H1 | web | route may expose flag | repeat same request | same result | active |",
  "## Failed paths / Do Not Repeat",
  "- None yet.",
  "## Next best test",
  "- Repeat same request."
].join("\n");
fs.writeFileSync(path.join(staleRoot, "solve_log.md"), staleLog + "\n");
let staleResult = null;
for (let i = 0; i < 3; i += 1) {
  staleResult = runStopHook(staleRoot);
}
if (!staleResult || !`${staleResult.stdout}${staleResult.stderr}`.includes("findings/hypothesis signal has not changed")) {
  console.error("stop hook should still block genuinely stale non-waiting solve logs");
  if (staleResult) {
    console.error(staleResult.stdout);
    console.error(staleResult.stderr);
  }
  process.exit(1);
}

fs.rmSync(guardTmp, { recursive: true, force: true });

const browserServer = fs.readFileSync(path.join(root, "payload/home-codex/tools/browser_arm/browser_server.py"), "utf8");
const browserClient = fs.readFileSync(path.join(root, "payload/home-codex/tools/browser_arm/browser_client.py"), "utf8");
if (!browserServer.includes("BROWSER_TOKEN") || !browserServer.includes("Unauthorized browser control request") || !browserClient.includes("load_token")) {
  console.error("Browser Arm client/server must enforce a local shared token");
  process.exit(1);
}

const requestsExploit = fs.readFileSync(path.join(root, "payload/home-codex/ctf-snippets/requests_exploit.py"), "utf8");
if (
  !requestsExploit.includes("PAYLOAD_ENCODING") ||
  !requestsExploit.includes("saved_base64") ||
  !requestsExploit.includes("body_base64_preview")
) {
  console.error("requests_exploit.py must expose payload encoding and base64 response capture");
  process.exit(1);
}

const rawHttpSocket = fs.readFileSync(path.join(root, "payload/home-codex/ctf-snippets/raw_http_socket.py"), "utf8");
if (!rawHttpSocket.includes("Transfer-Encoding: chunked ") || !rawHttpSocket.includes("Edit REQUEST")) {
  console.error("raw_http_socket.py must preserve literal header mutation workflow");
  process.exit(1);
}

const binarySampleTriage = fs.readFileSync(path.join(root, "payload/home-codex/ctf-snippets/binary_sample_triage.py"), "utf8");
if (
  !binarySampleTriage.includes("null_bytes") ||
  !binarySampleTriage.includes("differing_offsets") ||
  !binarySampleTriage.includes("struct alignment")
) {
  console.error("binary_sample_triage.py must report null-byte and offset-structure hints");
  process.exit(1);
}

console.log("smoke ok");
