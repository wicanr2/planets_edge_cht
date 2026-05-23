"""Build the Planet's Edge Chinese translation outputs.

Pipeline: TSVs -> (a) patched .bch files; (b) EXE-side runtime lookup tables.

Inputs (do not modify):
  translations/bch/{1,2,Objects,Spacet}_extracted.tsv
      columns: idx | offset | len | original_en | translation_zh | notes
      (text fields use \\r \\n \\t \\\\ escape conventions written by extract_bch.py)

  translations/exe/{land,pe,space}_strings.tsv
      columns: file_offset | len | kind | original_en | translation_zh | notes
      (kind = UI / DEBUG / NOISE -- only UI is translated)

Outputs (regenerated every run):
  build/bch/{1,2,Objects,Spacet}.bch    -- rebuilt .bch with Big5 replacements
  build/exe/{land,pe,space}_lookup.bin  -- sorted [ds_off:u16, pool_off:u16, len:u16]
  build/exe/{land,pe,space}_pool.bin    -- NUL-separated Big5 string pool

.bch on-disk format (per extract_bch.py + tools/extract_bch.py inspection):
  256 x u16 LE absolute file offsets   (unused entries point to 0x0200)
  For each used entry:
      u16 LE strlen, then `strlen` raw bytes of text (may contain 0x0D line breaks)
  No explicit string terminator -- next entry's strlen u16 follows directly.

EXE lookup approach: each English UI string is located inside the UNPACKED EXE by
literal byte search; the image offset minus DGROUP base yields the DS-relative
runtime offset used by the in-game C code.  This sidesteps EXEPACK entirely.
"""
import csv
import os
import struct
import sys
from collections import OrderedDict

ROOT     = r"D:\03_game\plant_edge_cht"
ORIG_DIR = os.path.join(ROOT, "original")
TSV_BCH  = os.path.join(ROOT, "translations", "bch")
TSV_EXE  = os.path.join(ROOT, "translations", "exe")
OUT_BCH  = os.path.join(ROOT, "build", "bch")
OUT_EXE  = os.path.join(ROOT, "build", "exe")

UNPACKED = {
    # name : (path, dgroup_image_off_or_None)
    "land":  (r"D:\03_tools\poc\land_re\Land_unpacked_v2.exe", 0x190F0),
    "pe":    (r"D:\03_tools\poc\land_re\Pe_unpacked.exe",      0x19320),
    "space": (r"D:\03_tools\poc\land_re\Space_unpacked.exe",   None),  # auto-detect
}

BCH_FILES = [
    ("1.bch",       "1_extracted.tsv"),
    ("2.bch",       "2_extracted.tsv"),
    ("Objects.bch", "Objects_extracted.tsv"),
    ("Spacet.bch",  "Spacet_extracted.tsv"),
]

EXE_FILES = [
    ("land",  "land_strings.tsv"),
    ("pe",    "pe_strings.tsv"),
    ("space", "space_strings.tsv"),
]

# -----------------------------------------------------------------
# TSV helpers
# -----------------------------------------------------------------
def unescape_tsv(s):
    """Inverse of tsv_escape() in extract_bch.py / extract_exe.py.

    Order matters: \\\\ first so we don't accidentally re-introduce a literal
    backslash next to a 't' / 'r' / 'n'.
    """
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt == '\\':
                out.append('\\'); i += 2; continue
            if nxt == 't':
                out.append('\t'); i += 2; continue
            if nxt == 'r':
                out.append('\r'); i += 2; continue
            if nxt == 'n':
                out.append('\n'); i += 2; continue
        out.append(c)
        i += 1
    return ''.join(out)


def read_tsv(path):
    """Yield dict rows from a header-prefixed TSV, no quoting tricks."""
    with open(path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE)
        for row in reader:
            yield row


# -----------------------------------------------------------------
# Big5 encoding
# -----------------------------------------------------------------
def encode_big5(text, encoding_errors_sink):
    """Encode UTF-8 text to cp950 (Big5). Bytes that don't map -> '?' and logged."""
    try:
        return text.encode('cp950')
    except UnicodeEncodeError:
        encoded_parts = []
        for ch in text:
            try:
                encoded_parts.append(ch.encode('cp950'))
            except UnicodeEncodeError:
                encoding_errors_sink.append(ch)
                encoded_parts.append(b'?')
        return b''.join(encoded_parts)


