#!/usr/bin/env python3
"""
Small scoped endpoint sibling runner for CTF web challenges.

This is not a broad fuzzer. It expands an observed route family such as
/_m/session and /_m/mirror into a capped list of logical siblings, then records
binary-safe evidence for each response.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

try:
    import requests
except ImportError:
    print("Missing dependency: python3 -m pip install requests", file=sys.stderr)
    raise


DEFAULT_WORDS = [
    "forge",
    "verify",
    "verifier",
    "relay",
    "mint",
    "issue",
    "sign",
    "grant",
    "token",
    "cargo",
    "mirror",
    "session",
    "seed",
    "sync",
    "debug",
    "admin",
    "check",
    "submit",
    "packet",
    "claim",
]


def split_csv(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out


def route_prefix(route: str) -> str:
    parsed = urlparse(route)
    path = parsed.path if parsed.scheme else route
    path = "/" + path.lstrip("/")
    if path.endswith("/") and path != "/":
        path = path.rstrip("/")
    if "/" not in path.strip("/"):
        return "/"
    return path.rsplit("/", 1)[0] + "/"


def unique_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def build_candidates(observed: list[str], words: list[str], max_candidates: int) -> list[str]:
    prefixes = unique_preserve_order(route_prefix(item) for item in observed)
    observed_paths = []
    for item in observed:
        parsed = urlparse(item)
        path = parsed.path if parsed.scheme else item
        observed_paths.append("/" + path.lstrip("/").rstrip("/"))

    candidates: list[str] = []
    for prefix in prefixes:
        for word in words:
            candidates.append(prefix + word.strip("/"))
    candidates.extend(observed_paths)
    return unique_preserve_order(candidates)[:max_candidates]


def load_headers(path: str | None) -> dict[str, str]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("--headers-file must contain a JSON object")
    return {str(k): str(v) for k, v in data.items()}


def load_body(path: str | None) -> bytes | None:
    if not path:
        return None
    return Path(path).read_bytes()


def safe_name(route: str) -> str:
    name = route.strip("/") or "root"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)[:120]


def body_base64_preview(body: bytes, limit: int = 96) -> str:
    # body_base64_preview keeps sensitive or binary output away from raw stdout.
    encoded = base64.b64encode(body[:limit]).decode("ascii")
    return encoded + ("..." if len(body) > limit else "")


def oracle_hit(body: bytes, status: int, oracle_text: str | None, oracle_status: int | None) -> bool:
    ok = True
    if oracle_status is not None:
        ok = ok and status == oracle_status
    if oracle_text:
        text = body.decode("utf-8", errors="ignore")
        try:
            ok = ok and bool(re.search(oracle_text, text, re.IGNORECASE))
        except re.error:
            ok = ok and oracle_text.lower() in text.lower()
    return ok


def print_row(route: str, status: int, size: int, hit: bool, saved: Path, body: bytes, notes: str) -> None:
    print(
        "\t".join(
            [
                route,
                str(status),
                str(size),
                "yes" if hit else "no",
                notes,
                str(saved),
                body_base64_preview(body),
            ]
        )
    )


def request_once(
    session: requests.Session,
    method: str,
    base_url: str,
    route: str,
    headers: dict[str, str],
    body: bytes | None,
    timeout: float,
) -> requests.Response:
    url = urljoin(base_url.rstrip("/") + "/", route.lstrip("/"))
    return session.request(method, url, headers=headers, data=body, timeout=timeout, allow_redirects=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scoped endpoint sibling runner with verifier_matrix support")
    parser.add_argument("--base-url", required=True, help="Scheme and host, for example https://target")
    parser.add_argument("--observed", action="append", default=[], help="Observed route(s), repeat or comma-separate")
    parser.add_argument("--verbs", default=",".join(DEFAULT_WORDS), help="Candidate words, comma-separated")
    parser.add_argument("--max-candidates", type=int, default=20, help="Hard cap for endpoint sibling candidates")
    parser.add_argument("--method", default="GET", choices=["GET", "POST", "PUT", "PATCH", "DELETE"])
    parser.add_argument("--headers-file", help="JSON object with headers")
    parser.add_argument("--cookie", help="Cookie header for same_session replay")
    parser.add_argument("--client-pub", help="Client public value to send as X-Client-Pub")
    parser.add_argument("--payload-file", help="Forged packet body to send")
    parser.add_argument("--oracle-text", help="Regex or substring that marks a promising response")
    parser.add_argument("--oracle-status", type=int, help="Expected status code")
    parser.add_argument("--same-session", action="store_true", help="Reuse one requests.Session across candidates")
    parser.add_argument("--matrix", action="store_true", help="Run verifier_matrix modes for forged_packet/client_pub")
    parser.add_argument("--evidence-dir", default="evidence/endpoint_sibling_runner")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    if args.max_candidates < 1 or args.max_candidates > 20:
        raise SystemExit("--max-candidates must be between 1 and 20 for scoped endpoint sibling probing")

    observed = split_csv(args.observed)
    if not observed:
        raise SystemExit("Provide at least one --observed route such as /_m/session")

    words = split_csv([args.verbs])
    candidates = build_candidates(observed, words, args.max_candidates)
    headers = load_headers(args.headers_file)
    if args.cookie:
        headers["Cookie"] = args.cookie
    if args.client_pub:
        headers["X-Client-Pub"] = args.client_pub
    body = load_body(args.payload_file)

    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    modes = ["baseline"]
    if args.matrix:
        modes = ["baseline", "same_session", "client_pub", "forged_packet", "verifier_matrix"]

    print("route\tstatus\tlen\toracle\tnotes\tsaved\tbody_base64_preview")
    for mode in modes:
        session = requests.Session() if (args.same_session or mode in {"same_session", "verifier_matrix"}) else requests.Session()
        mode_headers = dict(headers)
        mode_body = body
        if mode == "baseline":
            mode_body = None
        if mode == "client_pub" and not args.client_pub:
            mode_headers["X-Client-Pub"] = "missing-client-pub"
        if mode == "forged_packet" and body is None:
            mode_body = b""
        for route in candidates:
            response = request_once(session, args.method, args.base_url, route, mode_headers, mode_body, args.timeout)
            saved = evidence_dir / f"{safe_name(mode + '_' + route)}.bin"
            saved.write_bytes(response.content)
            hit = oracle_hit(response.content, response.status_code, args.oracle_text, args.oracle_status)
            print_row(route, response.status_code, len(response.content), hit, saved, response.content, mode)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
