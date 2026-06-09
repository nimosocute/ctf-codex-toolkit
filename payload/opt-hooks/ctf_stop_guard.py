#!/usr/bin/env python3
import hashlib
import json
import os
import re
import sys
from pathlib import Path

CTF_ROOT = (os.environ.get("CTF_ROOT") or os.environ.get("CTF_CODEX_ROOT") or str(Path.home() / "ctf-workspaces")).replace("\\", "/").rstrip("/")
WORK_ROOT = (os.environ.get("CTF_WORK_ROOT") or f"{CTF_ROOT}/_work").replace("\\", "/").rstrip("/").lower() + "/"
STATE_DIR = Path.home() / ".codex" / "ctf-evals"
STATE_PATH = STATE_DIR / "stop_state.json"
NO_FINDING_LIMIT = 3


def continue_with(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def ok() -> None:
    sys.exit(0)


def load_state():
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    tmp.replace(STATE_PATH)


def signal_from_log(text: str) -> str:
    keep = []
    in_table = False
    for line in text.splitlines():
        low = line.lower()
        if "|" in line and any(x in low for x in ["hypothesis", "finding", "status", "stuck", "pending", "active", "done", "failed", "confirmed"]):
            in_table = True
            keep.append(line.strip())
            continue
        if in_table and "|" in line:
            keep.append(line.strip())
            continue
        if in_table and line.strip() == "":
            in_table = False
        if any(term in low for term in ["known facts", "finding", "failed", "do not repeat", "stuck", "blocker", "next best test", "proved", "confirmed"]):
            keep.append(line.strip())
    return hashlib.sha256("\n".join(keep).encode()).hexdigest()


raw = sys.stdin.read()
try:
    event = json.loads(raw) if raw.strip() else {}
except Exception:
    event = {}

cwd = Path(event.get("cwd") or os.getcwd())
cwd_lower = str(cwd).lower()

if event.get("stop_hook_active"):
    ok()
if not cwd_lower.startswith(WORK_ROOT):
    ok()

log = cwd / "solve_log.md"
if not log.exists():
    continue_with(
        "Before continuing any CTF solve, create solve_log.md append-only with required sections: "
        "Known facts, Hypotheses, Failed paths / Do Not Repeat, Next best test."
    )
try:
    text = log.read_text(errors="ignore")
except Exception as exc:
    continue_with(f"Before continuing, inspect/fix solve_log.md; hook could not read it: {exc}")

low = text.lower()
missing = []
if "known facts" not in low:
    missing.append("Known facts")
if "hypoth" not in low:
    missing.append("Hypotheses")
if not all(term in low for term in ["surface", "hypothesis", "next test", "finding", "status"]):
    missing.append("hypothesis table columns")
if not any(term in low for term in ["failed paths", "do not repeat"]):
    missing.append("Failed paths / Do Not Repeat")
if "next best test" not in low:
    missing.append("Next best test")
if missing:
    continue_with(
        "Before continuing, update solve_log.md append-only. Missing required section(s): "
        + ", ".join(missing)
        + ". Keep it short; do not paste raw logs."
    )

signal = signal_from_log(text)
state = load_state()
entry = state.setdefault(str(cwd), {"signal": "", "unchanged": 0})
if entry.get("signal") == signal:
    entry["unchanged"] = int(entry.get("unchanged", 0)) + 1
else:
    entry["signal"] = signal
    entry["unchanged"] = 1
save_state(state)

if entry["unchanged"] >= NO_FINDING_LIMIT:
    continue_with(
        f"Stop hook: solve_log.md findings/hypothesis signal has not changed for {entry['unchanged']} turn stops. "
        "Before more attempts, either update the hypothesis table with a concrete finding/blocker, "
        "or mark the current path STUCK under Failed paths / Do Not Repeat and pivot to a new hypothesis."
    )

ok()
