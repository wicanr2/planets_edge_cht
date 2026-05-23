# Planet's Edge 繁體中文化專案 (pe-cht)

> 1992 年 New World Computing 發行的 sci-fi RPG 《Planet's Edge — The Point of No Return》
> （中文名《天際寒星》）繁體中文化專案。

## 專案目標

讓繁體中文玩家用熟悉的母語玩到這款 1992 年的太空 CRPG。

## 路線

**SDL2 native port** — C++17 重寫，Linux + macOS + Win 原生執行，**不需 DOSBox**。

| 階段 | 狀態 |
|---|---|
| 1-hour 可行性 spike | ✅ 通過（NWC logo + 中文字幕 demo + Win .exe 都驗證） |
| 翻譯 TSV (1191 條) | 🔄 進行中（多 agent 平行翻譯） |
| 8-week 全 port roadmap | 📋 spec 在 `docs/SPIKE_REPORT.md` |
| Week 1 SceneManager / ResourceLoader | ⏳ 翻譯完即開始 |

> **歷史路線（已凍結）**：早期探索過 binary patch packed Land.exe 路線，
> RE notes 留在 `docs/print_func_re.md` / `docs/wireframe_hook_notes.md` 供參考，
> 但已決定不繼續維護。SDL2 port 是唯一目標。

## Repo 結構

```
pe-cht/
├── translations/        ← 中文化主體（en + zh 對照 TSV）
│   ├── bch/             ← .bch 資源檔字串（532 條）
│   ├── exe/             ← Pe/Land/Space.EXE UI 字串（659 條）
│   └── glossary.md      ← 統一譯名表 + style guide
├── tools/               ← Python pipeline 工具（建 .bch / lookup table）
├── docs/                ← RE 筆記 / spec / 設計文件
│   ├── font_layout_spec.md
│   ├── wrapper_loader_plan.md
│   ├── print_func_re.md
│   └── wireframe_hook_notes.md
└── sdl2_engine/         ← C++17 + SDL2 native engine（路線 B，spike done）
```

> **不包含遊戲資料** — 你必須有正版 Planet's Edge 才能用。詳見 [IP / 法律](#ip--法律)。

## 字型 / 排版規格

- **字型**: 12×12 Big5 點陣黑體
- **譯文硬規定**: 中文 Big5 bytes ≤ 原 ASCII strlen（不擴 box 寬度）
- 全局統一一種字型，不分 pane
- 詳見 `docs/font_layout_spec.md`

## 翻譯統計

| 來源 | 條目 | 翻譯進度 |
|---|---|---|
| `Land.exe` UI | 212 | 進行中 |
| `Pe.exe` UI | 54 | 進行中 |
| `Space.EXE` UI | 393 | 進行中 |
| `1.bch` 章節 | 33 | 進行中 |
| `2.bch` 事件 | 24 | 進行中 |
| `Objects.bch` 物品 | 252 | 進行中 |
| `Spacet.bch` 行星掃描 | 223 | 進行中 |
| **合計** | **1191** | — |

## 技術摘要

- **EXEPACK** 壓縮三 EXE 已解；MSC C 6.0 + INT 3F overlay manager
- **.cc archive** = LZW 9-12 bit (Unix compress 風格)，**不是 LZHUF** — Python + C++ 解碼器都已驗證 fail=0
- **.bch** 格式 `[256 × u16 offset table][256 × (u16 strlen + text)]`
- **Land.exe `print_func`** @ image 0xABAA = real-mode 09CE:0ECA，24 個 UI callsite 共用
- 詳見 `docs/`

## IP / 法律

- 遊戲 binary (Pe.exe / Land.exe / Space.EXE / *.cc / *.bch) 屬 NWC → 3DO，本 repo **絕不包含**
- 譯文 (zh) 為譯者原創，授權 **CC BY-SA 4.0**
- 工具 (tools/ / sdl2_engine/) 授權 **MIT**
- 文件 (docs/) 授權 **CC BY 4.0**
- 詳見 `LICENSE`

## 使用方式（玩家視角）

**🚧 尚未發布。Spike + 翻譯仍在進行**

未來會提供：
- 路線 A: `pe-cht-dosbox-portable.exe` (DaumDOSBox + patched 三 EXE 一鍵跑)
- 路線 B: `pe-cht-native.exe` (Win) / `pe-cht-native` (Linux ELF) 原生執行

兩種都要求玩家自備正版遊戲資料夾。

## Related skills / memory

- `mm3-cc-archive` — 比 PE 簡單一階的 cc archive 格式參考
- `eob1-cht` — 1991 同期 DOS 16-bit 字串 hex patch 套路
- `mm3-cht-font` — 16×15 Big5 字型 hex patch 套路
- `dosbox-portable-sfx` — DaumDOSBox + 遊戲整包單檔技術
