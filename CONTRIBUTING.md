# 貢獻指南

歡迎參與 Planet's Edge 繁體中文化！

## 翻譯流程

1. **讀規範**：先讀 `translations/glossary.md` + `translations/style_guide.md`
2. **挑檔**：去 `translations/` 找一個 `translation_zh` 欄位多空的 TSV
3. **填中文**：保留原文欄位，只動 `translation_zh`
4. **檢查**：
   - 跑 `python tools/validate_translations.py <file.tsv>`（待補）
   - 中文 Big5 bytes ≤ 原 ASCII strlen
   - `%s` `%d` `\r` 保留位置
5. **送 PR**：commit 訊息格式 `translate(bch/objects): 200/252`

## RE / 技術貢獻

- C++17 + SDL2 為主，Python 工具輔助
- 16-bit DOS 反組譯用 rizin
- 跨平台 build 用 CMake + mingw-w64
- 不接受 Java / 自有 framework

## 法律

提交譯文視同同意 CC BY-SA 4.0 授權；提交程式碼視同同意 MIT。

## 程式碼 style

- C++17，4 spaces，prefer `std::span` / `std::optional` / `std::vector`
- 不要 raw new/delete，用 unique_ptr 或 RAII
- SDL2 資源用 RAII wrapper class
- Python 3.10+，type hints 鼓勵
