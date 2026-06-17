#!/usr/bin/env python3
import ast
import ipaddress
import json
import os
import re
import shlex
import sys
from pathlib import Path
from urllib.parse import urlparse

CTF_ROOT_DISPLAY = os.environ.get("CTF_ROOT") or os.environ.get("CTF_CODEX_ROOT") or str(Path.home() / "ctf-workspaces")
CTF_ROOT_DISPLAY = CTF_ROOT_DISPLAY.replace("\\", "/").rstrip("/")
CTF_ROOT_LOWER = CTF_ROOT_DISPLAY.lower()
WORK_ROOT_DISPLAY = (os.environ.get("CTF_WORK_ROOT") or f"{CTF_ROOT_DISPLAY}/_work").replace("\\", "/").rstrip("/") + "/"
CTF_ROOT_PATH = Path(CTF_ROOT_DISPLAY).expanduser().resolve(strict=False)
WORK_ROOT_PATH = Path(WORK_ROOT_DISPLAY).expanduser().resolve(strict=False)
DEFAULT_TIMEOUT_SECONDS = 120
MAX_SCRIPT_BYTES = 512_000
MAX_CANDIDATE_ATTEMPTS = 10_000
MAX_RANGE_ATTEMPTS = 100_000
MAX_EVALUATED_INT = MAX_RANGE_ATTEMPTS + 1

UNCONDITIONAL_SHELL_PATTERNS = [
    r"\bxargs\s+-P\b",
    r"\bparallel\b",
    r"\b(hashcat|john|hydra|medusa|ncrack|sqlmap|crunch|cewl)\b",
    r"\b(ffuf|wfuzz|gobuster|feroxbuster|dirsearch)\b.*\s-w\b",
    r"\bbrute[-_ ]?force\b",
    r"\bpython3?\b.+(brute|crack)",
]

CONDITIONAL_LOOP_PATTERNS = [
    r"\bseq\b.+\|",
    r"\bfind\b.+-exec\b",
    r"\bwordlist\b",
]

GENERIC_SCRIPT_BLOCK_PATTERNS = [
    r"\bwhile\s+true\s*:",
    r"\bwhile\s+True\s*:",
    r"\b(open|read_text)\s*\([^\n]*(rockyou|wordlist|dictionary|dict)",
]

CANDIDATE_HINT_RE = re.compile(
    r"\b(candidate|candidates|charset|alphabet|printable|ascii_letters|digits|"
    r"oracle|brute|crack|rockyou|permutation|combination|password|plaintext|keyspace)\b",
    re.IGNORECASE,
)

PATCH_PATH_RE = re.compile(r"^\*\*\*\s+(?:Add|Update|Delete)\s+File:\s+(.+?)\s*$|^\*\*\*\s+Rename\s+to:\s+(.+?)\s*$", re.MULTILINE)

PATH_KEYS = {
    "path", "file", "file_path", "filepath", "filename", "target_file",
    "target", "destination", "dest", "new_path", "old_path",
}
CONTENT_KEYS = {
    "content", "contents", "text", "new_str", "old_str", "replacement",
    "insert", "patch", "diff", "command",
}

TIMEOUT_COMMANDS = {
    "make", "ninja", "cmake", "ctest", "pytest", "cargo", "go", "npm", "yarn", "pnpm",
    "mvn", "gradle", "verilator", "yosys", "sby", "iverilog", "vvp", "sage", "z3",
    "bitwuzla", "python", "python3", "pypy", "pypy3", "node", "nodejs", "ruby", "perl",
}
TIMEOUT_SUBCOMMANDS = {"test", "run", "build", "exec", "solve", "check"}

