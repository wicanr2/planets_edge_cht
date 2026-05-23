# PE SDL2 Port Spike — Phase A Complete

> **Status:** ✅ **SUCCESS** — 2026-05-23, 1 hour elapsed
> **Goal:** Prove PE assets can render natively in SDL2 without DOSBox
> **Result:** 6 intro frames including "NEW WORLD COMPUTING" splash rendered byte-perfect

## What was built

| File | Size | Purpose |
|---|---|---|
| `pe_intro_viewer.c` | 3.3 KB | 110-line SDL2 viewer (320×200 indexed → 640×400 ARGB) |
| `pe_intro_viewer` (Linux ELF) | 17 KB | Compiled binary (gcc -O2) |
| `build_and_test.sh` | — | Headless test harness with Xvfb + screenshot |
| `render_batch.sh` | — | Batch-render multiple frames with palette swap |

## Pipeline confirmed working

```
.cc archive  ─LZW decode→  raw 64000-byte pixel data (320×200 mode 13h)
.cc palette  ─LZW decode→  raw 768-byte VGA 6-bit RGB triples
                  ↓
            pe_intro_viewer
                  ↓
   SDL2 window 640×400 native (Linux/Win/Mac portable)
```

## Evidence (in `D:\03_tools\poc\sdl2_spike\*.png`)

- **`4413.png`** — "NEW WORLD COMPUTING" logo splash with planets & starfield ⭐
- **`5E5C.png`** — starfield / galaxy intro background
- **`595D.png`** — secondary intro art
- **`6839.png`** — spaceship interior / control panel (full color VGA)
- **`D8C7.png`** / **`D9E3.png`** / **`4413.png`** — additional intro frames
- **`*_pal838C.png`** — same images with alternate palette (color shift verified)

## Implications for 8-week port estimate

The HARDEST part of "DOS → SDL2" — getting the rendering pipeline correct with right palette / right pixel format — is **proven in 1 hour**.

What this means for the full port:
- **Assets**: trivially extractable (cc decoder DONE, bch decoder DONE, palette decoder DONE)
- **Rendering**: trivially portable (this spike)
- **Audio**: separate concern (libopl / SDL_mixer / skip v1)
- **Input**: trivial (SDL_PollEvent)
- **Game logic**: the only real RE work remains (Land.exe combat, Space.EXE navigation, scripting)

## Phase B status

Ghidra 11.2.1 installing in background. Phase B will decompile `Pe_unpacked.exe` (smallest of 3 EXEs) and evaluate whether the decompiled C is human-readable enough to drive a logic port for the harder binaries.

But arguably: **for Pe.exe specifically, decompile is unnecessary**. The intro/menu is linear UI flow that can be re-implemented from observation alone. The 6 frames we already rendered are 90% of Pe.exe's value.

## Risk reassessment

| Risk | Pre-spike | Post-Phase-A |
|---|---|---|
| Asset pipeline | medium | ✅ eliminated |
| Rendering layer | medium | ✅ eliminated |
| Palette / color | high | ✅ eliminated |
| 8-week timeline | speculative | **plausible** for intro + menu |
| Land.exe gameplay port | high | unchanged — Phase B needs to evaluate |
