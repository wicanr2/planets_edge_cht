# Contributors / 貢獻者名單

## 主要維護者 / Maintainers

- **[wicanr2](https://github.com/wicanr2)** — Project lead, RE, engine development, translation coordination

## 翻譯 / Translation

| 範圍 | 譯者 | 完成日 |
|---|---|---|
| Land.exe + Pe.exe UI (266 條) | wicanr2 + Claude | 2026-05-23 |
| Space.EXE UI (393 條) | wicanr2 + Claude | 2026-05-23 |
| Objects.bch 物品 (252 條) | _進行中_ | — |
| Spacet/1/2.bch 敘事 (280 條) | _進行中_ | — |

## 工程 / Engineering

| 項目 | 貢獻者 | 日期 |
|---|---|---|
| Reverse engineering (LZW, print_func, EXEPACK) | wicanr2 + Claude | 2026-05 |
| SDL2 C++17 engine spike | wicanr2 + Claude | 2026-05-23 |
| Windows cross-build (mingw-w64) | wicanr2 + Claude | 2026-05-23 |
| 12×12 Big5 font pipeline | wicanr2 + Claude | 2026-05-23 |
| Translation TSV pipeline | wicanr2 + Claude | 2026-05-23 |

## AI Assistance

本專案大量使用 **Claude (Anthropic)** 進行：
- 多 agent 平行翻譯（4 agent 同時跑不同 TSV）
- 16-bit DOS 反組譯解讀
- C++ 架構設計
- 各種 spike 與工具開發

AI-assisted 內容會在 commit message 標 `Co-Authored-By: Claude ...`。
譯文最終由人工 review，AI 是力倍器不是替代者。

## 想加入？

見 [CONTRIBUTING.md](CONTRIBUTING.md)。歡迎：

- 翻譯尚未完成的 TSV 條目
- Glossary 補強
- SDL2 engine 子系統 (audio / save / combat)
- Bug report / 字幕位置調整
- 1990 年代 NWC 歷史考據

提 PR 即視同同意 repo 多重授權條款（CC BY-SA / MIT / CC BY）。
