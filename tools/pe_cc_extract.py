"""Extract all entries from Planet's Edge .cc archives.

Compression: variable-width LZW 9-12 bits, LSB-first (per RE notes in
D:\\03_tools\\poc\\land_re\\lzhuf_re_notes.md).

Entry detection:
  - If first u32 LE is in (size, 0x100000) and decompression succeeds and
    produces exactly orig_size bytes → compressed
  - Else → raw

Output:
  D:\\03_game\\plant_edge_cht\\extracted\\<archive_basename>\\<id>_<orig_size>_<kind>.bin
  Where kind is: 'cmp' (decompressed) or 'raw'
  Plus a summary TSV: D:\\03_game\\plant_edge_cht\\extracted\\index.tsv

Also runs string detection on each entry. Strings >= 10 printable ASCII + space
get logged to D:\\03_game\\plant_edge_cht\\extracted\\strings_found.tsv
"""
import os, struct, sys, re

ROOT_GAME = r"D:\03_game_tmp\1992_天際寒星_Planets Edge\PE"
ROOT_OUT  = r"D:\03_game\plant_edge_cht\extracted"
CC_FILES = ['Pe.cc', 'Intro.cc', 'MAP.CC', 'Backup.cc']

def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def u24(b, o): return b[o] | (b[o+1] << 8) | (b[o+2] << 16)
def u32(b, o): return struct.unpack_from('<I', b, o)[0]


def lzw_decompress(blob, orig_size):
    """variable-width LZW 9-12 bits, LSB-first, clear=0x100, end=0x101."""
    bit_pos = 0
    bl = len(blob)
    def get_code(width):
        nonlocal bit_pos
        bp = bit_pos
        bit_pos += width
        byte = bp >> 3
        shift = bp & 7
        b0 = blob[byte]   if byte   < bl else 0
        b1 = blob[byte+1] if byte+1 < bl else 0
        b2 = blob[byte+2] if byte+2 < bl else 0
        v = b0 | (b1 << 8) | (b2 << 16)
        return (v >> shift) & ((1 << width) - 1)

    out = bytearray()
    CLEAR = 0x100
    END   = 0x101
    width = 9
    next_cd = 0x102
    next_max = 1 << width
    parent = [0] * 4096
    suffix = [0] * 4096

    code = get_code(width)
    if code == END: return bytes(out)
    if code == CLEAR:
        code = get_code(width)
        if code == END: return bytes(out)
    out.append(code & 0xFF)
    prev = code
    first = code

    while len(out) < orig_size:
        code = get_code(width)
        if code == END: break
        if code == CLEAR:
            width = 9; next_cd = 0x102; next_max = 1 << width
            code = get_code(width)
            if code == END: break
            out.append(code & 0xFF); prev = code; first = code
            continue
        cur = code
        stack = []
        if code >= next_cd:
            stack.append(first); cur = prev
        while cur > 0xFF:
            stack.append(suffix[cur]); cur = parent[cur]
        first = cur
        out.append(cur)
        while stack: out.append(stack.pop())
        if next_cd < 4096:
            parent[next_cd] = prev
            suffix[next_cd] = first
            next_cd += 1
            if next_cd >= next_max and width < 12:
                width += 1; next_max <<= 1
        prev = code
    return bytes(out[:orig_size])


def parse_cc(path):
    data = open(path, 'rb').read()
    count = u16(data, 0)
    entries = []
    p = 2
    for _ in range(count):
        eid = u16(data, p)
        off = u24(data, p + 2)
        size = u24(data, p + 5)
        entries.append((eid, off, size))
        p += 8
    return data, entries


def looks_compressed(blob):
    """Returns (is_compressed, orig_size_or_None)."""
    if len(blob) < 8: return False, None
    orig = u32(blob, 0)
    # heuristic: orig should be between size and some large cap
    if not (len(blob) < orig < 0x100000): return False, None
    return True, orig


