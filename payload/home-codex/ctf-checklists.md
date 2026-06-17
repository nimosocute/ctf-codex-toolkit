# CTF Checklists

## 0. Meta - READ FIRST
- **Read challenge description carefully**: Text often contains hints about category, technical puns, or constraints.
- **Analyze author/source**: Some authors have specific styles or recurring techniques.
- **Check attachment names**: Filenames (e.g., `backup.tar.gz.old`, `index.php.bak`) suggest recon targets.
- **Hunt for the flag**: After resolving the flag format from the goal, always run `grep -rE "$FLAG_REGEX"` across all extracted artifacts.

## Reconnaissance Checklists
Classify the challenge type first. Use only the relevant checklist.

### Web
- **Basic Recon**: HTML, headers (Server, X-Powered-By), cookies, redirects, robots.txt, sitemap, security.txt, `.git`, `.env`, `.DS_Store`, source maps.
- **Advanced Recon**: API/GraphQL endpoints, JS bundles (webpack/parcel), backup files (`.bak`, `~`), parameter discovery (`arjun`).
- **Surface Expansion**: Directory/Content brute-force (`ffuf`, `gobuster`, `feroxbuster`), vhost enumeration, subdomains.
- **Contextual Fuzzing**: If you discover a hidden prefix such as `/_m/`, `/internal/`, or `/api/v2/`, build a small wordlist from local context before broad fuzzing. Pair observed nouns with likely verbs such as `mint`, `forge`, `issue`, `sign`, `grant`, `relay`, `mirror`, `seed`, `sync`, `debug`, `admin`.
- **Smuggling Mutation**: Test raw-header parser disagreements with a byte-exact client, not normalized libraries. Try `Transfer-Encoding: chunked `, `Transfer-Encoding : chunked`, `Content-Length :`, duplicated headers, `_m/Content-Length`, lone `\n`, mixed casing, and conflicting TE/CL combinations.
- **Tooling**: Use **Burp Suite** (Proxy, Repeater, Intruder) for all manual probes.
- **Vulnerability Classes**:
  - **Injection**: SQLi (Error, Union, Blind, Time), NoSQLi, Command Injection, LDAP, XPath.
  - **Server-Side**: SSRF, LFI/RFI, XXE (Billion Laughs, OOB), SSTI (Jinja2, Twig, Mako), Insecure Deserialization (PHP/Python/Java).
  - **Access Control**: IDOR (check UUID vs Incremental ID), Broken Access Control, JWT (No-alg, weak secret, kid injection).
  - **Client-Side**: XSS (Stored, Reflected, DOM), CORS misconfig, CSRF, Prototype Pollution.
  - **Logic/Upload**: File upload (bypass extension/magic bytes), race conditions, type juggling.
- **Cross-Layer Bridge**: If crypto work yields nonce reuse, forgery, replay, or parser confusion, immediately revisit web surfaces for hidden verifier, relay, or forge endpoints that may accept the crafted object.

### Audio
- **Visual Analysis**: Spectrogram (use Audacity or Sonic Visualiser) - look for hidden text/shapes.
- **Classic Encodings**: **SSTV** (Slow Scan TV - use `qsstv`), **DTMF** tones (phone dial pads), **Morse code**, Baudot.
- **Signal Processing**: Speed/Pitch shifting, Reversing, Phase inversion, **Multi-channel analysis** (check L/R differences).
- **Steganography**: LSB stego (use `DeepSound` or `SilentEye`), embedded files (check for ZIP/images in audio).

### Crypto
- **Attack Catalog**:
  - **Classical**: XOR (single-byte, repeating-key + crib dragging), Vigenère, substitution ciphers.
  - **RSA**: Small `e` (nth root), Håstad broadcast (multiple ciphertexts), Common Modulus, Wiener's attack (low private exponent `d`), Fermat factorization (close `p,q`), Boneh-Durfee, Coppersmith / Lattice-based attacks.
  - **ECC**: Smart's attack (anomalous), MOV, invalid/singular curve, ECDSA nonce reuse.
  - **Block Ciphers / Symm**: CBC Bit-flipping, ECB Byte-at-a-time (oracle), Padding Oracle (Vaudenay), Nonce reuse in CTR/GCM.
  - **Discrete Log**: Pohlig-Hellman, Baby-step Giant-step.
  - **Hash & RNG**: Collision (MD5/SHA1), Multi-collisions, Length extension. RNG prediction (LCG, Mersenne Twister / randcrack).
- **Tooling**: **SageMath** (for LLL, ECC, complex modular math), `RsaCtfTool`, `factordb`, `CyberChef`.

### Pwn
- **Setup & Libc Workflow**: Start with `file`, `checksec`, and `ldd`. Always test local first. For libc: leak address + `libc-database` or `libc.rip` (do not guess version blindly). If Docker is provided, extract native libc/ld.
- **Technique Map**:
  - **Stack**: ret2win, ret2libc (leak address + system), ROP (Return Oriented Programming), SROP (Sigreturn).
  - **Bypasses**: Canary bypass (leak or brute), ASLR bypass (leak or partial overwrite), NX/DEP (ROP), PIE (leak base).
  - **Strings**: Format string (read/write to stack/GOT).
  - **Heap**: tcache/fastbin poisoning, Use-After-Free (UAF), Double Free, Unsafe Unlink.
  - **Advanced**: GOT/PLT overwrite, one_gadget execution, seccomp bypass.
