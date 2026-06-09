# ctf-codex-toolkit

[![npm version](https://img.shields.io/npm/v/ctf-codex-toolkit.svg)](https://www.npmjs.com/package/ctf-codex-toolkit)
[![CI](https://github.com/nimosocute/ctf-codex-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/nimosocute/ctf-codex-toolkit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

CTF-focused Codex CLI setup for Kali WSL, packaged for npm.

This package installs a managed CTF policy, CTF skills/checklists/snippets, guard hooks, Browser Arm helper files, and Windows launchers for per-challenge workspaces under your chosen CTF root, using `<ctf-root>\_work\<challenge>`.

Primary command: `ctf-codex-toolkit`.

Compatibility aliases: `ctf-codex-workflow`, `ctf-codex-wsl`, `ctf-codex`.

## Install From npm

One-command setup after npm publish:

```powershell
npm exec --yes --package ctf-codex-toolkit -- ctf-codex-toolkit setup
```

Or install the command globally:

```powershell
npm install -g ctf-codex-toolkit
ctf-codex-toolkit setup
ctf-codex-toolkit <challenge_name>
```

Resume the last session for a challenge:

```powershell
ctf-codex-toolkit <challenge_name> -Resume
```

## Install From GitHub

One-command setup from GitHub:

```powershell
npm exec --yes --package github:nimosocute/ctf-codex-toolkit -- ctf-codex-toolkit setup
```

Or install the command globally from GitHub:

```powershell
npm install -g github:nimosocute/ctf-codex-toolkit
ctf-codex-toolkit setup
```

## Requirements

- Windows with WSL2
- A Kali WSL distro named `kali-linux`
- Node/npm on Windows
- Codex CLI installed and configured inside Kali WSL, available as `codex` on `PATH`

This package does not include, create, or overwrite `~/.codex/config.toml`. Keep your existing official OpenAI Codex config, or use any compatible third-party provider config yourself.

Use another distro name:

```powershell
ctf-codex-toolkit setup --distro kali-linux
ctf-codex-toolkit <challenge_name> --distro kali-linux
```

Use another challenge root:

```powershell
ctf-codex-toolkit <challenge_name> --ctf-root C:\CTF
```

During `setup` or `install`, the toolkit asks for a Windows CTF workspace root and stores it in `%USERPROFILE%\.ctf-codex-toolkit.json`. Press Enter to use the default `%USERPROFILE%\ctf-workspaces`, or pass `--ctf-root` to make setup non-interactive:

```powershell
ctf-codex-toolkit setup --ctf-root C:\CTF
```

The launcher also honors `CTF_CODEX_WSL_DISTRO`, `CTF_CODEX_ROOT`, `CTF_ROOT`, and `CODEX_BIN`. Explicit `--ctf-root` wins over environment variables and saved config.

## Commands

```text
ctf-codex-toolkit setup [--distro kali-linux] [--ctf-root <path>] [--no-browser-arm] [--skip-health]
ctf-codex-toolkit install [--distro kali-linux] [--ctf-root <path>] [--no-browser-arm]
ctf-codex-toolkit health [--distro kali-linux]
ctf-codex-toolkit update-skills [--distro kali-linux] [--source https://github.com/ljagiello/ctf-skills.git]
ctf-codex-toolkit install-launchers
ctf-codex-toolkit <challenge> [-Resume] [--distro kali-linux] [--ctf-root <path>]
```

`setup` runs `install` and then `health`. Use `--skip-health` when optional tools are not ready yet.

`install` copies the managed payload into Kali WSL:

- `~/.codex/AGENTS.md`
- `~/.codex/ctf-checklists.md`
- `~/.codex/ctf-snippets/`
- `~/.codex/skills/ctf-*`
- `~/.codex/skills/solve-challenge`
- `~/.codex/skills/ctf-writeup`
- `~/.codex/tools/ctf_health_check.py`
- `~/.codex/tools/browser_arm/browser_server.py`
- `/opt/codex-ctf-hooks/*`
- `/usr/local/bin/ctf-codex`

It also writes Windows launchers to `%USERPROFILE%\ctf-codex-wsl.ps1` and `%USERPROFILE%\ctf-codex-wsl.cmd`, then creates or updates a Desktop shortcut named `CTF Codex WSL.lnk` pointing to the CMD launcher. The Desktop path is resolved from Windows, so redirected Desktop folders such as OneDrive Desktop are supported.

It does **not** copy secrets, sessions, logs, cookies, `.env`, private keys, runtime SQLite state, or Codex provider configuration.

## Skill Credits and Updates

The bundled CTF skill directories are derived from [ljagiello/ctf-skills](https://github.com/ljagiello/ctf-skills.git). Credit for the upstream CTF skill content belongs to that project and its contributors.

This toolkit packages those skills together with the Windows/Kali WSL launcher, guard hooks, health check, snippets, and CTF workflow files so they can be installed in one command.

See `THIRD_PARTY_NOTICES.md` for the packaged third-party skill notice.

Automatic skill update from the upstream repository:

```powershell
ctf-codex-toolkit update-skills
```

Automatic update from a fork or compatible GitHub repo:

```powershell
ctf-codex-toolkit update-skills --source https://github.com/<owner>/<repo>.git
```

The updater runs inside Kali WSL, clones the source repository, finds skill directories containing `SKILL.md`, and refreshes matching CTF skill directories under:

```text
~/.codex/skills/
```

It updates directories named `ctf-*`, `solve-challenge`, and `ctf-writeup`. It does not delete unrelated user skills.

Manual update inside Kali WSL:

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

## Browser Arm

By default, `ctf-codex-toolkit setup` and `ctf-codex-toolkit install` create an isolated venv at:

```text
~/.codex/tools/browser_arm/.venv
```

and installs `cloakbrowser==0.3.31` there. CloakBrowser is a MIT-licensed browser automation project from [CloakHQ/CloakBrowser](https://github.com/CloakHQ/CloakBrowser). This toolkit uses it only for the optional Browser Arm helper, which gives Codex a local browser-control path for CTF web challenges that need JavaScript, DOM inspection, storage inspection, console logs, or network logs.

CloakBrowser is installed inside the isolated Browser Arm venv, not globally. On first use, CloakBrowser may download and cache its Chromium binary; upstream documents this as an automatic binary download. Use `--no-browser-arm` to skip this dependency entirely:

```powershell
ctf-codex-toolkit setup --no-browser-arm
```

## Supply Chain Notes

The preferred install path after npm publication is a versioned npm package:

```powershell
npm exec --yes --package ctf-codex-toolkit@0.1.0 -- ctf-codex-toolkit setup
```

The GitHub install form is convenient while the package is not yet published, but it executes the current repository content:

```powershell
npm exec --yes --package github:nimosocute/ctf-codex-toolkit -- ctf-codex-toolkit setup
```

Review the repository, pin to a trusted tag or commit when possible, and prefer signed/versioned releases for shared environments. CI runs `npm run smoke` and `npm pack --dry-run` on pushes and pull requests.

Contributor and publishing notes live in `CONTRIBUTING.md`.

## Safety Model

The pre-tool guard blocks high-risk automated attack commands and broad candidate searches, while allowing small deterministic loops. This is defense-in-depth for common mistakes; it is not a sandbox, not a security boundary, and not a substitute for running Codex inside a scoped CTF workspace.

Current regression checks include:

- `range(1<<20)` blocked
- `range(10**8)` blocked
- `range(100000000)` blocked
- `range(2**20)` blocked
- `range(2**10)` allowed
- small shell `for` allowed
- `hashcat` blocked