NETWORK_COMMANDS = {
    "curl", "wget", "http", "https", "httpie", "nc", "ncat", "netcat", "socat", "nmap",
    "masscan", "ssh", "ftp", "sftp", "telnet", "websocat", "openssl",
}
HTTP_SCRIPT_ONLY_COMMANDS = {"curl", "wget", "http", "https", "httpie"}
SHORT_HTTP_PAYLOAD_FLAGS = {"-A", "-H", "-X", "-b", "-d", "-e", "-F", "-T", "-u"}
LONG_HTTP_PAYLOAD_FLAGS = {
    "--cookie", "--cookie-jar", "--data", "--data-binary", "--data-raw", "--data-urlencode",
    "--form", "--header", "--json", "--oauth2-bearer", "--proxy-header", "--referer", "--request",
    "--upload-file", "--user", "--user-agent",
}
SENSITIVE_READ_COMMANDS = {"awk", "cat", "grep", "head", "less", "more", "nl", "sed", "strings", "tail"}
SENSITIVE_LOCAL_READ_RE = re.compile(
    r"^(?:[A-Za-z]:)?/(etc/(gshadow|group|hostname|hosts|issue|os-release|passwd|shadow|sudoers)"
    r"|proc/(self|[0-9]+)/(cmdline|environ|maps)"
    r"|root/\.ssh(?:/.*)?"
    r"|home/[^/]+/\.ssh(?:/.*)?"
    r"|var/www/[^/]+/\.env(?:\..*)?)$",
    re.IGNORECASE,
)
INLINE_NETWORK_PAYLOAD_RE = re.compile(
    r"\b(import\s+requests|from\s+requests\b|requests\.(delete|get|head|options|patch|post|put|request)\b|"
    r"urllib\.request|httpx\b|aiohttp\b|socket\.create_connection\b|remote\(|"
    r"from\s+pwn\s+import\b|import\s+pwn\b|https?://)",
    re.IGNORECASE,
)

PRIVATE_MATERIAL_RE = re.compile(
    r"(^|/)(auth\.json|id_rsa|id_ed25519|known_hosts|authorized_keys)$|"
    r"(^|/)\.ssh(/|$)|(^|/)\.codex/(auth\.json|sessions)(/|$)|"
    r"(^|/)\.env(?:\..*)?$",
    re.IGNORECASE,
)
HIGH_ENTROPY_LITERAL_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]{20,}",
    re.IGNORECASE,
)
SECRET_ASSIGN_RE = re.compile(
    r"\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*(['\"])([^'\"\n]{8,})",
    re.IGNORECASE,
)
SAFE_PLACEHOLDER_RE = re.compile(
    r"^(<[^>]+>|redacted|placeholder|changeme|example|dummy|test|none|null)$",
    re.IGNORECASE,
)

URL_RE = re.compile(r"https?://[^\s'\"<>]+", re.IGNORECASE)
HOSTISH_RE = re.compile(r"^[A-Za-z0-9.-]+(?::\d+)?(?:/.*)?$")


def deny(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(2)


def as_display_path(path: Path) -> str:
    return str(path).replace("\\", "/").rstrip("/")


def path_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def canonical_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def challenge_root_for(cwd: Path) -> Path | None:
    resolved = canonical_path(cwd)
    if not path_inside(resolved, WORK_ROOT_PATH):
        return None
    rest = resolved.relative_to(WORK_ROOT_PATH).parts
    if not rest:
        return None
    return WORK_ROOT_PATH / rest[0]


def ensure_workspace(cwd: Path) -> Path:
    root = challenge_root_for(cwd)
    if not root:
        deny(f"Blocked: command outside {WORK_ROOT_DISPLAY}<challenge> workspace.")
    return root


def workspace_path(path: str, cwd: Path) -> Path:
    p = Path(path.strip().strip('"\''))
    if not p.is_absolute():
        p = cwd / p
    return p


def ensure_path_inside_workspace(path: str, cwd: Path, root_path: Path, where: str) -> None:
    p = canonical_path(workspace_path(path, cwd))
    if p == CTF_ROOT_PATH or path_inside(p, CTF_ROOT_PATH) and not path_inside(p, WORK_ROOT_PATH):
        deny(f"Blocked: {where} targets {CTF_ROOT_DISPLAY} outside _work: {path}")
    if not (p == root_path or path_inside(p, root_path)):
        deny(f"Blocked: {where} outside current challenge workspace: {path}")


def regex_block(text: str, patterns: list[str], where: str, reason: str) -> None:
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE | re.DOTALL):
            deny(f"Blocked: {reason}; pattern `{pat}` in {where}. Ask user explicitly.")


