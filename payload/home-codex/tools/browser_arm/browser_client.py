import json
import os
import socket
import sys
from pathlib import Path

def load_token(token=None):
    if token:
        return token
    env_token = os.environ.get("BROWSER_TOKEN", "").strip()
    if env_token:
        return env_token
    workdir = Path(os.environ.get("BROWSER_WORKDIR", os.getcwd())).resolve()
    token_path = Path(os.environ.get("BROWSER_TOKEN_FILE", workdir / ".browser_token")).resolve()
    if token_path.exists():
        return token_path.read_text(encoding="utf-8").strip()
    return ""

def send_command(cmd_dict, host="127.0.0.1", port=9222, token=None):
    cmd_dict = dict(cmd_dict)
    cmd_dict["token"] = load_token(token)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(60)
    sock.connect((host, port))
    sock.sendall((json.dumps(cmd_dict) + "\n").encode())
    data = b""
    while b"\n" not in data:
        chunk = sock.recv(8192)
        if not chunk:
            break
        data += chunk
    sock.close()
    return json.loads(data.decode().strip())

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", help="Command to execute")
    parser.add_argument("--url", default=None)
    parser.add_argument("--selector", default=None)
    parser.add_argument("--value", default=None)
    parser.add_argument("--key", default=None)
    parser.add_argument("--x", type=int, default=None)
    parser.add_argument("--y", type=int, default=None)
    parser.add_argument("--action", default=None)
    parser.add_argument("--path", default=None)
    parser.add_argument("--js", default=None)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--full-page", action="store_true", default=True)
    parser.add_argument("--clear", action="store_true", default=False)
    parser.add_argument("--resource_type", default=None)
    parser.add_argument("--status_min", type=int, default=None)
    parser.add_argument("--mode", default=None)
    parser.add_argument("--url_pattern", default=None)
    parser.add_argument("--outdir", default=None)
    parser.add_argument("--interval", type=float, default=None)
    parser.add_argument("--enabled", type=lambda x: str(x).lower() in ["1","true","yes","on"], default=None)
    parser.add_argument("--headers", help="JSON string of headers", default=None)
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--token", default=None)
    args = parser.parse_args()

    msg = {"id": 1, "cmd": args.cmd}
    
    # Simple direct mappings
    for k in ["url", "selector", "value", "key", "x", "y", "action", "path", "js", "timeout", "resource_type", "status_min", "mode", "url_pattern", "outdir", "interval", "enabled"]:
        v = getattr(args, k)
        if v is not None:
            msg[k] = v
            
    # Complex mappings
    if args.headers:
        msg["headers"] = json.loads(args.headers)
        
    msg["full_page"] = args.full_page
    msg["clear"] = args.clear

    result = send_command(msg, port=args.port, token=args.token)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
