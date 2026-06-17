# CTF Snippets

Reusable local templates. Copy into a challenge workspace `work/` directory and adapt there. Do not edit installed upstream skills to add boilerplate.

- `z3_template.py` — small SMT solve skeleton.
- `sage_rsa.sage` — RSA/Sage starting point.
- `pwntools_template.py` — local/remote pwn harness.
- `requests_exploit.py` — web session/exploit skeleton with payload variables, optional Base64/Hex encoding, and Base64 response capture. Copy it to `work/exploit.py`.
- `raw_http_socket.py` — raw-socket HTTP template for header mutation, parser disagreements, and request-smuggling probes.
- `binary_sample_triage.py` — binary-first sample triage for null bytes, entropy hints, fixed offsets, and byte-level diffs.
- `angr_find.py` — angr symbolic execution skeleton.
- `pcap_extract.py` — Scapy PCAP triage/extract skeleton.
- `verilator_oracle.cpp` — FPGA/netlist oracle harness starting point.