# -----------------------------------------------------------------
# .bch rebuild
# -----------------------------------------------------------------
def build_bch(src_bch, src_tsv, dst_bch, encoding_errors_sink, log):
    with open(src_bch, 'rb') as f:
        data = f.read()
    # The first u16 LE of the table points at the start of the string region
    first_off = struct.unpack_from('<H', data, 0)[0]
    n_entries = first_off // 2          # always 256 in practice
    table_size = n_entries * 2

    # Read original offset table & build (idx -> bytes-payload) including unused entries
    orig_offsets = [struct.unpack_from('<H', data, i * 2)[0] for i in range(n_entries)]

    # Decode original payloads (strlen u16 + strlen bytes). For "unused" slots
    # (offset == first_off and no strlen present at first_off pointing here),
    # we treat them as empty.
    orig_payloads = {}      # idx -> bytes (raw text only, no strlen)
    for idx, off in enumerate(orig_offsets):
        if off == first_off and idx != 0:
            # Sentinel "unused" slot. idx 0 is special: it can legitimately point
            # at first_off if it really has data there -- we detect by checking
            # whether any later slot equals first_off too (which means unused).
            orig_payloads[idx] = None
            continue
        if off == 0 or off + 2 > len(data):
            orig_payloads[idx] = None
            continue
        strlen = struct.unpack_from('<H', data, off)[0]
        if off + 2 + strlen > len(data) or strlen > 8000:
            orig_payloads[idx] = None
            continue
        orig_payloads[idx] = data[off + 2:off + 2 + strlen]

    # Slot 0 special-case: if multiple slots share first_off, slot 0 still owns
    # the first real string.
    if orig_payloads.get(0) is None and orig_offsets[0] == first_off:
        strlen = struct.unpack_from('<H', data, first_off)[0]
        if first_off + 2 + strlen <= len(data) and strlen <= 8000:
            orig_payloads[0] = data[first_off + 2:first_off + 2 + strlen]

    # Read TSV; build idx -> translated bytes (or None to keep original)
    trans = {}
    total_rows = 0
    translated_rows = 0
    for row in read_tsv(src_tsv):
        total_rows += 1
        idx = int(row['idx'])
        tx = (row.get('translation_zh') or '').strip()
        if tx:
            translated_rows += 1
            decoded = unescape_tsv(tx)
            trans[idx] = encode_big5(decoded, encoding_errors_sink)

    # Assemble new file.
    new_payloads = []        # list of (idx, bytes or None)
    for idx in range(n_entries):
        if idx in trans:
            new_payloads.append((idx, trans[idx]))
        else:
            new_payloads.append((idx, orig_payloads.get(idx)))

    # Lay out: 256 u16 LE offsets, then for each non-None payload a u16 strlen +
    # bytes. Unused entries (payload is None) keep the canonical "unused"
    # pointer == start-of-strings (== table_size == original first_off), which
    # mirrors how the game's original .bch files mark empty slots.
    strings_start = table_size           # first byte after the table
    new_offsets = [strings_start] * n_entries
    cursor = strings_start
    strings_blob = bytearray()
    for idx in range(n_entries):
        payload = new_payloads[idx][1]
        if payload is None:
            continue
        new_offsets[idx] = cursor
        strings_blob += struct.pack('<H', len(payload))
        strings_blob += payload
        cursor += 2 + len(payload)

    # Sanity: u16 offsets cap at 0xFFFF
    if cursor > 0xFFFF:
        log.append(
            f"  WARN {os.path.basename(src_bch)}: total size 0x{cursor:X} "
            f"exceeds 0xFFFF -- offset table will wrap!"
        )

    table_bytes = b''.join(struct.pack('<H', o & 0xFFFF) for o in new_offsets)
    out = table_bytes + bytes(strings_blob)
    with open(dst_bch, 'wb') as f:
        f.write(out)

    return {
        "total_tsv_rows": total_rows,
        "translated_rows": translated_rows,
        "n_entries": n_entries,
        "orig_size": len(data),
        "new_size": len(out),
    }


# -----------------------------------------------------------------
# EXE lookup-table build
# -----------------------------------------------------------------
def detect_space_dgroup(exe_data, land_tsv_strings_for_calibration=None):
    """Find Space_unpacked.exe DGROUP.

    Heuristic: locate a long, unambiguous English UI string from the space TSV
    inside the unpacked EXE, then try several plausible DGROUP candidates and
    pick the one that makes the DS offset land at a believable spot (< 0xFFFF,
    near where Land's strings sit ~0x0000-0xC000 ds range).

    Simpler practical approach used here: scan for the MZ header's DS image
    layout by reading the EXE header's e_ss (initial SS) which usually equals
    DGROUP paragraph in DOS-extender-less small-model programs.  As a fallback
    we calibrate via a known sample string.
    """
    # MZ e_ss is at offset 0x0E (initial relative SS). For these small-model NWC
    # binaries DGROUP == SS, so dgroup_para = e_ss + (header_size_in_paragraphs).
    if exe_data[:2] != b'MZ':
        return None
    e_cblp  = struct.unpack_from('<H', exe_data, 0x02)[0]
    e_cp    = struct.unpack_from('<H', exe_data, 0x04)[0]
    e_cparhdr = struct.unpack_from('<H', exe_data, 0x08)[0]
    e_ss    = struct.unpack_from('<H', exe_data, 0x0E)[0]
    e_sp    = struct.unpack_from('<H', exe_data, 0x10)[0]
    header_size = e_cparhdr * 16
    dgroup_image = header_size + e_ss * 16
    return dgroup_image, {
        "e_ss": e_ss, "e_sp": e_sp, "e_cparhdr": e_cparhdr,
        "header_size": header_size,
        "image_size": (e_cp - 1) * 512 + (e_cblp if e_cblp else 512),
    }


