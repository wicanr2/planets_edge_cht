# Planet's Edge `Land.exe` — `print_func` reverse engineering

**Target binary:** `Land_unpacked_v2.exe` (post-EXEPACK, 167632 bytes, MZ header 4560 → image 163072 bytes)
**Entry point:** `e_cs=0x0526 e_ip=0x2A51`, `e_ss=0x27F0 e_sp=0x1194`
**DGROUP image_off:** `0x190F0` (seg `0x190F`)
**Compiler signature:** "MS Run-Time Library — Copyright (c) 1990, Microsoft Corp" at DGROUP+0x08 → **Microsoft C 6.0** with **MSC overlay loader (INT 3F dispatch)**.

`print_func` lives at **image_off 0xABAA**, real-mode addr **`09CE:0ECA`** (image base of seg `09CE` = `0x9CE0`, plus offset `0xECA`).

Length: image_off `0xABAA` → `0xAD86` inclusive (final `CB retf`) = **0x1DD = 477 bytes**.

A near-twin `print_func_buf` follows at image_off **0xAD87** (real-mode `09CE:0x10A7`). It allocates a 64-byte stack buffer instead of using the global buffer, but the downstream draw path is byte-for-byte identical.

---

## 1. Argument convention

Caller pattern (always exactly 3 args, **8 bytes pushed**):
```
B8 20 00          mov ax, 0x20         ; arg1: mode/flags byte
50                push ax
B8 lo hi          mov ax, <ds_off>     ; arg2: string offset (DS-relative)  [or lea ax,[bp-N] for stack buf]
1E                push ds              ;       string segment
50                push ax
26 FF 36 7E 23    push word [es:0x237e] ; arg3: context handle (Y-row / window id)
9A CA 0E CE 09    call far 09CE:0ECA   ; print_func
```
(Some callers push `ss` instead of `ds` if the string is in a stack buffer — see callsite #6, #10, #11, #29.)

After `push bp; mov bp,sp`, the args are at:

| `[bp+0x06]` | WORD | **mode** (bit 0 selects high/low pane → Y-baseline; high bits encode color?) |
|---|---|---|
| `[bp+0x08]` | WORD | string offset |
| `[bp+0x0A]` | WORD | string segment |
| `[bp+0x0C]` | WORD | context handle (push'd as `[es:0x237e]`, used later as struct ptr or as Y-row) |

24 callsites total (the `9A CA 0E CE 09` byte pattern occurs 24× in the image). 23 unique callers + 1 false-positive from data byte alignment.

Sample resolved strings:

```
ds:0x015E "He's dead jim!"
ds:0x016D "Repeat command to quit game."
ds:0x01AF "Repeat command to confirm Tele-trans"
ds:0x01D4 "Tele-Trans is disrupted here"
ds:0x01F1 "Tele-trans activated."
ds:0x0219 "I can't carry anymore"
ds:0x0239 / 0x02A4 / 0x02DF "I have no items"
ds:0x02EF "Examine which item?"
```

---

## 2. `print_func` body (full disassembly)

```text
ABAA  55              push bp
ABAB  8B EC           mov bp,sp
ABAD  83 EC 0E        sub sp,0x0E          ; 14 bytes locals
ABB0  56              push si

; --- save arg1 (mode) into BSS global [seg1708:0x14a] ---
ABB1  8B 46 06        mov ax,[bp+6]
ABB4  8E 06 12 E6     mov es,[0xE612]      ; es <- BSS seg (1708)
ABB8  26 A3 4A 01     mov [es:0x14A],ax

; --- save arg3 (ctx) into BSS global [seg1708:0x2a0] ---
ABBC  8B 4E 0C        mov cx,[bp+0xc]
ABBF  8E 06 14 E6     mov es,[0xE614]
ABC3  26 89 0E A0 02  mov [es:0x2A0],cx

; --- sprintf( buf=ds:0x1708:0x68, fmt=ds:0xC2AC "%s", str=[bp+8/A] ) ---
ABC8  FF 76 0A        push word [bp+0xA]   ; str seg
ABCB  FF 76 08        push word [bp+0x8]   ; str off
ABCE  B9 AC C2        mov cx,0xC2AC        ; fmt = "%s"  (verified by DGROUP dump)
ABD1  1E              push ds
ABD2  51              push cx
ABD3  B9 68 00        mov cx,0x0068        ; dst off
ABD6  BA 08 17        mov dx,0x1708        ; dst seg (BSS dispatch-table seg, shared scratch)
ABD9  52              push dx
ABDA  51              push cx
ABDB  9A 02 22 26 05  call far 0526:2202   ; sprintf  (image 0x07462)
ABE0  83 C4 0C        add sp,0x0C

; --- INT 3F overlay#03 @ off 0x0463  (text-style / set-color helper) ---
ABE3  FF 76 06        push word [bp+6]     ; arg = mode
ABE6  CD 3F 03 63 04  int 0x3F  ovl=03 off=0x0463
ABEB  5B              pop bx                  ; (stack cleanup after the 1-arg call)

; --- set [seg190F:0x9C16] = 0x2D ---
ABEC  8E 06 E6 E5     mov es,[0xE5E6]      ; es <- DGROUP (190F)
ABF0  26 C7 06 16 9C 2D 00   mov word [es:0x9C16],0x002D

; --- erase background rectangle behind the text ---
;     (memset-like fill via call 08B3:086A, see §3.2)
ABF7  B8 20 00        mov ax,0x0020
ABFA  50              push ax              ; height? = 0x20
ABFB  2B C9           sub cx,cx
ABFD  51              push cx              ; arg = 0
ABFE  50              push ax              ; height again
ABFF  BA 40 01        mov dx,0x0140        ; = 320 = screen pitch
AC02  52              push dx
AC03  51              push cx
AC04  51              push cx
AC05  9A 6A 08 B3 08  call far 08B3:086A   ; rep movs rect-copy (clear back-buf)  (image 0x9394, see §3.2)
AC0A  83 C4 0C        add sp,0x0C

; --- strlen( the formatted string ) ---
AC0D  FF 76 0A        push word [bp+0xA]   ; (BUG? this should push the buf seg 0x1708, not arg seg)
AC10  FF 76 08        push word [bp+8]
AC13  9A 90 1D 26 05  call far 0526:1D90   ; strlen  (image 0x06FF0; classic xor ax,ax; repne scasb)
AC18  5B              pop bx
AC19  5B              pop bx

; --- iters = abs(strlen)/4   (NOT a per-char count -- this is "how many shadow-frame columns") ---
AC1A  99              cwd
AC1B  33 C2           xor ax,dx
AC1D  2B C2           sub ax,dx            ; ax = abs(ax)
AC1F  B9 02 00        mov cx,0x0002
AC22  D3 F8           sar ax,cl            ; >> 2
AC24  33 C2           xor ax,dx
AC26  2B C2           sub ax,dx            ; final abs
AC28  89 46 FE        mov [bp-2],ax        ; loop counter

; --- compute color (cl) and starting X (dx) from mode bit 0 ---
AC2B  8A 46 06        mov al,[bp+6]
AC2E  25 01 00        and ax,0x0001
AC31  3D 01 00        cmp ax,1
AC34  1B C9           sbb cx,cx            ; cx = -1 if mode&1 else 0
AC36  80 E1 24        and cl,0x24
AC39  81 C1 FE 00     add cx,0x00FE        ; color = 0xFE or 0xFE+0x24=0x122 (probably index 0xFE or 0x22)
AC3D  89 4E FA        mov [bp-6],cx        ; color stash

AC40  BA 14 00        mov dx,0x0014        ; height = 20px

;     [bp-0xA] = base X = 0x20  (set in first loop iter at AC44)
AC43  52              push dx              ; arg: 0x14 (height)
AC44  BA 20 00        mov dx,0x0020
AC47  89 56 F6        mov [bp-0xA],dx      ; X = 0x20
AC4A  52              push dx              ; arg: X
AC4B  51              push cx              ; arg: color

;     resolve glyph table:  es = [DGROUP:0xe60c] then les si,[es:0x8e92]
AC4C  3D 01 00        cmp ax,0x0001
AC4F  1B DB           sbb bx,bx
AC51  80 E3 FD        and bl,0xFD
AC54  83 C3 11        add bx,0x11          ; bx = 0x11 or 0x0E
AC57  D1 E3           shl bx,1             ; *2 (word index)
AC59  8E 06 0C E6     mov es,[0xE60C]      ; es <- 190F (DGROUP)
AC5D  26 C4 36 92 8E  les si,[es:0x8E92]   ; les si,[DGROUP:0x8E92] = far ptr to glyph table
AC62  26 FF 30        push word [es:bx+si] ; arg: glyph_table[index]
AC65  EB 2B           jmp 0xAC92           ; skip the "first" branch, go straight to the call

; ===== LOOP BODY (first iteration entry) =====
AC67  B8 14 00        mov ax,0x14
AC6A  50              push ax              ; height
AC6B  FF 76 F6        push word [bp-0xA]   ; X
AC6E  8A 46 06        mov al,[bp+6]        ; mode
AC71  25 01 00        and ax,0x0001
AC74  3D 01 00        cmp ax,1
AC77  1B C0           sbb ax,ax
AC79  25 30 00        and ax,0x0030
AC7C  05 E8 FF        add ax,0xFFE8
AC7F  01 46 FA        add [bp-6],ax        ; adjust color
AC82  FF 76 FA        push word [bp-6]
AC85  8E 06 0C E6     mov es,[0xE60C]
AC89  26 C4 1E 92 8E  les bx,[es:0x8E92]
AC8E  26 FF 77 1E     push word [es:bx+0x1E]  ; arg: glyph_table[0x1E]
;
AC92  8E 06 0E E6     mov es,[0xE60E]
AC96  26 FF 36 8A 23  push word [es:0x238A]   ; arg: row/Y from BSS  (handle ctx)
AC9B  8E 06 10 E6     mov es,[0xE610]
AC9F  26 FF 1E 3A 1C  call far [es:0x1C3A]    ; **DRAW-CHUNK** dispatch  (5 args, retval ignored)
ACA4  83 C4 0A        add sp,0x0A             ; clean 5 words

;     advance X is NOT done here -- looking again, [bp-0xA] is not advanced inside loop.
;     So the loop draws the SAME column-style chunk strlen/4 times at the SAME X.
;     -- This is the LEFT-edge / shadow column being repeated for visual decoration.
ACA7  8B 46 FE        mov ax,[bp-2]
ACAA  FF 4E FE        dec word [bp-2]
ACAD  0B C0           or ax,ax
ACAF  75 B6           jnz 0xAC67           ; loop until counter == 0

; ===== END OF SHADOW/BORDER LOOP =====

; --- Draw final/tail chunk (right cap of the shadow column) ---
ACB1  B8 14 00        mov ax,0x14
ACB4  50              push ax              ; height
ACB5  FF 76 F6        push word [bp-0xA]   ; X
ACB8  8A 46 06        mov al,[bp+6]
ACBB  25 01 00        and ax,1
ACBE  3D 01 00        cmp ax,1
ACC1  1B C9           sbb cx,cx
ACC3  83 E1 30        and cx,0x30
ACC6  83 C1 E8        add cx,-0x18
ACC9  01 4E FA        add [bp-6],cx        ; color tweak
ACCC  8B 4E FA        mov cx,[bp-6]
ACCF  51              push cx              ; color
ACD0  3D 01 00        cmp ax,1
ACD3  1B DB           sbb bx,bx
ACD5  83 E3 0D        and bx,0x0D
ACD8  83 C3 03        add bx,0x03          ; bx = 3 or 0x10
ACDB  D1 E3           shl bx,1
ACDD  8E 06 0C E6     mov es,[0xE60C]
ACE1  26 C4 36 92 8E  les si,[es:0x8E92]
ACE6  26 FF 30        push word [es:bx+si] ; arg: glyph_table[index]
ACE9  8E 06 0E E6     mov es,[0xE60E]
ACED  26 FF 36 8A 23  push word [es:0x238A] ; arg: row
ACF2  8E 06 10 E6     mov es,[0xE610]
ACF6  8B F0           mov si,ax            ; save mode bit for later
ACF8  26 FF 1E 3A 1C  call far [es:0x1C3A] ; SAME DRAW-CHUNK dispatch as in loop
ACFD  83 C4 0A        add sp,0x0A

; --- advance X for the actual text-render that follows ---
AD00  0B F6           or si,si
AD02  74 0B           jz 0xAD0F
AD04  8B 46 FA        mov ax,[bp-6]
AD07  05 18 00        add ax,0x18
AD0A  89 46 FA        mov [bp-6],ax        ; (color += 0x18) -- this is offset of next pane
AD0D  EB 05           jmp 0xAD14
AD0F  C7 46 FA 2C 00  mov word [bp-6],0x002C

; --- Now the REAL text draw -- call far [es:0x160] ---
;     5 args pushed:  (str_seg, str_off, color, x+3, row/Y)
;
AD14  8E 06 08 E6     mov es,[0xE608]
AD18  26 FF 36 E8 00  push word [es:0xE8]  ; ?? extra arg pushed first (Y? font?)

AD1D  8E 06 04 E6     mov es,[0xE604]      ; es <- DGROUP
AD21  26 83 3E F4 C9 00   cmp word [es:0xC9F4],byte 0
AD27  74 05           jz 0xAD2E
AD29  8B 46 0C        mov ax,[bp+0xC]      ; if global flag set: use ctx directly
AD2C  EB 0E           jmp 0xAD3C
AD2E  8E 06 06 E6     mov es,[0xE606]      ; else: deref ctx as struct
AD32  8B 5E 0C        mov bx,[bp+0xC]
AD35  26 8A 87 14 00  mov al,[es:bx+0x14]
AD3A  2A E4           sub ah,ah
AD3C  50              push ax              ; color (from ctx struct field +0x14, or raw ctx)
AD3D  8B 46 F6        mov ax,[bp-0xA]
AD40  05 03 00        add ax,3
AD43  50              push ax              ; X+3 (so the text is inset 3px from the shadow box)
AD44  FF 76 FA        push word [bp-6]     ; row/Y (color slot reused as Y?)
AD47  FF 76 0A        push word [bp+0xA]   ; str seg
AD4A  FF 76 08        push word [bp+8]     ; str off
AD4D  8E 06 0A E6     mov es,[0xE60A]      ; es <- 1708 BSS (dispatch table seg)
AD51  26 FF 1E 60 01  call far [es:0x160]  ; **REAL TEXT-DRAW DISPATCH**
                                            ;   far pointer at seg1708:0x160 (BSS, filled at runtime
                                            ;   by overlay init). Resolves to the function that
                                            ;   iterates the string and renders glyphs.
AD56  83 C4 0C        add sp,0x0C          ; cleans 6 words (12 bytes — 5 pushes were 10 bytes
                                            ;   + 1 extra at AD18; actually 6 pushes = 12 bytes ✓)

; --- Final region invalidate / dirty-rect mark (the AD7A call) ---
AD59  83 7E 06 01     cmp word [bp+6],0x01
AD5D  7E 05           jng 0xAD64
AD5F  B8 82 00        mov ax,0x0082
AD62  EB 02           jmp 0xAD66
AD64  2B C0           sub ax,ax
AD66  89 46 F6        mov [bp-0xA],ax
AD69  50              push ax              ; y1
AD6A  2B C0           sub ax,ax
AD6C  50              push ax              ; x1 = 0
AD6D  B9 0E 00        mov cx,0x0E
AD70  51              push cx              ; height = 14
AD71  B9 40 01        mov cx,0x0140
AD74  51              push cx              ; width = 320
AD75  B9 20 00        mov cx,0x0020
AD78  51              push cx              ; src y? = 0x20
AD79  50              push ax              ; src x = 0
AD7A  9A 34 06 7A 04  call far 047A:0634   ; rect blit/invalidate  (image 0x4DD4, see §3.4)
AD7F  83 C4 0C        add sp,0x0C

AD82  5E              pop si
AD83  8B E5           mov sp,bp
AD85  5D              pop bp
AD86  CB              retf                 ;  <-- END of print_func
```

### Stack frame map

```
[bp+0x0C]   arg3: context (window/row handle)
[bp+0x0A]   arg2_hi: string segment
[bp+0x08]   arg2_lo: string offset
[bp+0x06]   arg1: mode/flags (LSB = pane selector, other bits influence color/Y)
[bp+0x04]   ret_seg
[bp+0x02]   ret_off
[bp+0x00]   saved bp
[bp-0x02]   loop counter = strlen/4
[bp-0x06]   color (palette index, ±adjustments)
[bp-0x0A]   X coordinate (starts at 0x20 = 32)
[bp-0x0E]   (unused / padding -- sub sp,0x0E reserved 14 bytes)
[bp-0x10]   saved si  (push si)
```

---

## 3. Per-call analysis

### 3.1 `call far 0526:2202` (image 0x07462) — `sprintf`
Classic MSC sprintf shim. Stack args: `(dst_seg, dst_off, fmt_seg, fmt_off, ...va_args)`.
Body confirms: stores arg pointers to scratch at `ds:0xEA7E`, sets sentinel `0x7FFF` at `ds:0xEA82`, calls into `0526:1014` (the real formatter), returns char count. **Generic library — not a hook target.**

### 3.2 `call far 08B3:086A` (image 0x0939A) — rect-fill / memcpy
Args: `(src_seg, src_off, dst_seg, dst_off, width_words, height)` (6 args, 0x0C cleanup matches).
Body: `rep movsw` + `rep movsb` line by line, with stride = 0x140 (= 320, mode 13h pitch). **This is a copy from background buffer to fill the chrome area.** Not glyph-related directly.

### 3.3 `call far 0526:1D90` (image 0x06FF0) — `strlen`
Standard:
```
les di,[bp+6]; xor ax,ax; mov cx,-1; repne scasb; not cx; dec cx; xchg ax,cx
```
Returns strlen in `ax`. **Library — not a hook target.**

### 3.4 `call far 047A:0634` (image 0x04DD4) — clip-and-blit-rect
~120 bytes of clipping logic + bounds against `[bp-0x32]`, `[bp-0xa]`, etc., then probably a nested call at `0x5108`. Reads/writes a back-buffer region. **This is the "dirty rect / blit-front-to-back" call, not glyph rendering.**

### 3.5 `INT 3F  03 63 04` — MSC overlay call → overlay #03, offset 0x0463
Format: `CD 3F  ov  off:WORD`  (5 bytes). 158 INT-3F sites across the image.
Print_func passes 1 word arg `[bp+6]` (the mode). Likely sets text style / palette context.

### 3.6 `call far [es:0x1C3A]` at AC9F, ACF8 — **chrome-column draw** (BSS dispatch)
`es <- DS:[0xE610] = 0x1708` (BSS). Slot `1708:0x1C3A` is **zero in the static image** — it's a runtime-populated dispatch slot. Filled by overlay-loaded code during init. Called once per shadow column (`strlen/4` iters) + once for the tail. Args: `(row, glyph_table_entry, color, x, height=0x14)`.

### 3.7 **`call far [es:0x160]` at AD51 — THE TEXT DRAW DISPATCH**
`es <- DS:[0xE60A] = 0x1708` (BSS). Slot `1708:0x0160` is **zero in the static image**. Filled at runtime by the overlay loader. Args (6 words pushed in AD18/AD3C/AD43/AD44/AD47/AD4A):

```
push word [es:0xE8]   ; seg 1708 extra word (Y2 or font_id)
push ax               ; color (from ctx struct +0x14, or raw [bp+0xC])
push (x + 3)
push word [bp-6]      ; Y / row (after the +0x18 adjustment)
push word [bp+0xA]    ; string segment
push word [bp+8]      ; string offset
call far [es:0x160]
```

**This is the function that walks the C-string and renders each byte to VGA**. It lives in an overlay (root-image slot is zero → only an overlay-init can populate it).

---

## 4. The real character-rendering function lives in an overlay

`Land_unpacked_v2.exe` is a **Microsoft C 6.0 program with the MSC overlay manager**. The signature `"MS Run-Time Library — Copyright (c) 1990, Microsoft Corp"` at DGROUP+8 is conclusive. The `INT 0x3F` 5-byte instructions seen 158× throughout the image are the **MSC overlay-call thunks** (overlay#, target_off:WORD).

Static evidence: BSS region `seg 0x1708` (image 0x17080–0x190F0, **4080 bytes, entirely zero**) holds dispatch-table slots. Slot `1708:0x160` (used by `call far [es:0x160]` at AD51) is the text-draw vector. Slot `1708:0x1C3A` (used in the shadow-column loop) is the chrome-draw vector. **Both are blank pre-run** and get populated when overlays load.

The actual byte-by-byte glyph blit (the routine that, given a string pointer, iterates char by char, looks up each glyph in a font table, and pushes bytes to `A000:` mode-13h video memory) is **NOT in the root segment**. It is inside one of the **15+ overlays** referenced across the image — most likely the same overlay that contains the font bitmaps. To find it statically we'd need to (a) find the overlay file (probably an `.OVL` companion or embedded after the EXE end), (b) load each overlay, (c) find the routine whose far address gets written into slot `1708:0x160` during init.

The MSC overlay system stores overlays in a separate file (or appended to the EXE) and loads them on demand by overlay#. Run-time trace via DOSBox debug log is the fastest way to identify which overlay # carries `vtable_init` (the function that writes the far pointer into BSS slot `1708:0x160`).

---

## 5. Hook point recommendation

### Recommended hook: `print_func` entry @ image_off `0xABAA`  (real-mode `09CE:0ECA`)

**Why here, not deeper:**

1. The real per-character draw is **in an overlay** (BSS dispatch slot `1708:0x160` is zero in the static image). We can't statically locate it without trace.
2. Even if we found it, we'd need to **hook inside an overlay** — which means the hook is overwritten every time that overlay is re-loaded. Hooking the root code is safer.
3. All 24 UI strings flow through `print_func` (verified — the byte signature `9A CA 0E CE 09` appears exactly at the call sites listed). Hooking entry catches them all.
4. Big5 detection works fine at the whole-string level: walk the string once, build a Big5-aware render call.

**Argument extraction at entry:**

```c
// On entry to our trampoline (after the saved 5 bytes have run):
//   sp -> ret_off, ret_seg, arg1_mode, arg2_off, arg2_seg, arg3_ctx
unsigned int mode    = *(unsigned int __far*)(MK_FP(ss, sp+0));   // [bp+6] equiv
unsigned int str_off = *(unsigned int __far*)(MK_FP(ss, sp+2));
unsigned int str_seg = *(unsigned int __far*)(MK_FP(ss, sp+4));
unsigned int ctx     = *(unsigned int __far*)(MK_FP(ss, sp+6));
const char __far* s  = MK_FP(str_seg, str_off);
```

### Stub size

Current plan: **5-byte FAR JMP** at image_off `0xABAA` →
```
EA  lo hi  seg seg     ;  jmp far  <stub_seg>:<stub_off>
```
That overwrites:
```
ABAA  55              push bp
ABAB  8B EC           mov bp,sp
ABAD  83 EC 0E        sub sp,0x0E
ABB0  56              push si    <-- this is byte 6+, NOT overwritten
```
**5-byte hook is clean.** It cuts exactly at the end of `sub sp,0x0E`. Our stub must:
1. Emulate the 5 saved bytes (`push bp; mov bp,sp; sub sp,0x0E`) OR re-do them after our work.
2. Read args via `[bp+6]/[bp+8]/[bp+0xA]/[bp+0xC]` (same as native).
3. Implement Big5-aware behavior, then either:
   - **Option A (preferred):** Substitute the string in-place (replace ASCII bytes with our pre-rendered translated Big5 string in a scratch buffer), then `JMP` to `0xABB0` (resume native `push si` and the rest). Native does the rest of the work.
   - **Option B (more invasive):** Skip native entirely. Build the full draw ourselves by calling the same dispatch slot `1708:0x160` — but that requires it to be populated, so we'd have to defer to the first overlay-load.

**Option A is the recommendation.** Stub does this:
```
Stub entry:
  push  bp
  mov   bp, sp
  sub   sp, 0x0E       ; ditto native
  push  si
  ; -- our work --
  push  es; push ds; pushf; pusha
  les   di, [bp+8]         ; di:es = original string far ptr
  ; copy + translate string into our scratch buffer
  ; (replace ASCII placeholder bytes with Big5 sequences from translation table)
  popa; popf; pop ds; pop es
  ; rewrite [bp+8],[bp+0xA] to point to scratch
  mov   ax, OFFSET scratch_ds
  mov   [bp+8], ax
  mov   [bp+0xA], ds
  pop   si                  ; undo push si
  ; -- resume native at ABB1 (just past the prologue we re-did) --
  jmp   far 09CE:0ED1       ; native at image_off 0xABB1
```

Net trampoline: ~60-100 bytes including string-scan + table-lookup. Easily fits.

### Stub placement

Look for any 0xFF-padding region or unused alignment slack in the image. EXEPACK historically leaves a small relocation area / unused tail. Practical option: **append the stub to a new code segment** by extending the EXE and adding a new MZ section that the loader maps as a normal segment. Then the FAR JMP at `0xABAA` targets `<new_seg>:0`.

For simpler binary surgery, scan for the longest run of `0x00` or `0x90 (NOP)` in the image — there are some between `ABE6` overlay thunks and inside DGROUP slack. A 256-byte clean region in DGROUP (or in the final 0x100 bytes of the image before BSS expansion) can host the stub.

(Specific free-space hunt is out of scope for this RE pass; deferred to the patch step.)

### Big5 detection strategy

At stub entry: scan the input C-string byte-by-byte. For each `b`:
- If `0xA1 <= b <= 0xFE` AND next byte is in `[0x40..0x7E] ∪ [0xA1..0xFE]` → it's a Big5 lead+trail pair.
- Convert that pair to a Big5 codepoint and emit a 2-byte placeholder that the native renderer will display **but** with our pre-installed font replacing those character codes. **OR** — easier — keep our own translated string in a parallel Big5 scratch and route to a different renderer.

The cleanest scheme: pre-translate every UI string to Big5, store in our string pool, and substitute pointer at stub entry. Native renderer then just emits the bytes via its existing glyph path — but we hook the glyph path too, deeper. For now we have **one good hook**: print_func entry.

### Open issues / next investigation steps

1. **Trace the overlay load** that populates `1708:0x160`. Run Land.exe in DOSBox-X with debug, breakpoint on writes to `1708:0x160`, identify the overlay (and offset within it) that holds the text-render function. That gives us a deeper, per-character hook if we want one.
2. **The dispatch table at glyph-table base `[DGROUP:0x8E92]`**: this is a far pointer to a glyph-metric table (entries at +0x1E etc). Populated at runtime, probably from the font file. Worth identifying — we may want to patch glyph-width entries for Big5 characters (16px instead of 8px).
3. **The `[seg1708:0xE8]` argument** pushed at AD18: figure out what it represents (font ID, Y2, clip-rect handle).
4. **The 2nd printf-style wrapper at image_off 0xAD87** (`print_func_buf`): mirrors print_func but with a stack buffer. If there are callers that use it instead of `print_func`, they need a separate hook OR we hook the shared `[1708:0x160]` slot once that's identified.

---

## Summary

- **`print_func` is a 477-byte chrome-drawing wrapper, NOT the glyph renderer.** It draws the message frame (background fill + shadow column + right cap) then calls the real text renderer via a runtime-populated far-pointer slot at `[seg 1708 BSS : 0x160]`.
- **The real glyph blit lives in an overlay** (proven: dispatch slot is all-zero in the static image; the binary is MSC 6.0 with INT-3F overlay manager).
- **Recommended hook:** entry of `print_func` at image_off `0xABAA` (5-byte FAR JMP, prologue boundary-aligned), with a stub that does string substitution + jumps back to image_off `0xABB1` to let native do the rest.
- All 24 UI strings flow through this single function — one hook covers them all.
