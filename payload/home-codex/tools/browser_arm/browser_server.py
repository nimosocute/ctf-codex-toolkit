import json
import socket
import sys
import os
import time
import threading
from pathlib import Path
import site
import re
import secrets

LOCAL_SITE = (
    Path(__file__).resolve().parent
    / ".venv"
    / "lib"
    / f"python{sys.version_info.major}.{sys.version_info.minor}"
    / "site-packages"
)
if LOCAL_SITE.is_dir():
    sys.path.insert(0, str(LOCAL_SITE))
    site.addsitedir(str(LOCAL_SITE))

from cloakbrowser import launch

HOST = "127.0.0.1"
PORT = int(os.environ.get("BROWSER_PORT", 9222))
WORKDIR = Path(os.environ.get("BROWSER_WORKDIR", os.getcwd())).resolve()
WORKDIR.mkdir(parents=True, exist_ok=True)
TOKEN_PATH = Path(os.environ.get("BROWSER_TOKEN_FILE", WORKDIR / ".browser_token")).resolve()

def load_or_create_token():
    env_token = os.environ.get("BROWSER_TOKEN", "").strip()
    if env_token:
        return env_token
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text(encoding="utf-8").strip()
    token = secrets.token_urlsafe(32)
    TOKEN_PATH.write_text(token + "\n", encoding="utf-8")
    try:
        TOKEN_PATH.chmod(0o600)
    except Exception:
        pass
    return token

BROWSER_TOKEN = load_or_create_token()

logs = {"console": [], "network": [], "console_clear": True, "network_clear": True}
watch = {"enabled": False, "path": str(WORKDIR / "latest.png"), "interval": 0.5, "last": 0.0}

def on_console(msg):
    try:
        logs["console"].append({
            "type": msg.type,
            "text": msg.text,
            "location": str(msg.location) if hasattr(msg, "location") else ""
        })
    except Exception:
        pass

def on_response(response):
    try:
        logs["network"].append({
            "url": response.url,
            "status": response.status,
            "headers": dict(response.headers),
            "resource_type": response.request.resource_type,
            "method": response.request.method
        })
    except Exception:
        pass

def on_dialog(dialog):
    # Auto-accept dialogs (alert, confirm, prompt) to prevent hanging
    try:
        logs["console"].append({"type": "dialog", "text": f"Dialog [{dialog.type}]: {dialog.message}", "location": "browser"})
        dialog.accept()
    except Exception:
        pass

def clean_html(html_content):
    """Strip unnecessary bloat to save LLM tokens."""
    # Remove script and style blocks entirely
    html_content = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'<svg\b[^<]*(?:(?!<\/svg>)<[^<]*)*<\/svg>', '<svg>[SVG]</svg>', html_content, flags=re.IGNORECASE)
    return html_content

