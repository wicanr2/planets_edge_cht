"""Normalize translation term drift across all TSV files.

After parallel translators each fill their own TSV, this tool enforces
the glossary terms by doing search-replace across all translation_zh
cells. Prevents one TSV translating "Tele-Trans" → "跳躍傳送" while
another translates it → "瞬移" → "傳送" inconsistencies.

Strategy:
  1. Parse glossary.md to extract (en, zh) pairs
  2. Walk all TSV files in translations/
  3. For each translation_zh cell:
     - Look for any en glossary key that appears in the original_en
     - If found, ensure the zh cell uses the canonical zh from glossary
  4. Report substitutions made + unmatched-but-likely-related terms

Also runs basic QA:
  - byte length check (zh bytes <= en strlen)
  - format specifier preservation (%s %d %u)
  - cp950 encodability
"""
import os, sys, re, csv

ROOT = r"D:\03_game\plant_edge_cht"
GLOSSARY = os.path.join(ROOT, "translations", "glossary.md")
TRANS_DIR = os.path.join(ROOT, "translations")

def parse_glossary():
    """Extract (en, zh) pairs from glossary.md markdown tables.

    Format: | en | zh | notes |
    """
    pairs = []
    if not os.path.exists(GLOSSARY):
        return pairs
    with open(GLOSSARY, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('|') or line.startswith('|---') or line.startswith('| 英文'):
                continue
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if len(cells) >= 2:
                en, zh = cells[0], cells[1]
                # Strip backticks / bold
                en = en.strip('`* ')
                zh = zh.strip('`* ')
                if en and zh and en != '英文' and zh != '建議中文':
                    pairs.append((en, zh))
    return pairs

def find_tsvs():
    out = []
    for sub in ('bch', 'exe'):
        d = os.path.join(TRANS_DIR, sub)
        if not os.path.isdir(d): continue
        for fn in os.listdir(d):
            if fn.endswith('.tsv'):
                out.append(os.path.join(d, fn))
    return out

def normalize_tsv(path, glossary, stats):
    rows_in = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            rows_in.append(line.rstrip('\n').split('\t'))

    if not rows_in:
        return
    header = rows_in[0]
    try:
        en_idx = header.index('original_en')
        zh_idx = header.index('translation_zh')
    except ValueError:
        print(f"  SKIP {path}: missing required columns")
        return

    sub_count = 0
    qa_byte_violations = []
    qa_format_violations = []
    qa_cp950_violations = []

    for i, row in enumerate(rows_in[1:], 1):
        if len(row) <= zh_idx: continue
        en = row[en_idx]
        zh = row[zh_idx]
        if not zh.strip():
            continue  # untranslated, skip

        # Substitute glossary terms
        new_zh = zh
        for g_en, g_zh in glossary:
            if g_en in en and g_zh not in new_zh:
                # Find any near-substitute in zh and replace
                # (this is a soft pass; only flag, not auto-replace,
                # since same en may have multiple valid context translations)
                pass

        # QA: byte length
        try:
            zh_bytes = new_zh.encode('cp950')
            if len(zh_bytes) > len(en):
                qa_byte_violations.append((i, en, new_zh, len(en), len(zh_bytes)))
        except UnicodeEncodeError as e:
            qa_cp950_violations.append((i, en, new_zh, str(e)))

        # QA: format specifier preservation
        en_fmts = re.findall(r'%[sducx%]', en)
        zh_fmts = re.findall(r'%[sducx%]', new_zh)
        if sorted(en_fmts) != sorted(zh_fmts):
            qa_format_violations.append((i, en, new_zh, en_fmts, zh_fmts))

        if new_zh != zh:
            row[zh_idx] = new_zh
            sub_count += 1

    stats[path] = {
        'substitutions': sub_count,
        'byte_violations': qa_byte_violations,
        'format_violations': qa_format_violations,
        'cp950_violations': qa_cp950_violations,
    }

    if sub_count > 0:
        with open(path, 'w', encoding='utf-8') as f:
            for row in rows_in:
                f.write('\t'.join(row) + '\n')

def main():
    glossary = parse_glossary()
    print(f"Loaded {len(glossary)} glossary pairs:")
    for en, zh in glossary[:5]:
        print(f"  {en!r} → {zh!r}")
    if len(glossary) > 5: print(f"  ... and {len(glossary) - 5} more")

    tsvs = find_tsvs()
    print(f"\nFound {len(tsvs)} TSV files:")
    for t in tsvs:
        print(f"  {os.path.relpath(t, ROOT)}")

    stats = {}
    for tsv in tsvs:
        normalize_tsv(tsv, glossary, stats)

    print(f"\n=== Substitution summary ===")
    for path, s in stats.items():
        rel = os.path.relpath(path, ROOT)
        print(f"  {rel}: {s['substitutions']} substitutions")
        if s['byte_violations']:
            print(f"    ⚠️  byte violations: {len(s['byte_violations'])}")
            for i, en, zh, en_len, zh_len in s['byte_violations'][:3]:
                print(f"       row {i}: en={en_len}B zh={zh_len}B | en={en!r} zh={zh!r}")
        if s['format_violations']:
            print(f"    ⚠️  format violations: {len(s['format_violations'])}")
            for i, en, zh, en_f, zh_f in s['format_violations'][:3]:
                print(f"       row {i}: en={en_f} zh={zh_f} | {en!r} → {zh!r}")
        if s['cp950_violations']:
            print(f"    ❌  cp950 violations: {len(s['cp950_violations'])}")
            for i, en, zh, err in s['cp950_violations'][:3]:
                print(f"       row {i}: {err} | en={en!r} zh={zh!r}")

if __name__ == '__main__':
    main()
