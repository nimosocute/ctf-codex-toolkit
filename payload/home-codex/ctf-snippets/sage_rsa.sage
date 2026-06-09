# Copy to work/solve.sage and adapt.
# Run: sage solve.sage
from sage.all import *

n = Integer(0)  # TODO
c = Integer(0)  # TODO
e = Integer(65537)

print(f'n bits = {n.nbits()}')
# TODO: choose attack: gcd shared factors, Fermat, small e, Wiener, Coppersmith, lattice.
# Example Fermat skeleton:
# a = ceil(sqrt(n)); b2 = a*a - n
# while not is_square(b2): a += 1; b2 = a*a - n
# p = a - sqrt(b2); q = a + sqrt(b2)