def split_shell_segments(command: str) -> list[str]:
    segments, buf = [], []
    quote = ""
    escape = False
    i = 0
    while i < len(command):
        ch = command[i]
        if escape:
            buf.append(ch); escape = False; i += 1; continue
        if ch == "\\":
            buf.append(ch); escape = True; i += 1; continue
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
            i += 1; continue
        if ch in {"'", '"'}:
            quote = ch; buf.append(ch); i += 1; continue
        if command.startswith("&&", i) or command.startswith("||", i):
            seg = "".join(buf).strip()
            if seg:
                segments.append(seg)
            buf = []; i += 2; continue
        if ch in {";", "|"}:
            seg = "".join(buf).strip()
            if seg:
                segments.append(seg)
            buf = []; i += 1; continue
        buf.append(ch); i += 1
    seg = "".join(buf).strip()
    if seg:
        segments.append(seg)
    return segments or [command]


def parse_args(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except Exception:
        return []


def is_timeout_wrapped(args: list[str]) -> bool:
    return bool(args and Path(args[0]).name == "timeout")


def unwrap_timeout(args: list[str]) -> list[str]:
    if not is_timeout_wrapped(args):
        return args
    idx = 1
    while idx < len(args) and args[idx].startswith("-"):
        idx += 1
    if idx < len(args):
        idx += 1
    return args[idx:]


def inline_payload_from_args(args: list[str]) -> tuple[str, str] | None:
    args = unwrap_timeout(args)
    if not args:
        return None
    exe = Path(args[0]).name
    if exe in {"python", "python3", "pypy", "pypy3"}:
        for i, arg in enumerate(args[1:], start=1):
            if arg == "-c" and i + 1 < len(args):
                return args[i + 1], "python -c"
            if arg.startswith("-c") and len(arg) > 2:
                return arg[2:], "python -c"
            if arg == "-m":
                return None
            if not arg.startswith("-"):
                return None
    if exe in {"node", "nodejs"}:
        for i, arg in enumerate(args[1:], start=1):
            if arg in {"-e", "--eval"} and i + 1 < len(args):
                return args[i + 1], "node -e"
            if not arg.startswith("-"):
                return None
    return None


def script_paths_from_args(args: list[str], cwd: Path, depth: int = 0) -> list[Path]:
    if depth > 3:
        return []
    args = unwrap_timeout(args)
    if not args:
        return []
    exe = Path(args[0]).name
    if exe in {"bash", "sh", "zsh"}:
        for i, arg in enumerate(args[1:], start=1):
            if arg in {"-c", "-lc"} and i + 1 < len(args):
                paths = []
                for segment in split_shell_segments(args[i + 1]):
                    paths.extend(script_paths_from_args(parse_args(segment), cwd, depth + 1))
                return paths
        for arg in args[1:]:
            if not arg.startswith("-"):
                return [workspace_path(arg, cwd)]
        return []
    if exe in {"python", "python3", "pypy", "pypy3", "node", "nodejs", "ruby", "perl", "sage"}:
        for arg in args[1:]:
            if arg == "--":
                continue
            if arg.startswith("-"):
                return []
            return [workspace_path(arg, cwd)]
        return []
    script_exts = {".py", ".sh", ".js", ".ts", ".pl", ".rb", ".sage"}
    first = workspace_path(args[0], cwd)
    if first.suffix in script_exts:
        return [first]
    return []


def command_needs_timeout(args: list[str]) -> bool:
    if not args:
        return False
    exe = Path(args[0]).name
    if exe in {"python", "python3", "pypy", "pypy3", "node", "nodejs", "ruby", "perl", "sage"}:
        return any((not arg.startswith("-") and arg != "--") for arg in args[1:])
    if exe in TIMEOUT_COMMANDS:
        if exe in {"cargo", "go", "npm", "yarn", "pnpm", "mvn", "gradle"}:
            return any(arg in TIMEOUT_SUBCOMMANDS for arg in args[1:])
        return True
    return False


def max_nested_loop_depth(node: ast.AST, depth: int = 0) -> int:
    here = depth + 1 if isinstance(node, (ast.For, ast.While, ast.AsyncFor)) else depth
    best = here
    for child in ast.iter_child_nodes(node):
        best = max(best, max_nested_loop_depth(child, here))
    return best


def cap_int(value: int) -> int:
    if value > MAX_EVALUATED_INT:
        return MAX_EVALUATED_INT
    if value < -MAX_EVALUATED_INT:
        return -MAX_EVALUATED_INT
    return value


def eval_int_expr(node: ast.AST) -> int | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return cap_int(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = eval_int_expr(node.operand)
        return cap_int(-inner) if inner is not None else None
    if isinstance(node, ast.BinOp):
        left = eval_int_expr(node.left)
        right = eval_int_expr(node.right)
        if left is None or right is None:
            return None
        if isinstance(node.op, ast.LShift):
            if right < 0:
                return None
            if left == 0:
                return 0
            if right > 63:
                return MAX_EVALUATED_INT if left > 0 else -MAX_EVALUATED_INT
            return cap_int(left << right)
        if isinstance(node.op, ast.Pow):
            if right < 0:
                return None
            if left in {-1, 0, 1}:
                return cap_int(left ** right)
            if right > 63:
                return MAX_EVALUATED_INT if left > 0 or right % 2 == 0 else -MAX_EVALUATED_INT
            return cap_int(left ** right)
        if isinstance(node.op, ast.Mult):
            return cap_int(left * right)
        if isinstance(node.op, ast.Add):
            return cap_int(left + right)
        if isinstance(node.op, ast.Sub):
            return cap_int(left - right)
    return None


def range_size(node: ast.Call) -> int | None:
    name = getattr(node.func, "id", "") or getattr(node.func, "attr", "")
    if name != "range" or not node.args or len(node.args) > 3:
        return None
    values = [eval_int_expr(arg) for arg in node.args]
    if any(value is None for value in values):
        return None
    if len(values) == 1:
        start, stop, step = 0, values[0], 1
    elif len(values) == 2:
        start, stop, step = values[0], values[1], 1
    else:
        start, stop, step = values
    if step == 0:
        return None
    if step > 0:
        if start >= stop:
            return 0
        return (stop - start + step - 1) // step
    if start <= stop:
        return 0
    step_abs = -step
    return (start - stop + step_abs - 1) // step_abs


def iterable_size(node: ast.AST) -> int | None:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return len(node.elts)
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)):
        return len(node.value)
    if isinstance(node, ast.Call):
        return range_size(node)
    return None


