# Planet's Edge 中文化 — Font &amp; Layout 規格

> **Decision date**: 2026-05-23
> **Source**: UX designer Agent analysis (full TSV + glossary + print_func RE 已讀)
> **Status**: locked, 工程師立刻去做

## 1. Font size — **12×12 統一**

- ✅ **選 12×12**：一行 26 中文，匹配「資訊密度感」，sci-fi 多 panel UI 風格
- ❌ 否決 16×16：Land 訊息框 typical 25-30 ASCII 翻完 ~10 中文，留白過多像兒童書
- ❌ 否決 mixed-mode：要 dispatch slot 跟字寬計算雙軌，patch 風險翻倍不值
- 參考：U6 繁中 12×12 已驗證可讀

## 2. Glyph style — **點陣設計黑體**

- 自繪 12×12 黑體 (hand-tuned bitmap, NOT TTF rasterize)
- 理由：
  - VGA 256 色但 print_func 走 shadow-column 只有 2 色實效
  - 明體襯線在 12px 必糊成黑塊
  - unifont 16×16 縮成 12 會掉筆畫
  - 黑體筆畫均一、12px 仍可辨
- **直接 fork U6 那套 Big5 12×12 點陣字庫**
  - 已對過 5400+ 字、已驗證 retro DOS pipeline、IP-safe（自繪過）、省 2 週
  - Repo: https://github.com/wicanr2/u6-cht

## 3. 訊息框溢出 — **翻譯時人工控字數**

- **Hard rule**: 中文 bytes ≤ 原 ASCII strlen
- 不動 box width / shadow loop / dispatch
- 不自動換行（PE intro 已預斷不需要、Land 短訊息也不該換）
- 不截斷（會丟資訊）
- glossary.md 已示範這格式

## 4. Pane 字型 — **統一一種 (12×12 全局)**

- mode bit 0 只影響 Y baseline + color，跟字寬無關
- 分字型 = 兩套 glyph table + 兩個 dispatch slot + 兩套寬度計算
- retro 遊戲一致性 &gt; 緊湊度
- Mixed 留給未來 v1.1 polish

---

## Spec for immediate engineering

> **12×12 Big5 點陣黑體 (fork U6 字庫)，全局統一，translation hard-cap = 原 ASCII bytes，不改 box width / shadow loop / dispatch**

從 Land.exe `print_func @ 09CE:0ECA` 開始 hook 一個 slot，餵 12×12 glyph blit，2 byte BIG5 in-place 替換 ASCII。Pe / Space 同 slot 模式重用即可。
