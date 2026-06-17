# CTF Snippets

Reusable local templates. Copy into a challenge workspace `work/` directory and adapt there. Do not edit installed upstream skills to add boilerplate.

- `z3_template.py` — small SMT solve skeleton.
- `sage_rsa.sage` — RSA/Sage starting point.
- `pwntools_template.py` — local/remote pwn harness.
- `requests_exploit.py` — web session/exploit skeleton with payload variables, optional Base64/Hex encoding, and Base64 response capture. Copy it to `work/exploit.py`.
- `raw_http_socket.py` — raw-socket HTTP template for header mutation, parser disagreements, and request-smuggling probes.
- `endpoint_sibling_runner.py` — scoped hidden-route expansion for an observed prefix such as `/_m/`, with a capped verifier matrix for same-session, client public value, and forged packet tests.
- `binary_sample_triage.py` — binary-first sample triage for null bytes, entropy hints, fixed offsets, and byte-level diffs.
- `angr_find.py` — angr symbolic execution skeleton.
- `pcap_extract.py` — Scapy PCAP triage/extract skeleton.
- `verilator_oracle.cpp` — FPGA/netlist oracle harness starting point.

Example scoped endpoint sibling workflow:

```bash
cp ~/.codex/ctf-snippets/endpoint_sibling_runner.py work/endpoint_sibling_runner.py
timeout 120s python3 work/endpoint_sibling_runner.py \
  --base-url "$URL" \
  --observed /_m/session \
  --observed /_m/mirror \
  --payload-file evidence/forged_packet.bin \
  --oracle-text flag \
  --same-session \
  --client-pub "$PUB" \
  --matrix
```

Keep the candidate set at 20 routes or fewer unless the challenge provides a clear oracle and the broader search is explicitly justified in `solve_log.md`.