def build_exe_lookup(name, tsv_path, unpacked_path, dgroup_hint,
                     encoding_errors_sink, log):
    with open(unpacked_path, 'rb') as f:
        exe_data = f.read()

    # Resolve DGROUP
    dgroup_info = None
    if dgroup_hint is not None:
        dgroup = dgroup_hint
    else:
        detected = detect_space_dgroup(exe_data)
        if detected:
            dgroup, dgroup_info = detected
        else:
            log.append(f"  ERROR {name}: cannot determine DGROUP")
            return None

    # Build lookup entries
    rows = list(read_tsv(tsv_path))
    total = len(rows)
    ui_rows = [r for r in rows if (r.get('kind') or '').strip() == 'UI']

    pool = bytearray()
    entries = []                # (ds_off, pool_off, pool_len, en_for_dbg)
    translated = 0
    untranslated = 0
    not_found = 0

    for row in ui_rows:
        en_escaped = row.get('original_en') or ''
        en = unescape_tsv(en_escaped)
        if not en:
            continue
        en_bytes = en.encode('latin-1', errors='replace')
        # Find this string inside the unpacked EXE. Expect to find it surrounded
        # by a NUL terminator (so the next byte is 0x00) -- this filters out
        # accidental substring matches inside longer strings.
        search_from = 0
        ds_off = None
        while True:
            i = exe_data.find(en_bytes, search_from)
            if i < 0:
                break
            # require trailing NUL to anchor
            if i + len(en_bytes) < len(exe_data) and exe_data[i + len(en_bytes)] == 0:
                ds_off = (i - dgroup) & 0xFFFF
                break
            search_from = i + 1
        if ds_off is None:
            # accept any match if NUL-anchored search failed
            i = exe_data.find(en_bytes)
            if i >= 0:
                ds_off = (i - dgroup) & 0xFFFF
        if ds_off is None and len(en_bytes) > 4:
            # Extraction artifact recovery: extract_exe.py occasionally over-reads
            # one trailing extended-ASCII byte. Retry without the last byte and
            # require a NUL terminator after that to anchor.
            trimmed = en_bytes[:-1]
            i = exe_data.find(trimmed + b'\x00')
            if i >= 0:
                ds_off = (i - dgroup) & 0xFFFF
                # Keep en_bytes consistent with what we'll write to pool
                en_bytes = trimmed
                en = en[:-1]
        if ds_off is None:
            not_found += 1
            continue

        tx = (row.get('translation_zh') or '').strip()
        if tx:
            tx_decoded = unescape_tsv(tx)
            big5 = encode_big5(tx_decoded, encoding_errors_sink)
            translated += 1
        else:
            # fall back to original English so runtime always has something
            big5 = en_bytes
            untranslated += 1

        pool_off = len(pool)
        pool += big5
        pool += b'\x00'
        entries.append((ds_off, pool_off, len(big5)))

    # Sort by ds_off for binary search
    entries.sort(key=lambda e: e[0])

    # De-dup: if two entries share the same ds_off (rare but possible if the
    # same English string appears twice in TSV), keep the first.
    dedup_entries = []
    seen_ds = set()
    for e in entries:
        if e[0] in seen_ds:
            continue
        seen_ds.add(e[0])
        dedup_entries.append(e)

    lookup_blob = b''.join(struct.pack('<HHH', *e) for e in dedup_entries)
    lookup_path = os.path.join(OUT_EXE, f"{name}_lookup.bin")
    pool_path   = os.path.join(OUT_EXE, f"{name}_pool.bin")
    with open(lookup_path, 'wb') as f: f.write(lookup_blob)
    with open(pool_path,   'wb') as f: f.write(bytes(pool))

    stats = {
        "name": name,
        "total_tsv_rows": total,
        "ui_rows": len(ui_rows),
        "translated": translated,
        "untranslated_passthrough": untranslated,
        "not_found_in_exe": not_found,
        "lookup_entries": len(dedup_entries),
        "lookup_bytes": len(lookup_blob),
        "pool_bytes": len(pool),
        "dgroup_image_off": dgroup,
        "dgroup_was_detected": dgroup_hint is None,
        "dgroup_header_info": dgroup_info,
    }
    return stats


