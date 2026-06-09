#!/usr/bin/env python3
from pathlib import Path
from scapy.all import rdpcap, TCP, UDP, Raw

pcap = Path('capture.pcap')
packets = rdpcap(str(pcap))
print('packets', len(packets))
for i, pkt in enumerate(packets[:20]):
    print(i, pkt.summary())

# TODO: filter streams/protocols and extract payloads.
for pkt in packets:
    if Raw in pkt and (TCP in pkt or UDP in pkt):
        data = bytes(pkt[Raw].load)
        if b'flag' in data.lower():
            print(data[:200])