def small_factorial_ratio(n: int, r: int) -> int:
    if r < 0 or n < 0 or r > n:
        return 0
    total = 1
    for value in range(n - r + 1, n + 1):
        total *= value
        if total > MAX_CANDIDATE_ATTEMPTS:
            break
    return total


def small_combination(n: int, r: int) -> int:
    if r < 0 or n < 0 or r > n:
        return 0
    r = min(r, n - r)
    total = 1
    for i in range(1, r + 1):
        total = total * (n - r + i) // i
        if total > MAX_CANDIDATE_ATTEMPTS:
            break
    return total


def generator_search_space(node: ast.Call) -> tuple[str, int | None] | None:
    name = getattr(node.func, "id", "") or getattr(node.func, "attr", "")
    if name not in {"product", "permutations", "combinations"}:
        return None

    repeat = 1
    for kw in node.keywords:
        if kw.arg == "repeat":
            value = eval_int_expr(kw.value)
            if value is None:
                return name, None
            repeat = value

    if name == "product":
        if not node.args:
            return name, 0
        total = 1
        for arg in node.args:
            size = iterable_size(arg)
            if size is None:
                return name, None
            total *= size
            if total > MAX_CANDIDATE_ATTEMPTS:
                return name, total
        total = total ** repeat
        return name, total

    if not node.args:
        return name, None
    n = iterable_size(node.args[0])
    if n is None:
        return name, None
    r = n
    if len(node.args) >= 2:
        value = eval_int_expr(node.args[1])
        if value is None:
            return name, None
        r = value
    if name == "permutations":
        return name, small_factorial_ratio(n, r)
    return name, small_combination(n, r)


