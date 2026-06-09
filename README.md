# ctf-codex-toolkit

CTF-focused Codex CLI setup for Kali WSL, packaged for npm.

This package installs a managed CTF policy, CTF skills/checklists/snippets, guard hooks, Browser Arm helper files, and Windows launchers for per-challenge workspaces under `D:\CTF\_work\<challenge>`.

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
ctf-codex-toolkit baby_bof
```

Resume the last session for a challenge:

```powershell
ctf-codex-toolkit baby_bof -Resume
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
ctf-codex-toolkit baby_bof --distro kali-linux
```

Use another challenge root:

```powershell
ctf-codex-toolkit baby_bof --ctf-root C:\CTF
```

The launcher also honors `CTF_CODEX_WSL_DISTRO`, `CTF_CODEX_ROOT`, `CTF_ROOT`, and `CODEX_BIN`.

## Commands

```text
ctf-codex-toolkit setup [--distro kali-linux] [--no-browser-arm] [--skip-health]
ctf-codex-toolkit install [--distro kali-linux] [--no-browser-arm]
ctf-codex-toolkit health [--distro kali-linux]
ctf-codex-toolkit install-launchers
ctf-codex-toolkit <challenge> [-Resume] [--distro kali-linux] [--ctf-root D:\CTF]
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

It does **not** copy secrets, sessions, logs, cookies, `.env`, private keys, runtime SQLite state, or Codex provider configuration.

## Browser Arm

By default, `ctf-codex-toolkit setup` and `ctf-codex-toolkit install` create an isolated venv at:

```text
~/.codex/tools/browser_arm/.venv
```

and installs `cloakbrowser` there. Use `--no-browser-arm` to skip that download.

## Publishing

Before publishing, rename the package if needed:

```powershell
cd outputs\ctf-codex-toolkit
npm run smoke
npm pack --dry-run
git init
git add .
git commit -m "Initial CTF Codex Toolkit package"
git branch -M main
git remote add origin https://github.com/<your-user>/ctf-codex-toolkit.git
git push -u origin main
npm publish --access public
```

If `ctf-codex-toolkit` is already taken on npm, change `"name"` in `package.json` to a scoped package, for example:

```json
"name": "@your-scope/ctf-codex-toolkit"
```

Then install with:

```powershell
npm install -g @your-scope/ctf-codex-toolkit
```

## Safety Model

The pre-tool guard blocks high-risk automated attack commands and broad candidate searches, while allowing small deterministic loops. Current regression checks include:

- `range(1<<20)` blocked
- `range(10**8)` blocked
- `range(100000000)` blocked
- `range(2**20)` blocked
- `range(2**10)` allowed
- small shell `for` allowed
- `hashcat` blocked
