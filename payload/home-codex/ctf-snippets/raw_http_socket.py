#!/usr/bin/env python3
import os
import socket
import ssl
from pathlib import Path

HOST = os.environ.get("TARGET_HOST", "127.0.0.1")
PORT = int(os.environ.get("TARGET_PORT", "80"))
USE_TLS = os.environ.get("TARGET_TLS", "0").lower() in {"1", "true", "yes"}
TIMEOUT = float(os.environ.get("TARGET_TIMEOUT", "5"))
OUTPUT = Path(os.environ.get("RAW_HTTP_OUTPUT", "evidence/raw_http_response.bin"))

# Edit this literal request when testing header parsing or smuggling mutations.
REQUEST = (
    b"GET / HTTP/1.1\r\n"
    b"Host: 127.0.0.1\r\n"
    b"Connection: close\r\n"
    b"Transfer-Encoding: chunked \r\n"
    b"\r\n"
    b"0\r\n"
    b"\r\n"
)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    sock = socket.create_connection((HOST, PORT), timeout=TIMEOUT)
    if USE_TLS:
        context = ssl.create_default_context()
        sock = context.wrap_socket(sock, server_hostname=HOST)
    with sock:
        sock.sendall(REQUEST)
        chunks = []
        while True:
            data = sock.recv(4096)
            if not data:
                break
            chunks.append(data)
    response = b"".join(chunks)
    OUTPUT.write_bytes(response)
    print(f"saved_raw={OUTPUT}")
    print(response[:240].hex())
    print("Edit REQUEST to try TE/CL spacing, duplicate headers, lone LF, mixed casing, or other raw mutations.")


if __name__ == "__main__":
    main()