def has_large_range_loop(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        size = range_size(node)
        if size is not None and size >= MAX_RANGE_ATTEMPTS:
            return True
    return False


def candidate_generator_issue(tree: ast.AST, candidate_hint: bool) -> str:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        gen = generator_search_space(node)
        if gen:
            name, size = gen
            if size is not None and size > MAX_CANDIDATE_ATTEMPTS:
                return f"{name} search space is {size:,} candidates"
            if candidate_hint and size is None:
                return f"{name} search space is unknown"
        call_name = getattr(node.func, "id", "") or getattr(node.func, "attr", "")
        if candidate_hint and call_name in {"Pool", "ThreadPoolExecutor", "ProcessPoolExecutor"}:
            return f"{call_name} used in candidate-style script"
    return ""


def scan_python_ast(text: str, where: str) -> None:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return
    nested = max_nested_loop_depth(tree)
    total_loops = sum(isinstance(n, (ast.For, ast.While, ast.AsyncFor)) for n in ast.walk(tree))
    candidate_hint = bool(CANDIDATE_HINT_RE.search(text))
    if candidate_hint and nested >= 2:
        deny(f"Blocked: candidate-style nested loop in {where}. Ask user explicitly.")
    if candidate_hint and total_loops >= 4:
        deny(f"Blocked: broad candidate-loop script in {where}. Ask user explicitly.")
    if candidate_hint and has_large_range_loop(tree):
        deny(f"Blocked: large candidate range in {where}. Ask user explicitly.")
    issue = candidate_generator_issue(tree, candidate_hint)
    if issue:
        deny(f"Blocked: candidate generator in {where}: {issue}. Ask user explicitly.")


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    from math import log2
    counts = {ch: value.count(ch) for ch in set(value)}
    return -sum((count / len(value)) * log2(count / len(value)) for count in counts.values())

def literal_looks_secret(value: str) -> bool:
    value = value.strip()
    if SAFE_PLACEHOLDER_RE.match(value):
        return False
    if len(value) < 20:
        return False
    alnum = sum(ch.isalnum() for ch in value)
    return alnum >= 16 and shannon_entropy(value) >= 3.5

def scan_secret_content(text: str, where: str) -> None:
    if HIGH_ENTROPY_LITERAL_RE.search(text):
        deny(f"Blocked: {where} appears to contain unredacted private material. Redact before writing/reporting.")
    for match in SECRET_ASSIGN_RE.finditer(text):
        if literal_looks_secret(match.group(3)):
            deny(f"Blocked: {where} appears to contain unredacted private material. Redact before writing/reporting.")

def scan_text_payload(text: str, where: str, python_ast: bool = False) -> None:
    scan_secret_content(text, where)
    regex_block(text, GENERIC_SCRIPT_BLOCK_PATTERNS, where, "candidate-loop/long-running payload")
    if python_ast:
        scan_python_ast(text, where)


def scan_script(path: Path, root_path: Path) -> None:
    resolved = canonical_path(path)
    if not (resolved == root_path or path_inside(resolved, root_path)):
        deny(f"Blocked: script path outside current challenge workspace: {path}")
    if not resolved.exists() or not resolved.is_file():
        return
    if resolved.stat().st_size > MAX_SCRIPT_BYTES:
        return
    text = resolved.read_text(errors="ignore")
    scan_text_payload(text, str(resolved), python_ast=resolved.suffix == ".py")


def load_scope(cwd: Path) -> set[str]:
    scopes: set[str] = set()
    for env_name in ["CTF_SCOPE", "CTF_TARGETS", "TARGET_SCOPE"]:
        raw = os.environ.get(env_name, "")
        for token in re.split(r"[\s,]+", raw):
            if token.strip():
                scopes.add(normalize_scope_token(token.strip()))
    for rel in ["scope.txt", "target.txt", "targets.txt", "work/scope.txt", "work/targets.txt"]:
        p = cwd / rel
        if p.exists() and p.is_file() and p.stat().st_size <= 64_000:
            for token in re.split(r"[\s,]+", p.read_text(errors="ignore")):
                if token.strip() and not token.strip().startswith("#"):
                    scopes.add(normalize_scope_token(token.strip()))
    return {s for s in scopes if s}


def normalize_scope_token(token: str) -> str:
    token = token.strip().strip("'\"")
    if "://" in token:
        parsed = urlparse(token)
        token = parsed.hostname or token
    token = token.split("/", 1)[0]
    token = token.rsplit(":", 1)[0] if token.count(":") == 1 else token
    return token.lower().strip(".")


def host_from_urlish(token: str) -> str:
    token = token.strip().strip("'\"<>()[]{}")
    if not token:
        return ""
    if "://" in token:
        parsed = urlparse(token)
        return (parsed.hostname or "").lower()
    if HOSTISH_RE.match(token) and ("." in token or token in {"localhost"} or re.match(r"^\d+\.\d+\.\d+\.\d+", token)):
        return normalize_scope_token(token)
    return ""


def inline_http_payload_issue(args: list[str]) -> str:
    args = unwrap_timeout(args)
    if not args:
        return ""
    exe = Path(args[0]).name.lower()
    if exe not in HTTP_SCRIPT_ONLY_COMMANDS:
        return ""

    for arg in args[1:]:
        if arg in SHORT_HTTP_PAYLOAD_FLAGS or arg in LONG_HTTP_PAYLOAD_FLAGS:
            return arg
        if any(arg.startswith(flag + "=") for flag in LONG_HTTP_PAYLOAD_FLAGS):
            return arg.split("=", 1)[0]
        if any(arg.startswith(flag) and len(arg) > len(flag) for flag in SHORT_HTTP_PAYLOAD_FLAGS):
            return arg[:2]
        if arg.startswith(("http://", "https://")):
            parsed = urlparse(arg)
            combined = f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path
            if re.search(r"/(etc/passwd|etc/shadow|proc/self/environ|\.env)(?:$|[/?#])", combined, re.IGNORECASE):
                return "sensitive-file-probe"
            if parsed.query and re.search(
                r"(%[0-9A-Fa-f]{2}|['\"`]|\.{2}|{{|}}|\$\(|<|>|;|\||"
                r"\b(select|union|sleep|load_file|passwd|shadow|proc/self|\.env)\b)",
                combined,
                re.IGNORECASE,
            ):
                return "url-query"
    return ""


def guard_sensitive_local_read(args: list[str], full_command: str, cwd: Path, root_path: Path) -> None:
    args = unwrap_timeout(args)
    if not args:
        return
    exe = Path(args[0]).name
    if exe not in SENSITIVE_READ_COMMANDS:
        return
    if re.search(r"\bbase64\b", full_command, re.IGNORECASE):
        return

    for arg in args[1:]:
        if arg == "--" or arg.startswith("-"):
            continue
        candidate = canonical_path(workspace_path(arg, cwd))
        if candidate == root_path or path_inside(candidate, root_path):
            continue
        if SENSITIVE_LOCAL_READ_RE.search(as_display_path(candidate)):
            deny(
                "Blocked: direct read of sensitive local system file. "
                "Encode the output first, for example `base64 < path`, instead of printing it raw."
            )


def inline_interpreter_requires_script(text: str, where: str) -> None:
    if INLINE_NETWORK_PAYLOAD_RE.search(text):
        deny(
            f"Blocked: inline network/exploit code in {where}. "
            "Write it to `work/exploit.py` (payloads may be Base64/Hex inside the script) "
            "and run `timeout 120s python3 work/exploit.py`."
        )


def is_local_or_private(host: str) -> bool:
    if host in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}:
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False


