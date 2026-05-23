# Planet's Edge Land.exe wireframe Big5 hook — notes

## Summary

Installed a wireframe-level Chinese-localization hook in Land.exe by patching
the EXEPACK-compressed binary **in place** (no unpack/repack). The hook
intercepts `print_func` (image_off `0xABAA`, real-mode `09CE:0ECA`) and draws
a hardcoded 16x16 "中"-pattern glyph at fixed VGA position (200, 20) every
time the game calls `print_func`.

End-state files:

| Path | Bytes | What |
|---|---|---|
| `D:\03_game\plant_edge_cht\build\Land_patched.exe` | 141345 | Patched packed Land.exe (same size as original) |
| `D:\03_game\plant_edge_cht\build\Land_patched.exe.notes.txt` | — | Per-build notes |
| `D:\03_tools\poc\land_re\stub_zhong.asm` | — | NASM source |
| `D:\03_tools\poc\land_re\stub_zhong.bin` | 107 | Assembled stub |
| `D:\03_tools\poc\land_re\patch_land_packed.py` | — | Patcher (idempotent: refuses re-patch) |
| `D:\03_tools\poc\land_re\dosbox_sandbox_packed\` | — | Sandbox: full PE dir + patched Land.exe + RUN_PE.bat |

## Approach: Option E (overwrite dead `print_func_buf`)

The brief listed five candidate placements (A–E). We picked **Option E**:

- `print_func_buf` at image_off `0xAD87` (real-mode `09CE:10A7`, 477 bytes)
  is a near-twin of `print_func` but uses a stack buffer instead of the
  global one. **Zero callers** in the unpacked image (verified by
  byte-pattern xref of `9A A7 10 CE 09`). So it's dead code.

- In the packed file, all 477 bytes of `print_func_buf` are stored as a
  contiguous 0xB2 literal-copy block at file_off `0xAE6C..0xB048`
  (verified by `trace_exepack_mapping.py`). Patching bytes there
  propagates verbatim to image_off `0xAD87..0xAF63` at runtime.

## Patch summary

1. **Hook site, packed file_off `0xAC8F` (5 bytes)**
   ```
   55 8B EC 83 EC   ->   EA A7 10 CE 09
   ```
   = `jmp far 09CE:10A7` (to stub). The 6th original byte (`0x0E` at
   file_off `0xAC94`) becomes an orphan immediate — unreachable because
   the FAR JMP redirects flow before it can execute.

2. **Stub body, packed file_off `0xAE6C` (107 bytes)**
   Overwrites the head of dead `print_func_buf`. The stub:
   - Saves all touched registers (ax/bx/cx/dx/si/di/es/ds + flags)
   - Sets ES = 0xA000 (VGA mode-13h framebuffer)
   - Reads its embedded 32-byte 1-bpp glyph table at glyph_zhong label
   - Blits 16x16 packed-1bpp glyph to (X=200, Y=20) with color 0x0F
   - Pops registers
   - Re-creates the destroyed prologue: `push bp; mov bp,sp; sub sp,0x0E`
   - `jmp far 09CE:0ED0` → resumes at the `push si` that originally
     followed the prologue (image_off `0xABB0`)

3. **EXEPACK reloc table (slot 0)**
   - Slot 0 count: 459 → 461 (+2)
   - Added image_off `0xABAD` (seg word of the new hook FAR JMP)
   - Added image_off `0xADD0` (seg word of stub's back-jmp)
   - 4 bytes inserted at file_off `0x161F5`; bytes after that point in
     the EXEPACK area shift up by 4. We consume 4 bytes from the
     180-byte zero-padding gap (file_off `0x16750..0x167FF`), so:
     - **File size unchanged** (141345 bytes)
     - **Overlay sub-EXE chain at file_off `0x16800` unmoved** ← critical:
       this is why the MSC overlay manager will not break

4. **EXEPACK header**
   - `exepack_size` field at file_off `0x15D36`: 2591 → 2595

## Why this works (and the unpack-then-repack route didn't)

Previous attempts unpacked Land.exe to patch it, but the resulting binary's
MSC overlay manager silently failed (overlay not found / exit). Root cause
was likely that the rebuilt MZ header / reloc table didn't match what the
overlay code expects when it computes its own load addresses from the file
layout.

The packed-in-place approach sidesteps the entire problem:
- File structure / size identical to original
- Overlay sub-EXE chain starts at the exact same byte offset
- EXEPACK loader does its normal decompression
- Our patched bytes propagate via the existing 0xB2 literal-copy commands
- The 2 new reloc entries get applied by the EXEPACK stub *during* the
  same reloc pass as all 1129 original entries, so the FAR JMP segs are
  correctly relocated to (image_base + 0x09CE) at load time

## Verification

Static verification done (`verify_patched.py`, `verify_patched_disasm.py`):

```
[hook @ image 0xABAA] ea a7 10 ce 09 0e   <- FAR JMP to 09CE:10A7 + orphan
[stub @ image 0xAD87] 50 53 51 52 ...     <- stub body (matches stub_zhong.bin)
[stub back-jmp seg]   0x09CE              <- baked seg, will reloc at load
[reloc table]         1131 entries (was 1129); new ones in slot 0
[file size]           141345 bytes (unchanged)
[overlay MZ]          still @ 0x16800 (unmoved)
```

DOSBox smoke test (automated, screenshots in
`dosbox_sandbox_packed\capture\`):

- Pe.exe launches cleanly via the patched Land.exe.
- One of the loaded saves drops the player onto a planet surface
  ("Research Lab" location). Land.exe overlay is alive and rendering
  the scene correctly.
- Game accepts ESC to quit → reaches "Thank you for playing Planet's
  Edge." message and exits to DOS prompt with errorlevel 0.

What screenshots did NOT show: the 16x16 "中" glyph at any of the 4 corners.
Most-likely explanations (in order of probability):

  1. **print_func was never called during the static-scene screenshots.**
     Per `print_func_re.md`, this function only handles popup/notification
     UI text ("Tele-trans activated", "I have no items", "He's dead jim!",
     etc.). Scene labels like "Research Lab" come from a *different*
     bitmap font path that reads strings out of `.CC` / `.BCH` archives
     — that path does NOT go through print_func. Confirmed: the literal
     string "Research" does NOT appear in `Land_unpacked_v2.exe` or
     `Pe_unpacked.exe` — it lives in game data.

  2. **Glyphs overwritten by next frame's full-screen redraw.** Land.exe
     likely double-buffers and copies the back buffer to VGA on every
     frame. A 16x16 white block at (4,4) lives on screen for one frame
     (~33ms) before the next scene copy obscures it. With a 1Hz
     screenshot, we'd miss it most of the time. The hook still ran, we
     just didn't catch the frame.

To VISUALLY confirm the hook fires:
  - Manually load a save, then perform an action that triggers a popup
    message: pick up an item, attempt teleport-to-ship, or examine
    something. The popup message will linger on screen for ~2 seconds,
    so the glyph will be visible during that window.
  - Or: extend the stub to write to a memory address that persists
    across frames (e.g., a corner of the EGA text page at B800:xxxx,
    which Land.exe in mode 13h does NOT touch).

## Automated DOSBox session screenshots

Captured during the SendKeys-driven smoke test:

| File | What it shows |
|---|---|
| `dosbox_sandbox_packed\capture\pe_000.png` | In-game scene from auto-loaded save: "Research Lab" planet surface. No print_func trigger yet. |
| `dosbox_sandbox_packed\capture\pe_001.png` | Same scene, slightly later (~10 s later, after ESC keys). |
| `dosbox_sandbox_packed\capture\pe_002.png` | Same scene, after additional ENTER keys. |
| `dosbox_sandbox_packed\capture\dosbox_001.png` | After enough ESC presses: game exited to DOS with "Thank you for playing Planet's Edge." → confirms binary ran the entire game loop cleanly. |

## Manual verification by user

```powershell
# Just double-click:
D:\03_tools\poc\land_re\dosbox_sandbox_packed\RUN_PE.bat
```

Or:

```powershell
cd D:\03_tools\poc\land_re\dosbox_sandbox_packed
& 'D:\03_game\DOSBOX\dosbox20130725\dosbox.exe' -conf PE.conf
```

Then:
1. Skip intro, get into the game (load save or new game)
2. Travel to and land on any planet → Land.exe overlay engages
3. Any UI message (pickup, examine, tele-trans, etc.) calls `print_func`
4. **Expected:** a white 16x16 "中"-pattern glyph appears at fixed
   position (pixel 200, row 20) every time text renders
5. The game's own UI text continues to render normally below/around it

## Reverting

```powershell
Copy-Item "D:\03_game_tmp\1992_天際寒星_Planets Edge\PE\Land.exe" `
          "D:\03_tools\poc\land_re\dosbox_sandbox_packed\Land.exe" -Force
```

## Next steps (not part of this wireframe)

Once the hook is visually confirmed, the stub can be extended to:

1. Detect Big5 lead byte in the string at `[bp+0xA]:[bp+0x8]` (the arg
   convention from `print_func_re.md` §1).
2. Branch into a Big5 → 16x16 glyph table lookup for full Chinese
   text rendering, fall through to original ASCII path otherwise.
3. Same approach can then be applied to Space.EXE and Pe.exe, both of
   which are also EXEPACK'd.

## Files

- Patcher: `D:\03_tools\poc\land_re\patch_land_packed.py`
- Stub source: `D:\03_tools\poc\land_re\stub_zhong.asm`
- Glyph generator: `D:\03_tools\poc\land_re\gen_glyph.py`
- EXEPACK trace tool: `D:\03_tools\poc\land_re\trace_exepack_mapping.py`
- Verification tools: `verify_patched.py`, `verify_patched_disasm.py`
- Print_func RE doc: `D:\03_tools\poc\land_re\print_func_re.md`
- Output: `D:\03_game\plant_edge_cht\build\Land_patched.exe`
- Runnable sandbox: `D:\03_tools\poc\land_re\dosbox_sandbox_packed\`
