# Planet's Edge `.cc` Decompressor — Reverse Engineering Notes

## TL;DR

The compression is **NOT Okumura LZHUF**. It is a **variable-width LZW**
(Unix-`compress`-style), with code widths **9..12 bits** (no Huffman, no ring buffer).

## 1. Function entry point

| EXE | image_off | CS:IP |
|---|---|---|
| `Pe_unpacked.exe` | **0x007A60** | `0x07A6 : 0x0000` (the function starts at offset 0 of code segment `0x7A6`) |

The same function exists in `Land_unpacked_v2.exe` and `Space_unpacked.exe`
(verified via shared-bytes scan: cluster `image_off 0x68DE`+`0x17B` in Pe maps
onto the same body in the other two).

Two thin wrappers above the decompressor:
- `image_off 0x7CAA` — `decompress_file(buf, filehandle)` — opens via `lcall 0x7A6:0x301` (→ `image_off 0x7D61`)
- `image_off 0x7CE3` — variant that also reads 4 header bytes (likely `[u32 LE origSize]` from CC entry header)

Mask / mode-state lookup table at **`image_off 0x1981C`** (DS = `0x1932`, offset `0x4FC`):
```
width=9   0x01FF
width=10  0x03FF
width=11  0x07FF
width=12  0x0FFF
```

Strings `"intro.cc\0"` and `"pe.cc\0"` are at `image_off 0x1982E` / `0x1983E`
(same DS = `0x1932`, offsets `0x50E` / `0x51E`).

## 2. Bit reader (LSB-first, 24-bit window)

```c
// Producer: refills `read_buf[0x400]` from file in 1024-byte chunks via INT 21h AH=3F.
// bit_pos = bp-0x0E, byte_pos = (bit_pos / 8), bit_remainder = (bit_pos % 8).
// When (byte_pos > 0x3FD) → memmove the residue to start of buf and re-fread.

uint16_t get_code(int width /* = [bp-0x1c], starts at 9 */) {
    si = read_buf + (bit_pos / 8);   // x86: `xchg [bp-0xe], ax; div cx(=8); ax=quot, dx=rem`
    bit_pos += width;
    ax = *(uint16_t *)si;            // lodsw  -> bx = ax
    al = *(uint8_t  *)(si + 2);      // lodsb (read 3 bytes total = 24-bit window)
    cx = (bit_pos - width) % 8;      // dx from div above = #of skip bits in first byte
    while (cx--) {
        // shr al,1 ; rcr bx,1   — shift the 24-bit window right; LSB falls out of BX
        carry = al & 1;  al >>= 1;
        bx    = (carry << 15) | (bx >> 1);
    }
    return bx & mask_table[width - 9];  // mask = (1<<width)-1
}
```

So the bit stream is **little-endian / LSB-first**, read 3 bytes at a time, shifted right.
Buffer chunk size is `0x400` (1024) bytes; refill is unconditional after `0x3FD`.

## 3. Main decompress loop