def host_allowed(host: str, scopes: set[str]) -> bool:
    host = host.lower().strip(".")
    if not host or is_local_or_private(host):
        return True
    for scope in scopes:
        if not scope:
            continue
        try:
            if "/" in scope and ipaddress.ip_address(host) in ipaddress.ip_network(scope, strict=False):
                return True
        except ValueError:
            pass
        if host == scope or host.endswith("." + scope):
            return True
    return False


def extract_network_hosts(args: list[str], command: str) -> list[str]:
    args = unwrap_timeout(args)
    hosts: list[str] = []
    for url in URL_RE.findall(command):
        host = host_from_urlish(url)
        if host:
            hosts.append(host)
    if not args:
        return hosts
    exe = Path(args[0]).name
    if exe in NETWORK_COMMANDS:
        if exe in {"nc", "ncat", "netcat", "ssh", "ftp", "sftp", "telnet"}:
            for arg in args[1:]:
                if arg.startswith("-") or arg.isdigit():
                    continue
                host = host_from_urlish(arg)
                if host:
                    hosts.append(host)
                    break
        elif exe in {"nmap", "masscan"}:
            for arg in args[1:]:
                if arg.startswith("-") or "/" in arg and not re.match(r"^\d+\.\d+\.\d+\.\d+/\d+", arg):
                    continue
                host = host_from_urlish(arg)
                if host:
                    hosts.append(host)
        else:
            for arg in args[1:]:
                host = host_from_urlish(arg)
                if host:
                    hosts.append(host)
    return sorted(set(hosts))


