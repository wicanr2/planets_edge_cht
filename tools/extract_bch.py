"""Extract all strings from .bch files into TSV for translation.

.bch format:
  [256 x u16 LE offset table]                  ← 512 bytes
  For each entry pointed by offset:
      [u16 LE strlen][text bytes with \r breaks]

Output TSV columns:
  idx | offset | len | original_en | translation_zh | notes
"""
import os, struct, sys

ROOT = r"D:\03_game\plant_edge_cht"
ORIG = os.path.join(ROOT, "original")
OUT  = os.path.join(ROOT, "translations", "bch")

BCH_FILES = ['1.bch', '2.bch', 'Objects.bch', 'Spacet.bch']

def extract(path):
    data = open(path, 'rb').read()
    # First u16 = first entry's offset; offset_table_size = first_offset bytes
    first_off = struct.unpack_from('<H', data, 0)[0]
    n_entries = first_off // 2

    entries = []
    offs = [struct.unpack_from('<H', data, i*2)[0] for i in range(n_entries)]
    # Append size as sentinel end of last entry
    bounds = offs + [len(data)]

    for i in range(n_entries):
        a = offs[i]
        b = bounds[i + 1]
        if a == 0 or a > len(data):
            entries.append((i, a, 0, b''))
            continue
        # First 2 bytes of entry = strlen
        if a + 2 > len(data):
            entries.append((i, a, 0, b''))
            continue
        strlen = struct.unpack_from('<H', data, a)[0]
        text = data[a + 2: a + 2 + strlen]
        # If strlen looks wrong (>1000 bytes, unlikely), guess by segment to next
        if strlen > 2000 or a + 2 + strlen > b:
            text = data[a + 2: b]
            strlen = len(text)
        entries.append((i, a, strlen, text))
    return entries

def tsv_escape(s):
    """Make string safe for TSV: escape \r \n \t \\."""
    return (s.replace('\\', '\\\\')
             .replace('\t', '\\t')
             .replace('\r', '\\r')
             .replace('\n', '\\n'))

def main():
    os.makedirs(OUT, exist_ok=True)
    for fname in BCH_FILES:
        src = os.path.join(ORIG, fname)
        if not os.path.exists(src):
            print(f"SKIP missing: {src}"); continue
        entries = extract(src)
        out_name = fname.replace('.bch', '_extracted.tsv')
        out_path = os.path.join(OUT, out_name)
        nonempty = 0
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write("idx\toffset\tlen\toriginal_en\ttranslation_zh\tnotes\n")
            for idx, off, ln, text in entries:
                if ln == 0:
                    continue
                nonempty += 1
                en = tsv_escape(text.decode('latin-1', errors='replace'))
                f.write(f"{idx}\t0x{off:04X}\t{ln}\t{en}\t\t\n")
        print(f"  {fname:>15s} -> {out_name}: {nonempty}/{len(entries)} nonempty entries")

if __name__ == '__main__':
    main()
