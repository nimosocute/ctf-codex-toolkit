#!/usr/bin/env python3
from z3 import *

# Copy to work/solve.py and adapt. Keep constraints small; validate with known examples.
s = Solver()

# Example: 8 printable bytes constrained by a placeholder relation.
xs = [BitVec(f'x{i}', 8) for i in range(8)]
for x in xs:
    s.add(x >= 0x20, x <= 0x7e)

# TODO: add challenge constraints here.
# s.add(...)

if s.check() != sat:
    raise SystemExit('unsat')
m = s.model()
print(bytes([m.eval(x).as_long() for x in xs]))