def guard_network(args: list[str], command: str, cwd: Path) -> None:
    hosts = extract_network_hosts(args, command)
    if not hosts:
        return
    scopes = load_scope(cwd)
    for host in hosts:
        if not host_allowed(host, scopes):
            if scopes:
                deny(f"Blocked: network target `{host}` outside declared CTF scope {sorted(scopes)}. Ask user before browsing unrelated domains.")
            deny(f"Blocked: network target `{host}` with no declared scope. Add `scope.txt`/`target.txt`, set CTF_SCOPE, or ask user explicitly.")


def private_material_hit(token: str, cwd: Path, root_path: Path) -> str:
    raw = token.strip().strip("'\"<>()[]{}")
    if not raw or raw == "--" or raw.startswith("-") or "://" in raw:
        return ""
    raw = raw.rstrip(",;:")
    expanded = os.path.expandvars(os.path.expanduser(raw))
    pathish = raw.startswith(("/", "~", "$HOME", "${HOME}", ".")) or "/" in raw or "\\" in raw
    if not pathish:
        return ""
    p = Path(expanded)
    if not p.is_absolute():
        p = cwd / p
    resolved = canonical_path(p)
    if resolved == root_path or path_inside(resolved, root_path):
        return ""
    return raw if PRIVATE_MATERIAL_RE.search(as_display_path(resolved)) else ""

def command_private_material_hits(args: list[str], command: str, cwd: Path, root_path: Path) -> list[str]:
    hits: list[str] = []
    for arg in args:
        hit = private_material_hit(arg, cwd, root_path)
        if hit:
            hits.append(hit)
    for raw in re.findall(r"(?:~|\$HOME|\$\{HOME\}|/home/[^/\s'\";|&<>]+)(?:/[^\s'\";|&<>]+)+", command):
        hit = private_material_hit(raw, cwd, root_path)
        if hit:
            hits.append(hit)
    return sorted(set(hits))

def guard_secrets(command: str, cwd: Path, root_path: Path) -> None:
    for segment in split_shell_segments(command):
        raw_args = parse_args(segment)
        args = unwrap_timeout(raw_args)
        if not args:
            continue
        if Path(args[0]).name in {"bash", "sh", "zsh"}:
            for i, arg in enumerate(args[1:], start=1):
                if arg in {"-c", "-lc"} and i + 1 < len(args):
                    guard_secrets(args[i + 1], cwd, root_path)
                    break
        hits = command_private_material_hits(args, segment, cwd, root_path)
        if hits:
            deny("Blocked: command references private operator material outside the challenge workspace: " + ", ".join(hits[:5]))

