# 統一譯名表

> 翻譯時遇到下列名詞請查表，避免一個東西被翻成多種說法。
> 新增條目時請維持「**英文** | **建議中文** | **備註**」表格欄位。

## 系統/動作

| 英文 | 建議中文 | 備註 |
|---|---|---|
| Tele-Trans / Tele-trans | 跳躍傳送 | 太空船到行星表面的傳送 |
| Centauri Device | 半人馬裝置 | 主線解謎物件 |
| First Contact | 第一次接觸 | 章節名 |
| U.N.F.A. | 聯合星際艦隊 | (United Nations Federation of Astronauts?) 縮寫保留英文 |
| Sector | 星區 | Sector Kornephoros = 庫尼弗洛斯星區 |
| Spawn | 卵生族 | 外星種族 |
| Cin Sae | 辛賽人 | 外星種族 |

## 戰艦/裝備

| 英文 | 建議中文 | 備註 |
|---|---|---|
| Ship's Beam Weapons | 光束武器 | |
| Ship's Bolt Weapons | 螺栓武器 | |
| Ship's Proj Weapons | 投射武器 | Proj = Projectile |
| Ship Repair | 船艦維修 | |
| Item Repair | 道具修復 | |
| Light Weapons | 輕兵器 | |
| Heavy Weapons | 重兵器 | |
| Hand Weapons | 近戰武器 | |
| First Aid | 急救 | |

## 物品/資源

| 英文 | 建議中文 | 備註 |
|---|---|---|
| Heavy Metals | 重金屬 | |
| Inert Gasses | 惰性氣體 | |
| Soft Metals | 軟金屬 | |
| Common Liquid | 普通液體 | |
| Hybrid Solids | 複合固體 | |
| Alien Gasses | 異星氣體 | |
| Alien Metals | 異星金屬 | |
| Alien Isotope | 異星同位素 | |
| Alien Crystal | 異星水晶 | |
| Alien Organic | 異星有機物 | |
| Alien Liquids | 異星液體 | |
| Rare Elmnts | 稀有元素 | Elmnts = Elements |
| New Elmnts | 新元素 | |

## 八個元件 (mission goal)

| 英文 | 建議中文 | 備註 |
|---|---|---|
| M.I.C.T.U. | M.I.C.T.U. | 縮寫保留 |
| Algocar | 阿戈卡 | |
| K-bean | K豆 | (or 保留英文) |
| Harmonic Resonator | 諧振共振器 | |
| Mass Converter | 質量轉換器 | |
| Gravitic Compressor | 重力壓縮器 | |
| Krupp Shields | 克魯伯護盾 | |
| Algiebian Crystals | 阿吉比安水晶 | |

## 動作回應 (Land.exe)

| 英文 | 建議中文 | 字數雷區 |
|---|---|---|
| Tele-trans activated. | 跳躍傳送啟動。 | 21→11chr (Big5 = 22 bytes) OK |
| Tele-Trans is disrupted here | 此處跳躍傳送受阻 | 28→10chr (20 bytes) OK |
| I took a%s%s | 我拿了%s%s | %s 必須保留 |
| I can't carry anymore | 我無法再攜帶更多 | 21→8chr (16 bytes) OK |
| I have no items | 我沒有物品 | 15→5chr (10 bytes) OK |
| Now wearing %s | 現在穿著 %s | |
| %s in %s hand | %s 在 %s 手 | |
| I can't Wear or Wield that! | 無法穿戴或持有！ | |
| Never mind. | 算了。 | |
| Drop Item | 丟棄物品 | |
| %s dropped | 已丟棄 %s | |
| There is no room here | 這裡沒有空間 | |
| Examine which item? | 檢查哪個物品？ | |
| Examine Item | 檢查物品 | |
| Use which item? | 使用哪個物品？ | |
| Use Item | 使用物品 | |
| No save during combat. | 戰鬥中無法存檔。 | |
| This corpse is worthless | 屍體無價值 | |
| Search corpse | 搜索屍體 | |
| It's a%s%s | 是一個%s%s | %s 保留 |
| I cannot move any further now. | 現在無法繼續移動。 | |
| He's dead jim! | 他死了，吉姆！ | Star Trek 哏 |
| Repeat command to quit game. | 再次確認以離開遊戲。 | |
| Repeat command to confirm Tele-trans | 再次確認以跳躍傳送 | |
| Maybe if I was on the right side! | 站對位置才行！ | |
| Perhaps if I was on the right side. | 也許要站對位置。 | 跟上條近義句 |
| Thank you for playing Planet's Edge. | 感謝您遊玩天際寒星。 | 遊戲結束訊息 |

## 元 Style Notes

- 全形標點：用「。」「？」「！」「，」不用 ASCII `.?!,`
- `%s` `%d` `%u` 等 printf format 必須保留原樣不翻
- `\r` 是 .bch 內 dialogue 換行符，保留位置
- 縮寫 (UNFA, MICTU) 視語境保留英文或音譯
