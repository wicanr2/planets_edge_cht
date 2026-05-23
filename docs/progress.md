# 進度紀錄

## 2026-05-23 (session 1+2+3+4)

### ✅ Toolchain (已可用)

- WSL Ubuntu 22.04 + gcc-ia16 6.3.0 + NASM 2.15.05
- WSL headless DOSBox + Xvfb + 自動截圖：`D:\03_tools\notes\dosbox_runner.sh`
- `Land.exe` 結構：file 141345 = MZ header 512 + image 91983 (EXEPACK) + **overlay 49362** (MSC sub-EXE chain)
- 對 Land.exe 來說：23 個 UI 字串 (`'Tele-trans activated.'` 等) 全 call far `09CE:0ECA` (file_offset 0xABCA in v1 unpacked)

### ⚠️ Hook PoC blocker

EXEPACK 解壓做完了 (1129 reloc 還原) + hook stub (25 bytes NASM, 印 'H' + 跳回) + patch 注入 — **但啟動失敗印「Overlay not found」**：

- MSC overlay manager 用未知公式算 overlay area file_offset，**不是** MZ header e_cp/e_cblp
- 沒找到 91983 / 0x1674F / 各種衍生 magic 在 image 任何 byte
- 0x1675 那 6 個 hits 全是 `jnz +0x16` 指令巧合

→ **下次主攻：wrapper loader (INT 21h AH=4B01h load child + memory patch)，不動原 Land.exe**

### ✅ 字串 inventory

- Land.exe 內 EXE strings: 345 個 candidate (≥6 chars + 含空格)
- Pe.exe: 84 個
- Space.EXE: 527 個
- 4 個 `.bch`: each 256 entries fixed (offset table + variable-length strings, `\r` 為換行)

## 下次起點

```
cd D:\03_game\plant_edge_cht\
# 翻譯：編輯 translations/**/*.tsv
# build (todo): tools/build.ps1
# verify (todo): wsl dosbox auto-screenshot
```

要繼續 hook 路徑 → attack wrapper loader (見 `project_pe_cht.md` "BLOCKER" section)。
