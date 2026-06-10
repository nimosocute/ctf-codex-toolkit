# CTF Codex Toolkit

[![npm version](https://img.shields.io/npm/v/ctf-codex-toolkit.svg)](https://www.npmjs.com/package/ctf-codex-toolkit)
[![CI](https://github.com/nimosocute/ctf-codex-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/nimosocute/ctf-codex-toolkit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Node.js](https://img.shields.io/badge/node-%3E%3D18-339933.svg)](package.json)

CTF-focused Codex setup for Kali Linux and Kali WSL.

`ctf-codex-toolkit` is installed from a Kali shell, either on native Kali or inside Kali WSL. The installer auto-detects the environment:

- Kali native: installs the Linux-side Codex CTF toolkit only.
- Kali WSL: installs the same Kali-side toolkit and also restores the Windows launcher/shortcut workflow.

It installs the managed Codex CTF environment into Kali: skills, checklists, snippets, guard hooks, health checks, the required CTF tool inventory, optional browser automation helpers, and per-challenge launchers.

The intended workflow is:

```text
Kali shell
  -> npm exec --yes --package ctf-codex-toolkit@latest -- ctf-codex-toolkit setup
  -> auto-detect Kali native vs Kali WSL
  -> ~/.codex CTF payload
  -> required CTF tools from tools_inventory.md
  -> /opt/codex-ctf-hooks guard hooks
  -> WSL only: Windows launcher + Desktop shortcut
  -> ctf-codex-toolkit <challenge>
  -> ~/ctf-workspaces/_work/<challenge>
  -> codex inside Kali
```

## Table of Contents

- [What This Project Provides](#what-this-project-provides)
- [Install](#install)
- [Daily Usage](#daily-usage)
- [Requirements](#requirements)
- [How It Works](#how-it-works)
- [Command Reference](#command-reference)
- [Vietnamese Quick Guide](#vietnamese-quick-guide)
- [Installed Files](#installed-files)
- [Workspace Model](#workspace-model)
- [Skill Credits and Updates](#skill-credits-and-updates)
- [Browser Arm](#browser-arm)
- [Health Checks](#health-checks)
- [Safety Model](#safety-model)
- [Supply Chain Notes](#supply-chain-notes)
- [Contributing](#contributing)
- [License](#license)

## What This Project Provides

This repository packages the operational pieces needed to run Codex as a CTF assistant inside Kali.

| Area | Included |
| --- | --- |
| Codex CTF policy | Managed `AGENTS.md`, category routing, workflow guidance |
| Skills | Web, pwn, crypto, reverse, forensics, OSINT, malware, AI/ML, misc, solve dispatcher, writeup |
| Guard hooks | Pre-tool checks for broad scans, high-risk commands, and oversized candidate loops |
| Health checks | One-shot environment inventory for CTF tools, providers, Browser Arm, hooks |
| CTF tools | Required bootstrap for the tools listed in `tools_inventory.md` |
| Browser support | Optional isolated Browser Arm venv using pinned `cloakbrowser==0.3.31` |
| Launchers | `ctf-codex-toolkit <challenge>` and `/usr/local/bin/ctf-codex <challenge>` |
| WSL integration | When run inside Kali WSL, writes the Windows `.ps1`/`.cmd` launcher and Desktop shortcut |
| Workspace layout | Per-challenge directories under a user-selected CTF root |

The package intentionally does not ship Codex provider configuration. Users keep their own official OpenAI Codex config or compatible third-party config outside this repository.

## Install

All commands below run inside Kali Linux or Kali WSL.

Install prerequisites if they are missing:

```bash
sudo apt update
sudo apt install -y nodejs npm python3 python3-venv git sudo
```

Verify Codex CLI is available inside Kali:

```bash
codex --version
```

Run setup:

```bash
npm exec --yes --package ctf-codex-toolkit@latest -- ctf-codex-toolkit setup
```

For a pinned install:

```bash
npm exec --yes --package ctf-codex-toolkit@0.1.22 -- ctf-codex-toolkit setup
```

Or install the CLI globally inside Kali:

```bash
npm install -g ctf-codex-toolkit
ctf-codex-toolkit setup
```

Start a challenge session:

```bash
ctf-codex-toolkit my_challenge
```

Resume the last session for a challenge:

```bash
ctf-codex-toolkit my_challenge -Resume
```

Install directly from GitHub when testing unreleased changes:

```bash
npm exec --yes --package github:nimosocute/ctf-codex-toolkit -- ctf-codex-toolkit setup
```

## Daily Usage

Most users do not need a global npm install. The recommended pattern is:

1. Run setup or update with `npm exec`.
2. Start daily challenge sessions from the installed launcher.
3. Use `npm exec` again only when updating or repairing the toolkit.

Check the published latest version:

```bash
npm view ctf-codex-toolkit version
```

Check the version installed by setup:

```bash
cat ~/.ctf-codex-toolkit.json
```

Check the Windows WSL launcher version:

```bash
grep 'LauncherVersion' /mnt/c/Users/$USER/ctf-codex-wsl.ps1 2>/dev/null || \
grep 'LauncherVersion' /mnt/c/Users/*/ctf-codex-wsl.ps1
```

Update the Kali payload and Windows WSL shortcut without reinstalling the full tool inventory:

```bash
npm exec --yes --package ctf-codex-toolkit@latest -- ctf-codex-toolkit setup --skip-health --skip-tools
```

Start a challenge from Kali native or Kali WSL:

```bash
ctf-codex <challenge>
```

Resume the last session for that challenge:

```bash
ctf-codex <challenge> -Resume
```

Run a health check after changing tools, PATH, Node.js, Python, Codex, or WSL:

```bash
npm exec --yes --package ctf-codex-toolkit@latest -- ctf-codex-toolkit health
```

If you want the `ctf-codex-toolkit` command available directly, install it globally inside Kali:

```bash
npm config set prefix ~/.npm-global
mkdir -p ~/.npm-global/bin
echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
npm install -g ctf-codex-toolkit
ctf-codex-toolkit --version
```

This global install affects only Kali/WSL when `which npm` points to a Linux path such as `/usr/bin/npm`. It does not update Windows npm unless you run npm from Windows PowerShell/CMD.

## Requirements

- Kali Linux or Kali WSL
- Node.js/npm inside Kali
- Python 3 and `python3-venv`
- Git
- `sudo` for installing `/opt/codex-ctf-hooks/*` and `/usr/local/bin/ctf-codex`
- Codex CLI installed inside Kali and available as `codex`

This package does not install Kali Linux, WSL, or Codex CLI. It configures an existing Kali environment for CTF-focused Codex workflows.

When setup is run inside Kali WSL and Windows interop is available, it also writes:

```text
%USERPROFILE%\ctf-codex-wsl.ps1
%USERPROFILE%\ctf-codex-wsl.cmd
Desktop\CTF Codex WSL.lnk
```

Kali native installs skip those Windows files automatically.

Use a non-default CTF root:

```bash
ctf-codex-toolkit setup --ctf-root ~/ctf
ctf-codex-toolkit my_challenge --ctf-root ~/ctf
```

During `setup` or `install`, the CLI asks where to place the CTF workspace root and stores the answer in:

```text
~/.ctf-codex-toolkit.json
```

Press Enter to use:

```text
~/ctf-workspaces
```

The launcher also honors:

- `CTF_CODEX_ROOT`
- `CTF_ROOT`
- `CODEX_BIN`

Explicit CLI flags take precedence over environment variables and saved config.

## How It Works

```mermaid
flowchart LR
    A["Kali shell"] --> B["npm exec ctf-codex-toolkit setup"]
    B --> C{"Kali WSL?"}
    C -->|No| D["Install Kali-native toolkit"]
    C -->|Yes| E["Install Kali toolkit + Windows launchers"]
    D --> F["~/.codex + /opt hooks + ctf-codex"]
    E --> F
    F --> G["Run health checks"]
    G --> H["ctf-codex-toolkit <challenge>"]
    H --> I["~/ctf-workspaces/_work/<challenge>"]
    I --> J["codex inside Kali"]
```

Setup performs five jobs:

1. Copy the managed payload into `~/.codex`.
2. Install guard hooks and the `ctf-codex` launcher locally in Kali.
3. Install and verify the CTF tools mapped from `tools_inventory.md`, unless skipped.
4. Prepare optional helper environments, including Browser Arm unless skipped.
5. In Kali WSL only, install the Windows launcher files and Desktop shortcut.

The tool install is required by default. It uses Kali apt first, then fallback installers for inventory tools that are commonly absent from minimal Kali:

- `/opt/codex-ctf-python` venv for Python CTF libraries when apt packages are missing.
- `/opt/oss-cad-suite` for `yosys` and `bitwuzla`.
- `/opt/codex-ctf-sage` via micromamba for SageMath if apt does not provide `sage`.
- Go fallback for `ffuf` if the apt package is unavailable.
- Chromium runtime libraries plus the isolated Browser Arm venv for `cloakbrowser==0.3.31`.

After bootstrap, setup runs the health check. If any inventory tool is still missing, setup exits with a real error instead of reporting a clean install.

After setup, challenge sessions run under:

```text
<ctf-root>/_work/<challenge>
```

## Command Reference

```text
ctf-codex-toolkit setup [--ctf-root <path>] [--no-browser-arm] [--skip-tools] [--skip-health]
ctf-codex-toolkit install [--ctf-root <path>] [--no-browser-arm] [--skip-tools]
ctf-codex-toolkit install-tools
ctf-codex-toolkit health
ctf-codex-toolkit update-skills [--source https://github.com/ljagiello/ctf-skills.git]
ctf-codex-toolkit install-launchers
ctf-codex-toolkit <challenge> [-Resume] [--ctf-root <path>]
ctf-codex <challenge> [-Resume] [--ctf-root <path>]
```

Compatibility aliases:

```text
ctf-codex-workflow
ctf-codex-wsl
ctf-codex
```

`setup` is the usual entry point. It runs `install` and then `health`.

Use `--skip-health` when optional tools are not installed yet:

```bash
ctf-codex-toolkit setup --skip-health
```

Use `--skip-tools` to install only the Codex payload, hooks, launchers, and optional Browser Arm without installing the full CTF inventory:

```bash
ctf-codex-toolkit setup --skip-tools
```

Install or repair only the tool inventory later:

```bash
ctf-codex-toolkit install-tools
```

Use `--no-browser-arm` to skip Browser Arm entirely:

```bash
ctf-codex-toolkit setup --no-browser-arm
```

Use `install-launchers` inside Kali WSL to recreate only the Windows launcher files and Desktop shortcut:

```bash
ctf-codex-toolkit install-launchers
```

When the Windows shortcut is launched from Kali WSL, it checks the published npm `latest` version. If a newer toolkit version is available, the launcher prompts:

```text
Update available! <current> -> <latest>

> 1. Update now
  2. Skip
  3. Skip until next version
```

Choosing update refreshes the toolkit payload, launchers, and saved toolkit version in Kali WSL, then continues launching the challenge. It skips the full CTF tool inventory install; run `ctf-codex-toolkit install-tools` when you want to repair or reinstall tools. The Windows launcher has its own embedded `LauncherVersion`, so stale shortcut files are detected even if the WSL config already contains a newer toolkit version.

If Codex fails before opening, the Windows launcher keeps the console open and prints the WSL exit code. Common causes are Codex CLI not installed inside Kali, `codex` missing from the WSL `PATH`, or a bad WSL distro name.

## Vietnamese Quick Guide

### Cai dat / cap nhat

Chay trong Kali native hoac Kali WSL:

```bash
npm exec --yes --package ctf-codex-toolkit@latest -- ctf-codex-toolkit setup
```

Neu chi muon cap nhat payload va shortcut, khong cai lai bo tool CTF nang:

```bash
npm exec --yes --package ctf-codex-toolkit@latest -- ctf-codex-toolkit setup --skip-health --skip-tools
```

Lenh `npm exec` chi tai package tam thoi de chay setup. Sau khi setup xong, toolkit da duoc ghi vao:

```text
~/.codex/
~/.ctf-codex-toolkit.json
/opt/codex-ctf-hooks/
/usr/local/bin/ctf-codex
```

Neu dang o Kali WSL, setup cung ghi shortcut phia Windows:

```text
%USERPROFILE%\ctf-codex-wsl.ps1
%USERPROFILE%\ctf-codex-wsl.cmd
Desktop\CTF Codex WSL.lnk
```

### Su dung hang ngay

Mo challenge moi:

```bash
ctf-codex ten_challenge
```

Resume challenge cu:

```bash
ctf-codex ten_challenge -Resume
```

Workspace mac dinh nam o:

```text
~/ctf-workspaces/_work/ten_challenge
```

Tren Windows shortcut, nhap ten challenge khi duoc hoi. Launcher se tao workspace, tao `AGENTS.md`, cai guard trong workspace, roi mo Codex ben trong Kali WSL.

### Kiem tra version

Version moi nhat tren npm:

```bash
npm view ctf-codex-toolkit version
```

Version da setup trong Kali:

```bash
cat ~/.ctf-codex-toolkit.json
```

Version cua Windows WSL shortcut:

```bash
grep 'LauncherVersion' /mnt/c/Users/*/ctf-codex-wsl.ps1
```

Neu `ctf-codex-toolkit --version` bao `command not found` thi khong sao. Dieu do chi co nghia la ban dung `npm exec`, chua cai CLI global. Shortcut va `ctf-codex` van co the dung neu setup da thanh cong.

### Global install la gi?

Global install chi can neu ban muon go truc tiep:

```bash
ctf-codex-toolkit --version
ctf-codex-toolkit health
ctf-codex-toolkit setup
```

Neu can cai global trong Kali ma gap loi `EACCES`, doi npm prefix ve thu muc user:

```bash
npm config set prefix ~/.npm-global
mkdir -p ~/.npm-global/bin
echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
npm install -g ctf-codex-toolkit
```

Global install trong Kali WSL khong anh huong npm Windows, mien la `which npm` tro den Linux path nhu `/usr/bin/npm`.

### Loi hay gap

Neu WSL bao Codex dang tro den `/mnt/c/.../codex`, nghia la no dang bat nham Codex Windows. Cai Codex CLI trong Kali:

```bash
npm config set prefix ~/.npm-global
mkdir -p ~/.npm-global/bin
echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
npm install -g @openai/codex
which codex
codex --version
```

Ket qua dung khong duoc la `/mnt/c/...`; nen la duong dan Linux nhu:

```text
/home/<user>/.npm-global/bin/codex
```

## Installed Files

Inside Kali, `install` writes:

```text
~/.codex/AGENTS.md
~/.codex/ctf-checklists.md
~/.codex/ctf-snippets/
~/.codex/skills/ctf-*
~/.codex/skills/solve-challenge
~/.codex/skills/ctf-writeup
~/.codex/tools/ctf_health_check.py
~/.codex/tools/browser_arm/browser_server.py
~/.codex/tools/browser_arm/browser_client.py
~/.ctf-codex-toolkit.json
/opt/codex-ctf-hooks/*
/usr/local/bin/ctf-codex
```

Inside Kali WSL only, setup also writes Windows-side launcher files through Windows interop:

```text
%USERPROFILE%\ctf-codex-wsl.ps1
%USERPROFILE%\ctf-codex-wsl.cmd
Desktop\CTF Codex WSL.lnk
```

The installer does not copy:

- `~/.codex/config.toml`
- provider keys
- API tokens
- sessions
- logs
- cookies
- `.env` files
- private keys
- runtime SQLite state

The installer writes hook executables under `/opt/codex-ctf-hooks` and symlinks them into `~/.codex/hooks`. It intentionally does not rewrite `~/.codex/config.toml`, because provider and runtime config is user-owned. Verify that your Codex runtime loads hooks from `~/.codex/hooks`; if your Codex build requires explicit hook registration in `config.toml`, register:

```text
/opt/codex-ctf-hooks/ctf_pre_tool_guard.py
/opt/codex-ctf-hooks/ctf_post_tool_guard.py
/opt/codex-ctf-hooks/ctf_stop_guard.py
```

## Workspace Model

The CTF root is selected during setup. A challenge named `web_login` creates or uses:

```text
~/ctf-workspaces/_work/web_login
```

That directory becomes the working directory for Codex.

Example:

```bash
ctf-codex-toolkit web_login
ctf-codex-toolkit web_login -Resume
```

## Skill Credits and Updates

The bundled CTF skill directories are derived from [ljagiello/ctf-skills](https://github.com/ljagiello/ctf-skills.git). Credit for the upstream CTF skill content belongs to that project and its contributors.

This toolkit packages those skills with Kali launchers, guard hooks, health checks, snippets, and CTF workflow files.

Automatic update from upstream:

```bash
ctf-codex-toolkit update-skills
```

Automatic update from a fork or compatible repository:

```bash
ctf-codex-toolkit update-skills --source https://github.com/<owner>/<repo>.git
```

The updater runs inside Kali, clones the source repository, finds skill directories containing `SKILL.md`, and refreshes matching CTF skill directories under:

```text
~/.codex/skills/
```

It updates directories named `ctf-*`, `solve-challenge`, and `ctf-writeup`. It does not delete unrelated user skills.

Manual update inside Kali:

```bash
tmp="$(mktemp -d)"
git clone --depth 1 https://github.com/ljagiello/ctf-skills.git "$tmp/ctf-skills"
mkdir -p ~/.codex/skills
find "$tmp/ctf-skills" -mindepth 1 -maxdepth 3 -name SKILL.md -type f -print |
while read -r skill_file; do
  skill_dir="$(dirname "$skill_file")"
  name="$(basename "$skill_dir")"
  case "$name" in
    ctf-*|solve-challenge|ctf-writeup)
      rm -rf "$HOME/.codex/skills/$name"
      cp -a "$skill_dir" "$HOME/.codex/skills/$name"
      ;;
  esac
done
rm -rf "$tmp"
```

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Browser Arm

By default, `setup` and `install` create an isolated venv at:

```text
~/.codex/tools/browser_arm/.venv
```

and install:

```text
cloakbrowser==0.3.31
```

CloakBrowser is a MIT-licensed browser automation project from [CloakHQ/CloakBrowser](https://github.com/CloakHQ/CloakBrowser). This toolkit uses it only for optional Browser Arm workflows: JavaScript execution, DOM inspection, storage inspection, console logs, and network logs during CTF web challenges.

CloakBrowser is installed inside the isolated Browser Arm venv, not globally. On first use, CloakBrowser may download and cache its Chromium binary.

The Browser Arm server binds to `127.0.0.1` and requires a local shared token. By default the server creates `.browser_token` in `BROWSER_WORKDIR` and the bundled client reads it automatically. You can also set `BROWSER_TOKEN` or `BROWSER_TOKEN_FILE` explicitly when starting both processes.

Minimal Kali installs may not include all Chromium shared libraries. If `ctf-codex-toolkit health` reports a Browser Arm error such as `libnspr4.so: cannot open shared object file`, install the browser runtime dependencies:

```bash
sudo apt install -y libnspr4 libnss3 libatk-bridge2.0-0 libgtk-3-0 libgbm1 libxkbcommon0
```

Skip this dependency:

```bash
ctf-codex-toolkit setup --no-browser-arm
```

## Health Checks

Run inside Kali:

```bash
ctf-codex-toolkit health
```

The health check verifies the installed CTF payload, selected tools, provider readiness signals, Browser Arm files, and hook availability. It is meant to catch broken or inconsistent setup state quickly after installation.

On minimal Kali, `setup` installs and verifies the inventory tools first, including pwn, reverse, forensics, web fuzzing, cracking, hardware helpers, and Chromium runtime libraries used by Browser Arm. Large packages such as `sagemath`, `ghidra`, `python3-angr`, and oss-cad-suite may take time and disk space.

## Safety Model

The pre-tool guard blocks high-risk automated attack commands and broad candidate searches while allowing small deterministic loops. Path containment checks canonicalize paths before comparison, so `..` traversal through patch/edit/write targets is rejected before tools run.

This is defense-in-depth for common mistakes. It is not a sandbox, not a security boundary, and not a substitute for running Codex inside a scoped CTF workspace. Static script scanning is best-effort: inline `python -c`/`node -e` payloads and script files are inspected, but code supplied through pipes or heredocs is not fully parsed before interpreter startup.

Current regression checks include:

- `range(1<<20)` blocked
- `range(10**8)` blocked
- `range(100000000)` blocked
- `range(2**20)` blocked
- `range(2**10)` allowed
- small shell `for` loops allowed
- `hashcat` blocked

## Supply Chain Notes

Prefer the published npm package for normal installation:

```bash
npm exec --yes --package ctf-codex-toolkit@0.1.22 -- ctf-codex-toolkit setup
```

The GitHub install form executes repository content directly:

```bash
npm exec --yes --package github:nimosocute/ctf-codex-toolkit -- ctf-codex-toolkit setup
```

For shared or sensitive environments:

- Review the repository before running setup.
- Pin npm versions, Git tags, or Git commits where practical.
- Prefer the npm package over mutable GitHub branch installs.
- Run `npm run smoke` when modifying the package locally.

CI runs `npm run smoke` and `npm pack --dry-run` on pushes and pull requests.

## Contributing

Contributor and release notes live in [CONTRIBUTING.md](CONTRIBUTING.md).

Development checks:

```bash
npm run smoke
npm pack --dry-run
```

## License

[MIT](LICENSE)
