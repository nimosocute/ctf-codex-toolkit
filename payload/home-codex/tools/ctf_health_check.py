#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


CODEX_HOME = Path.home() / ".codex"
INVENTORY_PATH = CODEX_HOME / "tools_inventory.md"
OSS_CAD_BIN = Path("/opt/oss-cad-suite/bin")
CODEX_CTF_PYTHON = Path("/opt/codex-ctf-python")
CODEX_CTF_PY_SITE = (
    CODEX_CTF_PYTHON
    / "lib"
    / f"python{sys.version_info.major}.{sys.version_info.minor}"
    / "site-packages"
)
BROWSER_ARM_DIR = CODEX_HOME / "tools" / "browser_arm"
BROWSER_ARM_SITE = (
    BROWSER_ARM_DIR
    / ".venv"
    / "lib"
    / f"python{sys.version_info.major}.{sys.version_info.minor}"
    / "site-packages"
)

BASE_ENV = os.environ.copy()
BASE_ENV["PATH"] = ":".join(
    str(path)
    for path in [
        OSS_CAD_BIN,
        CODEX_CTF_PYTHON / "bin",
        Path.home() / ".local" / "bin",
        Path.home() / ".npm-global" / "bin",
        Path("/usr/local/sbin"),
        Path("/usr/local/bin"),
        Path("/usr/sbin"),
        Path("/usr/bin"),
        Path("/sbin"),
        Path("/bin"),
    ]
)
if CODEX_CTF_PY_SITE.is_dir():
    BASE_ENV["PYTHONPATH"] = ":".join(
        part
        for part in [str(CODEX_CTF_PY_SITE), BASE_ENV.get("PYTHONPATH", "")]
        if part
    )


@dataclass(frozen=True)
class Check:
    name: str
    verify: str
    install: str
    limitations: str = ""
    timeout: int = 20
    shell: bool = True


CHECKS = [
    Check("python3", "python3 --version", "system"),
    Check("pwntools", "python3 -c 'import pwnlib; print(pwnlib.__version__)'", "apt"),
    Check("gdb", "gdb --version", "apt"),
    Check("checksec", "pwn checksec --help", "apt/pip"),
    Check("z3", "python3 -c 'import z3; print(z3.get_version_string())'", "pip/apt"),
    Check("sage", "readlink -f \"$(command -v sage)\"", "micromamba/local"),
    Check("angr", "python3 -c 'import angr; print(angr.__version__)'", "pip"),
    Check("binwalk", "binwalk --help", "apt"),
    Check("exiftool", "exiftool -ver", "apt"),
    Check("foremost", "foremost -V", "apt"),
    Check("tshark", "tshark --version", "apt"),
    Check("radare2", "r2 -v", "apt"),
    Check(
        "ghidra",
        "test -x /usr/share/ghidra/ghidraRun && dpkg-query -W -f='${Version}' ghidra",
        "apt",
        "GUI tool; version comes from package metadata.",
    ),
    Check("verilator", "verilator --version", "apt"),
    Check("yosys", "yosys -V", "oss-cad-suite", "PATH must include /opt/oss-cad-suite/bin."),
    Check("iceunpack", "iceunpack 2>&1 | head -1", "apt"),
    Check("icebox_vlog", "icebox_vlog -h 2>&1 | head -1", "apt"),
    Check("bitwuzla", "bitwuzla --version", "oss-cad-suite", "PATH must include /opt/oss-cad-suite/bin."),
    Check("curl", "curl --version", "apt"),
    Check("ffuf", "ffuf -V", "apt/go", "guard blocks broad scans unless scoped/approved"),
    Check("hashcat", "hashcat --version", "apt", "guard blocks brute force unless approved"),
    Check("john", "john --list=build-info", "apt", "guard blocks brute force unless approved"),
    Check(
        "browser_arm",
        "python3 ~/.codex/tools/ctf_health_check.py --check browser_arm",
        "local venv/pip",
        "Uses isolated ~/.codex/tools/browser_arm/.venv plus CloakBrowser cache.",
    ),
]