def handle(page, msg):
    cmd = msg.get("cmd", "")
    global logs

    if cmd == "goto":
        page.goto(msg["url"], wait_until="domcontentloaded", timeout=msg.get("timeout", 30000))
        return {"url": page.url, "title": page.title()}

    elif cmd == "set_headers":
        # Useful for injecting Authorization tokens, custom User-Agents
        page.set_extra_http_headers(msg["headers"])
        return {"headers_set": True}

    elif cmd == "click":
        page.click(msg["selector"], timeout=msg.get("timeout", 5000))
        return {"clicked": msg["selector"]}

    elif cmd == "fill":
        page.fill(msg["selector"], msg["value"], timeout=msg.get("timeout", 5000))
        return {"filled": msg["selector"]}

    elif cmd == "type":
        page.type(msg["selector"], msg["value"], delay=msg.get("delay", 0))
        return {"typed": msg["value"]}

    elif cmd == "press":
        page.press(msg.get("selector", "body"), msg["key"])
        return {"pressed": msg["key"]}

    elif cmd == "mouse":
        action = msg.get("action", "move")
        if action == "move":
            page.mouse.move(msg["x"], msg["y"])
        elif action == "down":
            page.mouse.down()
        elif action == "up":
            page.mouse.up()
        elif action == "click":
            page.mouse.click(msg["x"], msg["y"])
        return {"mouse": action}

    elif cmd == "text":
        el = page.query_selector(msg["selector"])
        return {"text": el.text_content() if el else None}

    elif cmd == "html":
        raw = page.content()
        if msg.get("clean", True):
            raw = clean_html(raw)
        limit = msg.get("limit", 50000)
        return {"html": raw[:limit]}

    elif cmd == "screenshot":
        path = Path(msg.get("path", str(WORKDIR / "screenshot.png"))).resolve()
        page.screenshot(path=str(path), full_page=msg.get("full_page", True))
        return {"path": str(path)}

    elif cmd == "eval":
        result = page.evaluate(msg["js"])
        return {"result": result}

    elif cmd == "cookies":
        return {"cookies": page.context.cookies()}

    elif cmd == "set_cookies":
        page.context.add_cookies(msg["cookies"])
        return {"ok": True}

    elif cmd == "storage":
        ls = page.evaluate("JSON.stringify(localStorage)")
        ss = page.evaluate("JSON.stringify(sessionStorage)")
        return {"localStorage": json.loads(ls), "sessionStorage": json.loads(ss)}

    elif cmd == "upload":
        page.set_input_files(msg["selector"], msg["path"])
        return {"uploaded": msg["path"]}

    elif cmd == "network_logs":
        data = logs["network"].copy()
        if msg.get("clear", False):
            logs["network"].clear()
        return {"logs": data}

    elif cmd == "console_logs":
        data = logs["console"].copy()
        if msg.get("clear", False):
            logs["console"].clear()
        return {"logs": data}

    elif cmd == "network_filter":
        data = logs["network"]
        if msg.get("resource_type"):
            data = [x for x in data if x["resource_type"] == msg["resource_type"]]
        if msg.get("status_min"):
            data = [x for x in data if x["status"] >= msg["status_min"]]
        return {"logs": data, "total": len(logs["network"]), "filtered": len(data)}

    elif cmd == "intercept":
        mode = msg.get("mode", "passthrough")
        url_pattern = msg.get("url_pattern", "**/*")
        if mode == "block":
            page.route(url_pattern, lambda route: route.abort())
        elif mode == "passthrough":
            page.unroute(url_pattern)
        return {"intercepted": mode, "pattern": url_pattern}

    elif cmd == "source_dump":
        outdir = Path(msg.get("outdir", str(WORKDIR))).resolve()
        outdir.mkdir(parents=True, exist_ok=True)
        raw = page.content()
        cleaned = clean_html(raw)
        
        raw_path = outdir / "source_raw.html"
        clean_path = outdir / "source_clean.html"
        
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(raw)
        with open(clean_path, "w", encoding="utf-8") as f:
            f.write(cleaned)
            
        return {
            "saved": True, 
            "raw_path": str(raw_path), 
            "clean_path": str(clean_path),
            "raw_len": len(raw),
            "clean_len": len(cleaned)
        }

    elif cmd == "ax_snapshot":
        # Interactive elements only snapshot
        snap = page.evaluate("""() => {
            const interesting = ['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA', 'FORM', 'IFRAME'];
            const all = document.querySelectorAll('*');
            const res = [];
            for(let el of all) {
                if(interesting.includes(el.tagName) || el.onclick || el.hasAttribute('role')) {
                    const r = el.getBoundingClientRect();
                    if(r.width > 0 && r.height > 0) {
                        res.push({
                            tag: el.tagName,
                            text: el.innerText ? el.innerText.trim().slice(0,100) : '',
                            id: el.id || null,
                            name: el.name || null,
                            type: el.getAttribute('type') || null,
                            href: el.getAttribute('href') || null,
                            rect: {x: Math.round(r.x), y: Math.round(r.y)}
                        });
                    }
                }
            }
            return res;
        }""")
        return {"snapshot": snap, "total_elements": len(snap)}

    elif cmd == "element_at":
        x, y = msg["x"], msg["y"]
        return page.evaluate("""([x, y]) => {
            const el = document.elementFromPoint(x, y);
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return {
                tag: el.tagName, id: el.id || null, class: el.className || null,
                text: (el.innerText || el.textContent || '').slice(0, 500),
                aria: el.getAttribute('aria-label'), title: el.getAttribute('title'),
                rect: {x:r.x, y:r.y, w:r.width, h:r.height},
                selector: el.id ? '#' + el.id : el.tagName.toLowerCase()
            };
        }""", [x, y])

    elif cmd == "auto_watch":
        watch["enabled"] = bool(msg.get("enabled", True))
        watch["path"] = str(Path(msg.get("path", watch["path"])).resolve())
        watch["interval"] = float(msg.get("interval", watch["interval"]))
        return {"enabled": watch["enabled"], "path": watch["path"], "interval": watch["interval"]}

    elif cmd == "wait":
        page.wait_for_selector(msg["selector"], timeout=msg.get("timeout", 10000))
        return {"found": msg["selector"]}

    elif cmd == "back":
        page.go_back()
        return {"url": page.url}

    elif cmd == "url":
        return {"url": page.url}

    elif cmd == "title":
        return {"title": page.title()}

    elif cmd == "close":
        return "__CLOSE__"

    else:
        raise ValueError(f"Unknown command: {cmd}")

