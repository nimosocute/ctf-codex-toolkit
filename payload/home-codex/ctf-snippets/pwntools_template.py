#!/usr/bin/env python3
from pwn import *

exe = context.binary = ELF('./chall', checksec=False)
context.log_level = 'info'

HOST, PORT = args.HOST or '127.0.0.1', int(args.PORT or 31337)

def start():
    if args.REMOTE:
        return remote(HOST, PORT)
    return process([exe.path])

io = start()
# TODO: sync prompt, send payload, verify leak/flag.
io.interactive()
