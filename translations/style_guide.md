# 譯文 style guide

> 為 1488 條字串提供統一翻譯風格規範，避免多人/多 agent 翻譯詞彙與口吻飄移。

## Hard rules（必守）

### 1. 字數雷區

**中文 Big5 bytes ≤ 原英文 strlen**

| 原文 | strlen | 譯文長度上限 | 範例 |
|---|---|---|---|
| `Tele-trans activated.` | 21 | 10 中文字 (20 bytes) + 1 ASCII | 「跳躍傳送啟動。」(8 中文字 16 bytes ✓) |
| `He's dead jim!` | 14 | 7 中文字 | 「他死了，吉姆！」(7 中文 14 bytes ✓) |
| `I have no items` | 15 | 7 中文字 | 「沒有任何物品」(6 中文 12 bytes ✓) |

**理由**：原版 message box 寬度固定，不擴 box width / shadow loop。

### 2. 保留 printf format specifiers

- `%s` `%d` `%u` `%c` `%x` 全保留原位
- 範例：`"I took a%s%s"` → `"我拿了%s%s"` (`%s%s` 保留)
- 不要把 `%s` 改成「？」或翻譯

### 3. 保留分隔字元

- `\r` (.bch 對話換行符) 保留位置
- 不要把 `\r` 替換成全形句號
- 範例：`"line 1\rline 2"` → `"第一行\r第二行"`

### 4. 全形標點

- 用「。」「？」「！」「，」「：」「；」 — 不用 ASCII `.?!,:;`
- **例外**: `%s` 後接的標點若原版是半形保留半形 (sprintf 需要 ASCII 對齊)
- 引號用「」/『』，不用 `""` 或 `''`

### 5. 縮寫 / 專有名詞

照 `glossary.md` — Tele-Trans 永遠是「跳躍傳送」，不可寫成「傳送」「瞬移」「跳躍」等變體。

## Soft rules（建議）

### 1. 口吻

- 系統訊息 / UI 標籤: **簡潔中性**（「裝備」「物品」「離開」）
- 角色對白: **保留原文情緒**（「他死了，吉姆！」帶感嘆語氣）
- 旁白 / 章節敘述: **稍微文雅**（「啟程的時刻已至」）

### 2. 軍事 / 科幻術語

PE 是 sci-fi 太空 RPG，常用：
- "Captain" / "Commander" → 「艦長」/「司令官」（看上下文）
- "shield" / "armor" → 「護盾」/「裝甲」
- "warp" / "jump" → 「曲速」/「跳躍」
- "scanner" / "sensor" → 「掃描器」/「感應器」
- "biosphere" → 「生物圈」

### 3. 玩家視角

- 第一人稱動詞用「我」（"I took"→「我拿了」）
- 第二人稱避免，多用無主語或被動

## 禁忌

- 不要意譯到失真（"Tele-trans" 不要翻成「瞬間移動裝置啟用完成」）
- 不要簡體字（即使 Big5 缺字也優先音譯，不退簡體）
- 不要超出 cp950 範圍的罕用字（會掉 glyph）
- 不要 emoji / unicode 符號

## QA checklist

每批翻譯完跑 `tools/validate_translations.py`（待寫）檢查：

- [ ] 所有 zh 欄位 cp950 encodable
- [ ] 所有 zh bytes ≤ en strlen
- [ ] 所有 `%s` `%d` 等 format 保留
- [ ] 所有 `\r` 保留
- [ ] glossary 統一詞彙（fix_term_drift.py 跑過）
- [ ] 抽樣 5% 人工 review

## 多 agent 平行翻譯流程

1. 共讀 `glossary.md` + 本 style_guide.md
2. 各自翻自己分到的 TSV
3. 全部跑完 → `fix_term_drift.py` normalize
4. reviewer agent 跑「QA pass」
5. 人工 spot-check 抽樣
6. commit
