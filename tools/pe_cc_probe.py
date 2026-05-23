"""Probe Planet's Edge .cc archive structure + dump LZHUF entry headers.

Goal: understand the .cc format and the LZHUF variant well enough to:
  1. List all entries (id, offset, size)
  2. Identify cross-archive shared ids
  3. Dump first N bytes of each entry payload — to find LZHUF format hints
     (magic? param table? tree start?)

CC format (1992 NWC, simplified vs MM3):
  [u16 LE count]
  [count × (u16 id, u24 off, u24 size)]
  [payload blobs ...]

Entry payload structure (suspected):
  [u32 LE origSize]   — uncompressed size
  [LZHUF bitstream...]
"""
import os, struct, sys, collections

ROOT = r"D:\03_game_tmp\1992_天際寒星_Planets Edge\PE"
CC_FILES = ['Pe.cc', 'Intro.cc', 'MAP.CC', 'Backup.cc']

def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def u24(b, o): return b[o] | (b[o+1] << 8) | (b[o+2] << 16)
def u32(b, o): return struct.unpack_from('<I', b, o)[0]

def parse_cc(path):
    data = open(path, 'rb').read()
    count = u16(data, 0)
    entries = []
    p = 2
    for i in range(count):
        eid = u16(data, p)
        off = u24(data, p + 2)
        size = u24(data, p + 5)
        entries.append((eid, off, size))
        p += 8
    return data, entries

def hexsnip(buf, n=32):
    return ' '.join(f'{b:02X}' for b in buf[:n])

def analyze():
    print("# Planet's Edge .cc archive probe\n")
    all_entries = {}  # path -> [(id, off, size, first16)]
    id_to_archives = collections.defaultdict(list)  # id -> [archive_name]

    for fname in CC_FILES:
        path = os.path.join(ROOT, fname)
        if not os.path.exists(path):
            print(f"## SKIP missing: {fname}\n"); continue
        data, entries = parse_cc(path)
        all_entries[fname] = []
        print(f"## {fname}")
        print(f"  file_size  = {len(data)}")
        print(f"  count      = {len(entries)}")

        # Stats: payload sizes distribution
        sizes = [s for _, _, s in entries]
        print(f"  size: min={min(sizes)} max={max(sizes)} median={sorted(sizes)[len(sizes)//2]}")

        # Show first 8 entries with first-16-byte hex
        print(f"  first 8 entries:")
        print(f"    idx | id     | offset    | size    | first 16 bytes")
        for i, (eid, off, sz) in enumerate(entries[:8]):
            chunk = data[off:off+16]
            print(f"    {i:3d} | 0x{eid:04X} | 0x{off:08X} | {sz:7d} | {hexsnip(chunk, 16)}")

        # Save all for cross-ref
        for eid, off, sz in entries:
            chunk = data[off:off+16]
            all_entries[fname].append((eid, off, sz, chunk))
            id_to_archives[eid].append(fname)

        # u32 LE first 4 bytes (suspect = origSize)
        print(f"  origSize candidates (first u32 LE of payload):")
        examples = entries[:4] + entries[len(entries)//2:len(entries)//2+2] + entries[-2:]
        for eid, off, sz in examples:
            if off + 4 > len(data): continue
            orig = u32(data, off)
            ratio = sz / orig if orig else 0
            sane = "ok" if 0 < ratio < 4 else "?"
            print(f"    id 0x{eid:04X}  size={sz:6d}  orig={orig:8d}  ratio={ratio:5.2f} {sane}")
        print()

    # Cross-archive shared ids
    shared = {eid: arcs for eid, arcs in id_to_archives.items() if len(arcs) > 1}
    print(f"\n## Cross-archive shared ids: {len(shared)}")
    for eid, arcs in sorted(shared.items())[:20]:
        print(f"  id 0x{eid:04X}: {arcs}")

    return all_entries

if __name__ == '__main__':
    analyze()