def find_strings(data, minlen=10):
    """Find runs of printable ASCII (incl. space, CR, LF) >= minlen."""
    out = []
    i = 0; n = len(data)
    while i < n:
        if 0x20 <= data[i] < 0x7F or data[i] in (0x0A, 0x0D):
            start = i
            while i < n and (0x20 <= data[i] < 0x7F or data[i] in (0x0A, 0x0D)):
                i += 1
            if i - start >= minlen:
                # require at least 2 alpha chars to filter out pure punctuation
                alpha = sum(1 for c in data[start:i] if (0x41 <= c < 0x5B) or (0x61 <= c < 0x7B))
                if alpha >= 2:
                    out.append((start, data[start:i]))
        else:
            i += 1
    return out


def detect_kind(data):
    """Categorize entry by content."""
    if not data: return 'empty'
    n = len(data)
    if n < 16: return 'tiny'
    # Count printable / null / high bytes
    printable = sum(1 for b in data[:512] if 0x20 <= b < 0x7F)
    zeros = sum(1 for b in data[:512] if b == 0)
    sample_n = min(n, 512)
    if printable > sample_n * 0.7: return 'text'
    if zeros > sample_n * 0.7: return 'sparse'
    # Common image hint: many bytes of the same value clustered
    # Common audio (digitized) hint: ramps around 0x80
    return 'binary'


def main():
    os.makedirs(ROOT_OUT, exist_ok=True)
    index_path = os.path.join(ROOT_OUT, 'index.tsv')
    strings_path = os.path.join(ROOT_OUT, 'strings_found.tsv')

    summary = []  # (archive, id, off, size, orig, kind_compr, kind_data)
    string_rows = []  # (archive, id, off_in_entry, text)

    with open(index_path, 'w', encoding='utf-8') as idx_f:
        idx_f.write("archive\tid\toff\tsize\torig\tcompressed\tkind\tnotes\n")

        for fname in CC_FILES:
            path = os.path.join(ROOT_GAME, fname)
            if not os.path.exists(path):
                print(f"SKIP {fname}: not found"); continue
            print(f"\n=== {fname} ===")
            data, entries = parse_cc(path)
            arc_name = fname.split('.')[0].lower()
            out_dir = os.path.join(ROOT_OUT, arc_name)
            os.makedirs(out_dir, exist_ok=True)

            n_cmp = 0; n_raw = 0; n_fail = 0
            for eid, off, sz in entries:
                blob = data[off:off+sz]
                is_cmp, orig = looks_compressed(blob)
                payload = None
                cmp_status = ''
                if is_cmp:
                    try:
                        payload = lzw_decompress(blob[4:], orig)
                        if len(payload) == orig:
                            cmp_status = 'cmp'
                            n_cmp += 1
                        else:
                            cmp_status = f'cmp_partial_{len(payload)}'
                            n_fail += 1
                    except Exception as e:
                        cmp_status = f'cmp_fail_{type(e).__name__}'
                        n_fail += 1
                        payload = None
                if payload is None:
                    payload = blob  # raw
                    cmp_status = cmp_status or 'raw'
                    n_raw += 1

                # save
                kind = detect_kind(payload)
                ext = 'txt' if kind == 'text' else 'bin'
                outname = f"{eid:04X}_{len(payload)}_{cmp_status}_{kind}.{ext}"
                with open(os.path.join(out_dir, outname), 'wb') as fout:
                    fout.write(payload)

                idx_f.write(f"{fname}\t0x{eid:04X}\t0x{off:X}\t{sz}\t{orig if orig else ''}\t{cmp_status}\t{kind}\t\n")

                # strings
                for s_off, s_data in find_strings(payload, minlen=10):
                    s_text = s_data.decode('latin-1')
                    s_text = s_text.replace('\r', '\\r').replace('\n', '\\n').replace('\t', '\\t')
                    string_rows.append((fname, f"0x{eid:04X}", s_off, s_text))

            print(f"  entries: {len(entries)}  cmp_ok={n_cmp}  raw={n_raw}  fail={n_fail}")

    # write strings
    with open(strings_path, 'w', encoding='utf-8') as f:
        f.write("archive\tid\toff_in_entry\ttext\n")
        for row in string_rows:
            f.write(f"{row[0]}\t{row[1]}\t{row[2]}\t{row[3]}\n")
    print(f"\nWrote {len(string_rows)} string candidates -> {strings_path}")
    print(f"Wrote index -> {index_path}")


if __name__ == '__main__':
    main()