def guard_bash(command: str, cwd: Path, root_path: Path, depth: int = 0, timeout_ok: bool = False) -> None:
    regex_block(command, UNCONDITIONAL_SHELL_PATTERNS, "command", "candidate-loop command")
    if CANDIDATE_HINT_RE.search(command):
        regex_block(command, CONDITIONAL_LOOP_PATTERNS, "command", "candidate-loop command")
    guard_secrets(command, cwd, root_path)

    escaped_root = re.escape(CTF_ROOT_LOWER)
    root_write_pattern = rf">\s*{escaped_root}(/|\s|$)|\b(cp|mv|unzip|tar|7z)\b.*\s{escaped_root}(/|\s|$)"
    if re.search(root_write_pattern, command.lower(), re.IGNORECASE | re.DOTALL):
        deny(f"Blocked: write/extract target appears to be {CTF_ROOT_DISPLAY} root or outside _work.")

    if depth > 3:
        return

    current_cwd = cwd
    for segment in split_shell_segments(command):
        raw_args = parse_args(segment)
        segment_timeout_ok = timeout_ok or is_timeout_wrapped(raw_args)
        args = unwrap_timeout(raw_args)
        if not args:
            continue
        if args[0] == "cd":
            target = args[1] if len(args) > 1 else str(Path.home())
            new_cwd = workspace_path(target, current_cwd)
            ensure_path_inside_workspace(str(new_cwd), current_cwd, root_path, "cd")
            current_cwd = canonical_path(new_cwd)
            continue

        guard_network(args, segment, current_cwd)
        http_issue = inline_http_payload_issue(args)
        if http_issue:
            deny(
                "Blocked: inline HTTP payload request. "
                f"Found `{http_issue}` in `{Path(args[0]).name}`. "
                "Move the request into `work/exploit.py`, keep payloads in variables or Base64/Hex literals, "
                "then run it as a file-based script."
            )
        guard_sensitive_local_read(args, command, current_cwd, root_path)
        if command_needs_timeout(args) and not segment_timeout_ok:
            deny(f"Blocked: long solve/build/test command `{Path(args[0]).name}` must be wrapped, e.g. `timeout {DEFAULT_TIMEOUT_SECONDS}s {segment}`.")

        shell_payload = None
        if Path(args[0]).name in {"bash", "sh", "zsh"}:
            for i, arg in enumerate(args[1:], start=1):
                if arg in {"-c", "-lc"} and i + 1 < len(args):
                    shell_payload = args[i + 1]
                    break
        if shell_payload is not None:
            guard_bash(shell_payload, current_cwd, root_path, depth + 1, timeout_ok=segment_timeout_ok)
            continue

        payload = inline_payload_from_args(args)
        if payload:
            text, where = payload
            inline_interpreter_requires_script(text, where)
            scan_text_payload(text, where, python_ast=where.startswith("python"))
        for script_path in script_paths_from_args(args, current_cwd):
            scan_script(script_path, root_path)


def iter_tool_fields(value, parents=()):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from iter_tool_fields(item, parents + (str(key),))
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            yield from iter_tool_fields(item, parents + (str(idx),))
    else:
        yield parents, value


def looks_like_path_key(key: str) -> bool:
    k = key.lower().replace("-", "_")
    return k in PATH_KEYS or k.endswith("_path") or k.endswith("_file")


def looks_like_content_key(key: str) -> bool:
    return key.lower().replace("-", "_") in CONTENT_KEYS


def guard_patch(command: str, tool_input: dict, cwd: Path, root_path: Path) -> None:
    saw_path = False
    saw_patch_envelope = False

    if command.strip():
        scan_text_payload(command, "edit/apply_patch command", python_ast=False)
        for match in PATCH_PATH_RE.finditer(command):
            saw_patch_envelope = True
            path = match.group(1) or match.group(2)
            if path:
                saw_path = True
                ensure_path_inside_workspace(path, cwd, root_path, "edit/apply_patch")
        if "*** Begin Patch" in command and not PATCH_PATH_RE.search(command):
            deny("Blocked: apply_patch without parseable file target.")

    for parents, value in iter_tool_fields(tool_input):
        if not parents or not isinstance(value, str):
            continue
        key = parents[-1]
        if looks_like_path_key(key):
            if value.strip():
                saw_path = True
                ensure_path_inside_workspace(value, cwd, root_path, f"structured edit field {'.'.join(parents)}")
        elif looks_like_content_key(key):
            if value.strip():
                scan_text_payload(value, f"structured edit field {'.'.join(parents)}", python_ast=value.lstrip().startswith(("import ", "from ", "for ", "while ", "def ", "class ")))

    if tool_input and not saw_path and not saw_patch_envelope:
        deny("Blocked: structured edit/write without parseable path field.")


raw = sys.stdin.read()
try:
    event = json.loads(raw) if raw.strip() else {}
except Exception:
    event = {}

tool_name = event.get("tool_name", "")
tool_input = event.get("tool_input", {}) if isinstance(event.get("tool_input", {}), dict) else {}
cmd = tool_input.get("command", "") or raw
cwd = Path(event.get("cwd") or os.getcwd())
root_path = ensure_workspace(cwd)

if tool_name in {"Bash", ""}:
    guard_bash(cmd, cwd, root_path)
elif tool_name in {"apply_patch", "Edit", "Write"}:
    guard_patch(cmd, tool_input, cwd, root_path)
else:
    pass

sys.exit(0)