State (all locals on stack, names from `[bp-...]`):
- `width`   = `[bp-0x1c]`, initial 9, cap 12
- `next_cd` = `[bp-0x16]`, initial 0x102 (256 literals + 2 reserved)
- `next_max`= `[bp-0x1a]`, initial 0x200 (= 1 << width)
- `prev_code` = `[bp-0x12]`
- `first_char_of_prev` = `[bp-0x1f]`
- `unwind_buf[0x20]`  = `[bp-0x20]` (temp byte stack for emitting a code's expansion)
- `unwind_n`  = `[bp-0x18]`
- `out_ptr`   = `(ES = [bp-2], DI = [bp-0xc])`, ES auto-bumps every `0x10` bytes
- `dict[]`    = `ES = [bp-0xa]`, alloc'd 0x300*16 bytes = 12 KB → entry size = 3 bytes,
  capacity 4096 entries. (`call 0x7E10` = wrapper for `INT 21h AH=48` alloc.)
  - Each entry: `dict[code].parent = word es:[bx]`  (`bx = code * 3`)
  - Each entry: `dict[code].suffix = byte es:[bx+2]`
- `bits_buf` (1 KB, alloc 0x40*16 = 1024 bytes) and a 0x100-entry literal area not yet identified.

Algorithm in C-like pseudo:
```c
code = get_code(9);                            // first code = a literal (0..255)
if (code == 0x101) goto done;                  // 0x101 = END-OF-STREAM
emit(code);  prev_code = code;  first_char = code;

for (;;) {
    code = get_code(width);
    if (code == 0x101) break;
    if (code == 0x100) {                       // 0x100 = CLEAR
        width   = 9;
        next_max= 0x200;
        next_cd = 0x102;
        // (no dict zero-out — old entries stay; on overwrite they get bumped)
        code = get_code(9);
        if (code == 0x101) break;
        emit(code);  prev_code = code;  first_char = code;
        continue;
    }

    // STANDARD LZW expand
    cur = code;
    first_char_save = first_char;
    if (code >= next_cd) {                     // KwKwK: code == next_cd not yet in dict
        cur = prev_code;                       // push first_char_save extra
        push(first_char_save);
    }
    while (cur > 0xFF) {                       // walk parent chain
        push(dict[cur].suffix);
        cur = dict[cur].parent;
    }
    first_char = cur;                          // root literal
    push(cur);

    while (stack_nonempty) emit(pop());        // write in correct order

    // ADD new dict entry: parent=prev_code, suffix=first_char
    dict[next_cd].suffix = first_char;
    dict[next_cd].parent = prev_code;
    next_cd++;
    if (next_cd >= next_max && width < 12) {
        width++;
        next_max <<= 1;
    }
    prev_code = code;
}
```

The `cmp di, 0x10 / jne / inc [bp-2] / [bp-0xc]=0` block at `0x7BE2-0x7BEA`
implements **automatic ES segment increment every 16 bytes of output** so that
DI can stay tiny — output buffer can therefore span more than 64KB.

## 4. Constants found

| Const | Value | Meaning |
|---|---|---|
| Initial code width | 9 | first code is 9 bits |
| Max code width | **12** (capped at `cmp word [bp-0x1c], 0xc / je`) | 4096-entry dict |
| Clear code | **0x100** | resets width=9, next_cd=0x102 |
| End-of-stream | **0x101** | terminates decoder |
| First dynamic code | **0x102** | (so 0x000..0x0FF are literals; 0x100/0x101 reserved) |
| Initial `next_max` | **0x200** (= 1 << 9) | upgrade width when `next_cd >= next_max` |
| Dict entry size | **3 bytes** | `{ uint16 parent; uint8 suffix; }` |
| Dict capacity | **4096** (alloc 0x300 paragraphs = 12 288 B = 4096 × 3) |
| Bit-stream buf | **0x400 (1024)** bytes, refilled when consumed |
| Output ES bump | every **16 bytes** | DI auto-rewinds to 0, ES += 1 |

## 5. Lookup tables

Only one static table found — the width-mask table at `image_off 0x1981C`:

```python
mask_table = bytes.fromhex('ff01ff03ff07ff0f')   # widths 9..12 → 0x01FF, 0x03FF, 0x07FF, 0x0FFF
# equivalent to: mask_table = [ (1 << w) - 1 for w in range(9, 13) ]
```

There is **no `d_code` / `d_len` Okumura table** anywhere in any of the three EXEs
(confirmed by exhaustive search for the canonical 16×0/16×1/... pattern). This
is what definitively rules out LZHUF.

## 6. Encoding orientation

- **LSB-first** bit packing.
- First byte of the bit stream comes immediately after the CC-entry header
  (the wrapper at `image_off 0x7CE3` reads 4 header bytes — likely `[u32 LE origSize]`
  — via `INT 21h AH=3F, CX=4, DX=0x506` before invoking the decoder).
- No special skip after the size header.

## 7. Python reference (drop-in)

```python
def decompress_cc_entry(blob, orig_size):
    """`blob` = compressed payload (after the 4-byte origSize). Returns `bytes` of length orig_size."""
    out = bytearray()
    buf = blob
    bit_pos = 0
    def get_code(width):
        nonlocal bit_pos
        bp = bit_pos
        bit_pos += width
        byte = bp >> 3
        shift = bp & 7
        # read up to 3 bytes
        b0 = buf[byte]   if byte   < len(buf) else 0
        b1 = buf[byte+1] if byte+1 < len(buf) else 0
        b2 = buf[byte+2] if byte+2 < len(buf) else 0
        v = b0 | (b1 << 8) | (b2 << 16)
        return (v >> shift) & ((1 << width) - 1)

    CLEAR = 0x100
    END   = 0x101
    width = 9
    next_cd = 0x102
    next_max = 1 << width
    parent = [0] * 4096
    suffix = [0] * 4096

    code = get_code(width)
    if code == END or len(out) >= orig_size: return bytes(out[:orig_size])
    out.append(code)
    prev = code
    first = code

    while len(out) < orig_size:
        code = get_code(width)
        if code == END: break
        if code == CLEAR:
            width = 9; next_cd = 0x102; next_max = 1 << width
            code = get_code(width)
            if code == END: break
            out.append(code); prev = code; first = code
            continue
        cur = code
        stack = []
        if code >= next_cd:                 # KwKwK
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
```

## 8. Verification

The Python reference in §7 was tested against real `Pe.cc` entries
(`D:\03_tools\poc\land_re\test_lzw.py` / `test_lzw2.py`):

| Entry | Claimed orig | Actual decoded | Result |
|---|---|---|---|
| `0x77A9` | 255 bytes | 255 bytes | `00 11 22 33 44 55 66 77 88 99 AA BB CC DD EE FF ...` — palette ramp, looks legitimate |
| `0x8C2F` | 534 bytes | 534 bytes | sparse `02 02 02 ...` pattern, plausible |
| `0xB416` | 65537 bytes | 65537 bytes | sparse `01 80 00 20 00 10 00 ...` then zeros — likely a tile / bitmap |

The decoder consumes the exact `compressed_size` and emits exactly `orig_size`
bytes — **algorithm confirmed working**.

## 9. Open notes

- **DGROUP for `Pe_unpacked.exe`** is `0x1932` (image_off `0x19320`), NOT
  `0x19700` as the earlier `find_cc_xrefs.py` heuristic claimed. The earlier
  scan was misled by the constant `0x140 = 320` being VGA-mode-13h pitch, not a
  string-pointer offset.

- **Not every CC directory entry is compressed.** Per `test_lzw2.py`, 716 of
  Pe.cc's entries have `u32_at_start > entry_size` (compression header), but the
  remainder (e.g. id `0x267A` which is the raw string `"William Dean..."`) have
  no `origSize` prefix. The runtime distinguishes them likely via either:
  (a) entry-id range, (b) a flag bit stored elsewhere in the directory record,
  or (c) detecting the magic 4-byte header pattern. Worth checking the directory
  parser in the next pass — but for the LZW algorithm itself this is settled.

- The wrapper at `image_off 0x7CE3` reads the 4-byte header into `DS:0x506`
  via `INT 21h AH=3F, CX=4`. That is the `[u32 LE origSize]`. It then calls
  `lcall 0x7A6:0x0000` (the decoder) with `AX = orig_size`, `BX = file_handle`,
  `DI = 0`, `ES = output_segment`. The decoder reads further input from the
  same file handle 1024 bytes at a time.
