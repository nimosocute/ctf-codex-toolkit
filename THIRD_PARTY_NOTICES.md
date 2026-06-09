# Third-Party Notices

## CTF Skills

This package includes CTF skill directories derived from:

- Repository: https://github.com/ljagiello/ctf-skills.git
- Upstream project: `ljagiello/ctf-skills`
- Upstream license: MIT
- Upstream copyright: Copyright (c) 2026 Lukasz Jagiello

The upstream project provides Agent Skills for CTF categories including web exploitation, pwn, crypto, reverse engineering, forensics, OSINT, AI/ML, malware, miscellaneous challenges, solve dispatching, and writeups.

This toolkit packages those skills with additional Windows/Kali WSL launchers, guard hooks, health checks, and workflow files. Users can update the packaged skill directories from the upstream repository with:

```powershell
ctf-codex-toolkit update-skills
```

## CloakBrowser

The optional Browser Arm installs a pinned Python dependency into an isolated local venv:

- Package: `cloakbrowser==0.3.31`
- Repository: https://github.com/CloakHQ/CloakBrowser
- Upstream project: `CloakHQ/CloakBrowser`
- Upstream license: MIT

CloakBrowser provides a Chromium-based browser automation layer with Playwright-style APIs. This toolkit uses it only for optional CTF browser inspection workflows through `~/.codex/tools/browser_arm/`.

Users can skip this dependency during setup:

```powershell
ctf-codex-toolkit setup --no-browser-arm
```
