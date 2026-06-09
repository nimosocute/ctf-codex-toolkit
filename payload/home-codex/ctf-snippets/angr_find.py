#!/usr/bin/env python3
import angr
import claripy

BIN = './chall'
proj = angr.Project(BIN, auto_load_libs=False)
arg = claripy.BVS('arg', 8 * 32)
state = proj.factory.full_init_state(args=[BIN, arg])
for byte in arg.chop(8):
    state.solver.add(byte >= 0x20, byte <= 0x7e)

simgr = proj.factory.simulation_manager(state)
# TODO: set find/avoid addresses or output predicates.
# simgr.explore(find=0x401234, avoid=0x401000)
print(simgr)
