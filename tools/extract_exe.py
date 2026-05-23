"""Extract printable strings from Pe/Land/Space.EXE, classify into UI vs noise.

Strategy:
  1. Find every contiguous run of printable bytes >= 5 chars, NUL-terminated.
  2. Classify:
     - NOISE: looks like C runtime (e.g. "MS Run-Time Library", "Microsoft"),
              filename ("HELLO.EXE"), library symbol, single token < 4 chars
     - DEBUG: short identifiers (no spaces), variable name patterns
     - UI:   has spaces + alphabetic + printable structure
  3. Emit TSV: file_offset, len, original, translation_zh, kind, notes
"""
import os, re, struct, sys

ROOT = r"D:\03_game\plant_edge_cht"
ORIG = os.path.join(ROOT, "original")
OUT  = os.path.join(ROOT, "translations", "exe")

EXE_FILES = [
    ('Land.exe',  'land'),
    ('Pe.exe',    'pe'),
    ('Space.EXE', 'space'),
]

NOISE_PATTERNS = [
    re.compile(r'^MS Run-Time'),
    re.compile(r'Copyright \(c\)'),
    re.compile(r'^[\d\.\-\: ]+$'),    # all-numeric / dates
    re.compile(r'^[A-Z_]+$'),         # all upper underscore -> likely symbol
    re.compile(r'^\$\$\$'),           # debug markers
    re.compile(r'^[a-z]+\.(exe|com|cfg|dat|cc)$', re.I),  # filenames
]

def classify(s):
    if any(p.search(s) for p in NOISE_PATTERNS):
        return 'NOISE'
    # Pure printable, has a space, has at least 2 alpha chars
    has_space = ' ' in s
    has_alpha = sum(1 for c in s if c.isalpha()) >= 3
    has_format = '%' in s
    if has_space and has_alpha:
        return 'UI'
    if has_format:
        return 'UI'   # printf format strings, important
    if has_alpha and len(s) >= 6:
        return 'DEBUG'   # could be label, error code identifier
    return 'NOISE'

def extract_strings(data, minlen=5):
    """Find all NUL-terminated printable runs >= minlen."""
    out = []
    i = 0
    n = len(data)
    while i < n:
        if 0x20 <= data[i] < 0x7F:
            start = i
            while i < n and 0x20 <= data[i] < 0x7F:
                i += 1
            # Check NUL terminator
            if i < n and data[i] == 0 and (i - start) >= minlen:
                out.append((start, i - start, data[start:i].decode('latin-1')))
            i += 1
        else:
            i += 1
    return out

def tsv_escape(s):
    return s.replace('\\', '\\\\').replace('\t', '\\t')

def main():
    os.makedirs(OUT, exist_ok=True)
    for fname, prefix in EXE_FILES:
        src = os.path.join(ORIG, fname)
        if not os.path.exists(src):
            print(f"SKIP missing: {src}"); continue
        data = open(src, 'rb').read()
        all_strs = extract_strings(data, minlen=5)
        # Classify
        by_kind = {'UI': [], 'DEBUG': [], 'NOISE': []}
        for off, ln, s in all_strs:
            by_kind[classify(s)].append((off, ln, s))

        out_path = os.path.join(OUT, f"{prefix}_strings.tsv")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write("file_offset\tlen\tkind\toriginal_en\ttranslation_zh\tnotes\n")
            # Order: UI first, then DEBUG, then NOISE (each by file_offset)
            for kind in ('UI', 'DEBUG', 'NOISE'):
                for off, ln, s in sorted(by_kind[kind]):
                    f.write(f"0x{off:08X}\t{ln}\t{kind}\t{tsv_escape(s)}\t\t\n")
        print(f"  {fname:>10s} -> {prefix}_strings.tsv  total={len(all_strs)}  UI={len(by_kind['UI'])}  DEBUG={len(by_kind['DEBUG'])}  NOISE={len(by_kind['NOISE'])}")

if __name__ == '__main__':
    main()