def main():
    browser = launch(
        headless=False,
        humanize=True,
        args=[
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
            "--auto-open-devtools-for-tabs",
        ],
    )
    context = browser.new_context(
        viewport={"width": 1400, "height": 900},
        accept_downloads=True,
        permissions=["camera", "microphone"],
        ignore_https_errors=True,
    )
    page = context.new_page()
    page.on("console", on_console)
    page.on("response", on_response)
    page.on("dialog", on_dialog)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    server.settimeout(0.2)
    print(f"CloakBrowser server listening on {HOST}:{PORT}")
    sys.stdout.flush()

    running = True
    while running:
        try:
            if watch["enabled"] and time.time() - watch["last"] >= watch["interval"]:
                try:
                    page.screenshot(path=watch["path"], full_page=False)
                    watch["last"] = time.time()
                except Exception:
                    pass
            conn, addr = server.accept()
        except socket.timeout:
            continue
        try:
            data = b""
            while b"\n" not in data:
                chunk = conn.recv(8192)
                if not chunk:
                    break
                data += chunk

            line = data.decode().strip()
            if not line:
                conn.close()
                continue

            try:
                msg = json.loads(line)
            except json.JSONDecodeError as e:
                resp = json.dumps({"ok": False, "error": f"Bad JSON: {e}"}) + "\n"
                conn.sendall(resp.encode())
                conn.close()
                continue

            msg_id = msg.get("id")
            if msg.get("token") != BROWSER_TOKEN:
                resp = json.dumps({"id": msg_id, "ok": False, "error": "Unauthorized browser control request"}) + "\n"
                conn.sendall(resp.encode())
                conn.close()
                continue

            try:
                result = handle(page, msg)
                if result == "__CLOSE__":
                    resp = json.dumps({"id": msg_id, "ok": True, "result": "closed"}) + "\n"
                    conn.sendall(resp.encode())
                    conn.close()
                    running = False
                    break
                resp = json.dumps({"id": msg_id, "ok": True, "result": result}, default=str) + "\n"
            except Exception as e:
                resp = json.dumps({"id": msg_id, "ok": False, "error": str(e)}) + "\n"

            conn.sendall(resp.encode())
        finally:
            try:
                conn.close()
            except Exception:
                pass

    server.close()
    browser.close()
    print("CloakBrowser server stopped.")

if __name__ == "__main__":
    main()
