# CTF Tools Inventory

Updated: 2026-06-10T00:27:14

| tool | verification command | install method | status | version/output | known limitations |
|---|---|---|---|---|---|
| python3 | `python3 --version` | system | OK | `Python 3.13.12` |  |
| pwntools | `python3 -c 'import pwnlib; print(pwnlib.__version__)'` | apt or /opt/codex-ctf-python fallback | OK | `4.15.0` |  |
| gdb | `gdb --version` | apt | OK | `GNU gdb (Debian 17.1-3) 17.1 Copyright (C) 2025 Free Software Foundation, Inc. License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html> This is free software: you are free to change and redistribute ` |  |
| checksec | `pwn checksec --help` | apt/pip | OK | `usage: pwn checksec [-h] [--file [elf ...]] [elf ...] Check binary security settings positional arguments: elf Files to check options: -h, --help show this help message and exit --file [elf ...] File to check (for compat` |  |
| z3 | `python3 -c 'import z3; print(z3.get_version_string())'` | apt or /opt/codex-ctf-python fallback | OK | `4.13.0` |  |
| sage | `sage --version || readlink -f "$(command -v sage)"` | apt or /opt/codex-ctf-sage micromamba fallback | OK | `SageMath / command available` | Large install. |
| angr | `python3 -c 'import angr; print(angr.__version__)'` | apt or /opt/codex-ctf-python fallback | OK | `9.2.217` |  |
| binwalk | `binwalk --help` | apt | OK | `Binwalk v2.1.4 Craig Heffner, ReFirmLabs https://github.com/ReFirmLabs/binwalk Usage: binwalk [OPTIONS] [FILE1] [FILE2] [FILE3] ... Disassembly Scan Options: -Y, --disasm Identify the CPU architecture of a file using the` |  |
| exiftool | `exiftool -ver` | apt | OK | `13.50` |  |
| foremost | `foremost -V` | apt | OK | `1.5.7 This program is a work of the US Government. In accordance with 17 USC 105, copyright protection is not available for any work of the US Government. This is free software; see the source for copying conditions. The` |  |
| tshark | `tshark --version` | apt | OK | `TShark (Wireshark) 4.6.4. Copyright 1998-2026 Gerald Combs <gerald@wireshark.org> and contributors. Licensed under the terms of the GNU General Public License (version 2 or later). This is free software; see the file nam` |  |
| radare2 | `r2 -v` | apt | OK | `radare2 6.0.5 0 @ linux-x86-64 birth: git.6.0.5 2025-09-29__06:39:34 options: gpl release -O1 cs:5 cl:2 meson` |  |
| ghidra | `test -x /usr/share/ghidra/ghidraRun && dpkg-query -W -f='${Version}' ghidra` | apt | OK | `12.0.4+ds-0kali1` | GUI tool; version comes from package metadata. |
| verilator | `verilator --version` | apt | OK | `Verilator 5.049 devel rev v5.048-111-g69b3c5f6d (mod)` |  |
| yosys | `yosys -V` | apt or /opt/oss-cad-suite fallback | OK | `Yosys 0.65+57 (git sha1 9d0cdb855, clang++ 18.1.8 -fPIC -O3)` | PATH must include /opt/oss-cad-suite/bin. |
| iceunpack | `command -v iceunpack` | apt | OK | `/usr/bin/iceunpack` |  |
| icebox_vlog | `command -v icebox_vlog` | apt | OK | `/usr/bin/icebox_vlog` |  |
| bitwuzla | `bitwuzla --version` | apt or /opt/oss-cad-suite fallback | OK | `1.0-prerelease` | PATH must include /opt/oss-cad-suite/bin. |
| curl | `curl --version` | apt | OK | `curl 8.18.0 (x86_64-pc-linux-gnu) libcurl/8.18.0 OpenSSL/3.5.5 zlib/1.3.1 brotli/1.2.0 zstd/1.5.7 libidn2/2.3.8 libpsl/0.21.2 libssh2/1.11.1 nghttp2/1.68.0 ngtcp2/1.16.0 nghttp3/1.12.0 librtmp/2.3 mit-krb5/1.22.1 OpenLDA` |  |
| ffuf | `ffuf -V` | apt or Go fallback | OK | `ffuf version: 2.1.0-dev` | guard blocks broad scans unless scoped/approved |
| hashcat | `hashcat --version` | apt | OK | `v7.1.2` | guard blocks brute force unless approved |
| john | `john --list=build-info` | apt | OK | `Version: 1.9.0-jumbo-1+bleeding-aec1328d6c 2021-11-02 10:45:52 +0100 Build: linux-gnu 64-bit x86_64 AVX2 AC OMP SIMD: AVX2, interleaving: MD4:3 MD5:3 SHA1:1 SHA256:1 SHA512:1 System-wide exec: /usr/lib/john System-wide h` | guard blocks brute force unless approved |
| browser_arm | `python3 ~/.codex/tools/ctf_health_check.py --check browser_arm` | local venv/pip | OK | `cloakbrowser 0.3.31; chromium installed; headless launch title=ok` | Uses isolated ~/.codex/tools/browser_arm/.venv plus CloakBrowser cache. |