- **Tooling**: `pwntools`, `pwndbg` / `GEF`, `ROPgadget`, `one_gadget`, `checksec`, `ldd`, `libc-database`, `libc.rip`.

### Stego & Images
- **Image Analysis**: Metadata (ExifTool), Dimensions (check if cropped), Color Channels, LSB (zsteg, StegSolve).
- **File Integrity**: `pngcheck` (check for CRC errors/appended data), `binwalk` (carving).
- **Brute Force**: **stegseek** (fast steghide brute with `rockyou.txt`), `stegcracker`.

### Forensics & Archives
- **Archive Attacks**: **bkcrack** (known-plaintext for ZIP), `fcrackzip`, `john`, `hashcat` (for protected RAR/ZIP/7z).
- **File Carving**: `foremost`, `bulk_extractor`, `binwalk -e`.
- **Binary Plaintext Audit**: For unknown blobs or token samples, inspect raw hex first. Check for null bytes, fixed-size records, repeated offsets, block alignment, and endian-looking counters before trying UTF-8 or JSON assumptions.
- **PCAP / Network**:
  - Protocol extraction (HTTP, FTP, SMB objects).
  - **USB HID**: Decode keystrokes / mouse movements from USB pcap.
  - **Wireshark Actions**: Follow Stream (TCP/UDP), Export Objects, Decode As (if non-standard port), tshark filtering, **TLS Decryption** (use SSLKEYLOGFILE or RSA key to decrypt traffic).
- **Memory/Disk**: Volatility (process list, filescan, cmdline), MFT analysis, Registry analysis.

### OSINT / Misc
- **Search & Recon**: Reverse image search (Yandex, Google, Bing), EXIF geolocation. Username enumeration (`sherlock`), OSINT platforms (Shodan, Censys).
- **Web**: Wayback Machine, Google Dorking, domain history, DNS records.
- **Jail**: pyjail (check `__builtins__`, `__mro__`, `__subclasses__`), JS sandbox (vm2/proxies), rbash/ssh-jail.

### Reverse Engineering
- **Static Analysis**: Decompile/Disassemble based on language. C/C++ (Ghidra, IDA, Binary Ninja), C# (dnSpy, ILSpy), Java/APK (jadx, JD-GUI), Python (uncompyle6, pycdc, decompyle3), WASM (wasm2c, WABT).
- **Dynamic Analysis**: Debugging (GDB/GEF, x64dbg), Hooking/Instrumentation (Frida), Tracing (strace, ltrace).
- **Advanced Techniques**: Symbolic Execution (angr, Triton), SMT Solvers (Z3), Anti-debugging bypass, Obfuscation/Packer analysis.

### Remote TCP / Unknown Protocol
- **Initial Interaction**: Connect using `nc` or `pwntools`. Start with read-only observation before sending commands. Do NOT spam the remote service.
- **Protocol Analysis**: Map out the state machine. Document a "protocol table" of all commands, parameters, and expected responses.
- **Crypto-Oracles**: If behavior is crypto-related, analyze oracle constraints (chosen plaintext/ciphertext, nonce reuse, sample limits, one-time oracles).
- **Vulnerability Hunting**: Identify state-changing commands. Look for logic flaws, type confusion, overflow in custom parsing, or out-of-order execution in the state machine.
- **Rabbit-Hole Detection**: If a service keeps responding but creates no new artifact, no cross-service state change, and no verifier improvement, freeze it as a likely decoy and pivot.

### Video / Platform
- **Extraction**: `yt-dlp -F` to list all available formats/streams. Download specific streams including hidden or alternate tracks.
- **Analysis**: Check storyboard, manifest files (M3U8/MPD), and subtitles. Remember that "side artifacts may be the intended path" (e.g., thumbnail, metadata, alternate audio track).

## Core Dispatcher Workflow
Use this order for every challenge: inventory → classify → load correct ctf-* skill → hypothesis table → small test → exploit → verify.
- Load only the matching category skill.
- Do not edit installed skill files; record feedback in `work/skill_feedback.md` or `~/.codex/ctf-evals/history.md`.
- Keep `solve_log.md` short with required sections: Known facts, Hypotheses, Failed paths / Do Not Repeat, Next best test.
- Wrap solve/build/test commands with `timeout 120s` by default.
- Verify final flags with challenge logic, local checker, remote validation, or reproducible proof.

## Strong First Checks
### Pwn first checks
- `file`, `checksec`, `ldd`, `strings`, local crash repro, libc/ld identification if provided, input format and crash surface.

### Crypto first checks
- Parse parameters, identify primitive, check modulus/curve/cipher mode, write a small sanity script, test obvious weak cases before advanced attacks.
- Compare at least two raw samples byte-by-byte before assuming text serialization; stable offsets often reveal nonce fields, counters, or fixed-layout structs.

### Reverse first checks
- `file`, `strings`, imports/symbols, basic control-flow overview, run safely if possible, emulate/instrument only after static triage.

### Forensics first checks
- Magic bytes, file sizes, `binwalk`, `exiftool`, `foremost`, archive listing, PCAP protocol summary if applicable.

### Web first checks
- Source/HTML, headers, cookies/session behavior, endpoints, auth flow, JS routes, robots/sitemap/static files, API behavior.
- If one hidden route exists, infer likely siblings from naming conventions before assuming the route list is complete.