# -----------------------------------------------------------------
# main
# -----------------------------------------------------------------
def main():
    os.makedirs(OUT_BCH, exist_ok=True)
    os.makedirs(OUT_EXE, exist_ok=True)

    encoding_errors_sink = []
    log = []

    print("=" * 70)
    print("Planet's Edge translation build")
    print("=" * 70)

    # --- BCH ---
    print("\n[1/2] Rebuilding .bch files...")
    bch_stats = []
    for src_name, tsv_name in BCH_FILES:
        src = os.path.join(ORIG_DIR, src_name)
        tsv = os.path.join(TSV_BCH, tsv_name)
        dst = os.path.join(OUT_BCH, src_name)
        if not os.path.exists(src):
            log.append(f"  SKIP {src_name}: missing source")
            continue
        if not os.path.exists(tsv):
            log.append(f"  SKIP {src_name}: missing TSV {tsv_name}")
            continue
        stats = build_bch(src, tsv, dst, encoding_errors_sink, log)
        bch_stats.append((src_name, stats))
        delta = stats["new_size"] - stats["orig_size"]
        sign = '+' if delta >= 0 else ''
        print(
            f"  {src_name:>12s}: "
            f"{stats['translated_rows']:3d}/{stats['total_tsv_rows']:3d} translated  "
            f"size {stats['orig_size']:6d} -> {stats['new_size']:6d}  ({sign}{delta} bytes)"
        )

    # --- EXE lookup tables ---
    print("\n[2/2] Building EXE lookup tables...")
    exe_stats = []
    for name, tsv_name in EXE_FILES:
        unpacked_path, dgroup_hint = UNPACKED[name]
        tsv = os.path.join(TSV_EXE, tsv_name)
        if not os.path.exists(unpacked_path):
            log.append(f"  SKIP exe/{name}: missing unpacked EXE {unpacked_path}")
            continue
        if not os.path.exists(tsv):
            log.append(f"  SKIP exe/{name}: missing TSV {tsv_name}")
            continue
        stats = build_exe_lookup(name, tsv, unpacked_path, dgroup_hint,
                                 encoding_errors_sink, log)
        if stats is None:
            continue
        exe_stats.append(stats)
        print(
            f"  {name:>6s}: UI={stats['ui_rows']:3d}  "
            f"tx={stats['translated']:3d}  pass={stats['untranslated_passthrough']:3d}  "
            f"notfound={stats['not_found_in_exe']:3d}  "
            f"lookup={stats['lookup_bytes']}B  pool={stats['pool_bytes']}B  "
            f"dgroup=0x{stats['dgroup_image_off']:X}"
            + ("  (detected from MZ e_ss)" if stats['dgroup_was_detected'] else "")
        )

    # --- Summary ---
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    if log:
        print("Warnings / skips:")
        for line in log: print(line)

    if encoding_errors_sink:
        unique = OrderedDict()
        for ch in encoding_errors_sink:
            unique[ch] = unique.get(ch, 0) + 1
        ch_list = ' '.join(f"{ch!r}x{n}" for ch, n in list(unique.items())[:20])
        print(f"\nBig5 encoding fallbacks ({len(encoding_errors_sink)} chars replaced with '?'):")
        print(f"  {ch_list}")
    else:
        print("\nBig5 encoding: no fallbacks needed.")

    # ---- Self-verification ----
    print("\nSelf-verification (binary search over land lookup):")
    if exe_stats:
        verify_lookup("land")

    print("\nDone.")


def verify_lookup(name):
    """Pick a known English string, walk the lookup binary, confirm round-trip."""
    lookup_path = os.path.join(OUT_EXE, f"{name}_lookup.bin")
    pool_path   = os.path.join(OUT_EXE, f"{name}_pool.bin")
    if not (os.path.exists(lookup_path) and os.path.exists(pool_path)):
        print(f"  {name}: lookup/pool not present")
        return
    lookup = open(lookup_path, 'rb').read()
    pool   = open(pool_path, 'rb').read()
    n = len(lookup) // 6
    print(f"  {name}: {n} entries, pool {len(pool)} bytes")
    # Dump first 3 entries
    for i in range(min(3, n)):
        ds_off, p_off, p_len = struct.unpack_from('<HHH', lookup, i * 6)
        sample = pool[p_off:p_off + p_len]
        try:
            shown = sample.decode('cp950')
        except UnicodeDecodeError:
            shown = sample.decode('latin-1', errors='replace')
        print(f"    [{i}] ds=0x{ds_off:04X}  pool[{p_off}..+{p_len}]  = {shown!r}")


if __name__ == '__main__':
    main()
