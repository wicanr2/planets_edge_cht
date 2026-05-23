# Planet's Edge 繁體中文化專案

> 1992 NWC DOS RPG, EXEPACK 壓縮 + MSC C 5.x overlay + 320×200 VGA 自繪字型。

## 目錄結構

```
plant_edge_cht\
├── original\          # 原版 game 唯讀 ref (37 個檔, RO 屬性)
├── work\PE\           # 工作 sandbox (要被改的 copy)
├── translations\      # 翻譯 source of truth
│   ├── bch\
│   │   ├── 1_extracted.tsv          # 章節對話/事件文字
│   │   ├── 2_extracted.tsv          # 新聞稿/廣播
│   │   ├── Objects_extracted.tsv    # 物品描述
│   │   └── Spacet_extracted.tsv     # 行星掃描報告
│   ├── exe\
│   │   ├── land_strings.tsv         # 23 UI + 動作回應 (Land.exe)
│   │   ├── space_strings.tsv        # 戰鬥/裝備 (Space.EXE)
│   │   └── pe_strings.tsv           # intro/credits (Pe.exe)
│   └── glossary.md                  # 統一譯名表
├── builds\            # 各輪 patched 產物 (時間戳)
├── tools\             # 工具 shortcut → D:\03_tools\poc\land_re\
└── docs\
    ├── README.md      # 本檔
    ├── progress.md    # cross-session 進度紀錄
    └── NOTES.md       # 短期觀察筆記
```

## 翻譯流程

1. **翻譯** — 編輯 `translations/<area>/*.tsv` 的「translation_zh」欄
2. **build** — 跑 `tools\build.ps1`（之後寫）把 TSV 注入 work/PE/ 並輸出到 builds/
3. **驗證** — WSL DOSBox 自動截圖（用 `D:\03_tools\notes\dosbox_runner.sh`）

## TSV 格式

每個 `*_extracted.tsv` 欄位：

| col | 內容 |
|---|---|
| `idx` | entry index (.bch) 或 file_offset (EXE) |
| `len_en` | 原文長度（byte） |
| `original_en` | 原英文 (`\r` 顯示為 `\\r`，方便 column 排版) |
| `translation_zh` | **你要填的中文** (留空 = 不翻) |
| `notes` | 譯註/雷區提醒 |

## 已知雷區

- **EXE 字串長度限制**：in-place patch 不能超過原 slot 長度。短於原 slot 後面補 `\0`。詳見 `progress.md` 的 hook 路線狀況
- **DOSBox 預設不認 Big5**：純改字串內容後在 dosbox 看是亂碼，要 hook + 16×16 blit 才能顯示真中文。目前 hook 路線 blocked by EXEPACK+overlay (見 `progress.md`)
- **`\r` 是 .bch 內換行符**：不要動原字串裡的 `\r` 數量，會影響 dialogue 排版

## 跨 session 接續點

下次直接「繼續 Planet's Edge 中文化」、AI 會 load `project_pe_cht.md` 知道全脈絡。