def clean_output(text: str) -> str:
    return " ".join(text.replace("\r", "\n").split())[:220]


def run_shell(command: str, timeout: int = 20) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            f"set -o pipefail; {command}",
            shell=True,
            executable="/bin/bash",
            env=BASE_ENV,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    output = clean_output((proc.stdout or proc.stderr or "").strip())
    return proc.returncode == 0, output


def check_browser_arm() -> tuple[bool, str]:
    if BROWSER_ARM_SITE.is_dir():
        import site

        sys.path.insert(0, str(BROWSER_ARM_SITE))
        site.addsitedir(str(BROWSER_ARM_SITE))
    try:
        import cloakbrowser
        from cloakbrowser import binary_info, launch
    except Exception as exc:
        return False, f"cloakbrowser import failed: {type(exc).__name__}: {exc}"
    try:
        info = binary_info()
    except Exception as exc:
        return False, f"cloakbrowser {cloakbrowser.__version__}; binary_info failed: {exc}"
    installed = bool(info.get("installed"))
    binary = info.get("binary_path", "")
    if not installed:
        return False, f"cloakbrowser {cloakbrowser.__version__}; chromium missing at {binary}"
    browser = None
    try:
        browser = launch(headless=True)
        page = browser.new_page()
        page.goto("data:text/html,<title>ok</title>")
        title = page.title()
    except Exception as exc:
        output = f"cloakbrowser {cloakbrowser.__version__}; headless launch failed: {type(exc).__name__}: {exc}"
        if "libnspr4.so" in output:
            output += "; missing Chromium system deps: install libnspr4/libnss3 or run the Playwright Chromium deps installer"
        return False, output
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
    return True, f"cloakbrowser {cloakbrowser.__version__}; chromium installed; headless launch title={title}"


SPECIAL_CHECKS = {
    "browser_arm": check_browser_arm,
}


def run_check(check: Check) -> tuple[bool, str]:
    special = SPECIAL_CHECKS.get(check.name)
    if special:
        return special()
    return run_shell(check.verify, timeout=check.timeout)


def markdown_escape(value: str) -> str:
    return value.replace("|", "\\|")


def render_inventory(results: list[tuple[Check, bool, str]]) -> str:
    lines = [
        "# CTF Tools Inventory",
        "",
        f"Updated: {datetime.now().replace(microsecond=0).isoformat()}",
        "",
        "| tool | verification command | install method | status | version/output | known limitations |",
        "|---|---|---|---|---|---|",
    ]
    for check, ok, output in results:
        status = "OK" if ok else "MISSING/ERR"
        lines.append(
            "| {tool} | `{verify}` | {install} | {status} | `{output}` | {limitations} |".format(
                tool=markdown_escape(check.name),
                verify=markdown_escape(check.verify),
                install=markdown_escape(check.install),
                status=status,
                output=markdown_escape(output),
                limitations=markdown_escape(check.limitations),
            )
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Codex CTF environment health check.")
    parser.add_argument("--check", choices=[check.name for check in CHECKS], help="Run one named check.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument("--update-inventory", action="store_true", help="Rewrite ~/.codex/tools_inventory.md from live checks.")
    args = parser.parse_args()

    selected = [check for check in CHECKS if not args.check or check.name == args.check]
    results = [(check, *run_check(check)) for check in selected]

    if args.check:
        check, ok, output = results[0]
        print(output)
        return 0 if ok else 1

    if args.update_inventory:
        INVENTORY_PATH.write_text(render_inventory(results))

    if args.json:
        print(json.dumps([
            {
                "tool": check.name,
                "verify": check.verify,
                "install": check.install,
                "status": "OK" if ok else "MISSING/ERR",
                "output": output,
                "limitations": check.limitations,
            }
            for check, ok, output in results
        ], indent=2))
    else:
        print(render_inventory(results), end="")

    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
