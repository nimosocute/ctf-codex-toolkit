#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path

CTF_ROOT = (os.environ.get("CTF_ROOT") or os.environ.get("CTF_CODEX_ROOT") or str(Path.home() / "ctf-workspaces")).replace("\\", "/").rstrip("/")
WORK_ROOT = (os.environ.get("CTF_WORK_ROOT") or f"{CTF_ROOT}/_work").replace("\\", "/").rstrip("/").lower() + "/"
STATE_DIR = Path.home() / ".codex" / "ctf-evals"
STATE_PATH = STATE_DIR / "posttool_state.json"
FAILURE_PATTERNS = {
    "timeout": re.compile(r"\b(timed out|timeout|time limit|deadline exceeded)\b", re.I),
    "killed": re.compile(r"\b(killed|oom|out of memory|segmentation fault|core dumped)\b", re.I),
    "missing_file": re.compile(r"\b(no such file|not found|cannot stat|does not exist)\b", re.I),
    "same_error": re.compile(r"\b(same error|unchanged failure|repeated failure|still failing)\b", re.I),
    "permission": re.compile(r"\b(permission denied|operation not permitted|access denied)\b", re.I),
}


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


def emit_context(message: str):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": message,
        }
    }))
    sys.exit(0)


raw = sys.stdin.read()
try:
    event = json.loads(raw) if raw.strip() else {}
except Exception:
    event = {}

cwd = str(event.get("cwd") or os.getcwd())
if not cwd.lower().startswith(WORK_ROOT):
    sys.exit(0)

blob = json.dumps(event.get("tool_response", event), ensure_ascii=False, default=str)
matched = [name for name, pat in FAILURE_PATTERNS.items() if pat.search(blob)]
state = load_state()
entry = state.setdefault(cwd, {"last": "", "count": 0})

if matched:
    signal = ",".join(sorted(matched))
    if entry.get("last") == signal:
        entry["count"] = int(entry.get("count", 0)) + 1
    else:
        entry["last"] = signal
        entry["count"] = 1
    save_state(state)
    if entry["count"] >= 3:
        emit_context(
            "PostToolUse pivot reminder: repeated failure signal(s) "
            f"{signal} occurred {entry['count']} times in this workspace. "
            "Do not keep retrying. Update solve_log.md with the concrete blocker/finding, "
            "mark the hypothesis STUCK if appropriate, and choose a new hypothesis or smaller test."
        )
else:
    if entry.get("count"):
        entry["last"] = ""
        entry["count"] = 0
        save_state(state)

sys.exit(0)
