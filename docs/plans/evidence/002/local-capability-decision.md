# READER-002 T-00 能力冻结：本地阅读/注释/导出（阶段A）

- 日期：2026-10-31
- 基线：main `30fcfb5`（worktree `D:/autostack/.wt/reader-002/auto-reader`，branch `plan-002-dev`，base 同提交）
- 依赖交付：READER-001（archived/r9）、READER-003（archived/r3，merge `24c9838`，landing verify_epub 21/21 PASS）
- 工具链：auto 0.1.0+v0.0.20-118-ge6cc06f；测试统一走 `tests/spec/run_fresh_server.sh`（隔离数据目录 + AUTO_HTTP_STEP_BUDGET=1e9 + 请求超时 300s）
- 关键源核对（sha256 前16位，base 30fcfb5）：`library.at` ada11e2dd52b27ac（相对 Plan §4 记录 dd41fe7d… 的差异=003 已合入，预期）、`reading_page.at` d16ef8c9cea420d6（与 §4 一致）、`pac.at` 36d1e3efa1940180（与 §4 一致）

## 1. 内容 / locator / 选区（冻结）

- 双格式同面：TXT/MD 与 EPUB 章文本均经 `GET /api/library/chapter`（library.at `chapter_json`：epub 分支走惰性解压缓存 `epub_chapter_json`，其余走 meta 窗口 `File.read_text_range`），返回同构 `{number,title,body,word_count}`。注释锚模型可对格式无关，统一锚在 (book_id, chapter_number, para_idx, quote)。
- 段模型（reading_page.at `split_paragraphs`）：body 按 `\n` 切分、trim、去空行，`idx`=原行号，`key`=`p<idx>`（pane 内稳定子锚）。 Locator v1 阅读状态：`<data>/<book_id>.reading.json`，后端逐字核对 `para_text`（字符串相等跨轨安全）、读侧严格 schema 校验、损坏回 `""` 拒绝假恢复（get_reading_json）。
- 版本身份：library.json 每书记录 `source_hash`/`managed_path`（注释需记录创建时 source_hash，回访失配诚实标注）。
- 选区现状：UI 仅段级（`TapParagraph`）；文本 widget 整串渲染、row 不换行，**两轨均无子串 span 选区/内联高亮 widget**（见 §5 具名缺口 N-002-A-1）。
- 恢复定位：scroll-pane controller + `scroll_to_child(p<idx>)`（PLAN-781 子内容锚，双轨同源 nearest 公式）；完成 oracle=真实 offset 变化+目标正面积交集（001 V-20 门式样）。

## 2. Unicode 与双端输入可达性（冻结）

- 内容 UTF-8；锚相等为字符串相等。中文/GBK fixture 已有（xiaoshuo*.txt、gbk.txt）；emoji 用例 t02 已在册（可能 SKIP，A 级验证自建）。VM HTTP 请求体内多字节历史性损坏 → 既有规避：锚文本走顶层 JSON 字段（框架转义、前端零转义），payload 内仅 ASCII 签名（`sig1:len:lines`）。注释 quote/comment 一律走顶层字段，不进手工拼接 payload。
- `input`/`textarea` widget 双轨在册（vue codegen + VM native catalog：Input/Textarea→text_input），生产在用（auto-chat `oninput/onenter`；auto-musk `onkeydown($event)`、`onkeydown.enter.exact.prevent`、r11 IME composition 守卫先例）。搜索框/注释输入可达。
- 快捷键裁决：**不做 window 级全局键盘 handler**（AutoUI 无可靠 document focus 查询面，抢输入框/IME 事件风险不可控）；快捷动作绑定到具体 widget（搜索框 onenter、注释对话框按钮、`.exact.prevent` 修饰的 textarea 键位）。结构性避免抢事件，A-01 以中文+emoji 输入实测守卫。
- storage（前端 KV `br-font-size`/`br-line-height` 先例）双轨可用，仅作排版偏好兜底；注释/书签持久化一律后端文件（单一事实源）。

## 3. 样式配置 / 注释版本（冻结）

- 排版偏好：font_size small/medium/large、line_height compact/comfy，后端 reading.json 权威 + 前端 storage 兜底；真实书模式以 `/api/library/progress` 为源（fill_pref 先例）。A 阶段沿用枚举集，不改既有枚举（旧状态兼容）。
- 注释版本：新增 `<data>/<book_id>.annotations.json`（version:1 + book_id + source_hash + annotations[]），写侧沿 put_reading 协议：严格 schema 门（类型精确/重复键拒绝/长度与数量上限）→ write_with_backup（.bak/暂存/提交/读回校验）→ 失败不落盘；读侧损坏→`{"ok":false,message}` 诚实报错不清除原文件（.bak 保留上一态）。
- annotation 字段：annotation_id（str.uuid，创建后不变）、book_id、source_hash、chapter_number、para_idx、quote（锚段逐字子串）、occurrence（段内第几次出现，≥1，重复句判别）、kind（bookmark|highlight|comment）、comment（≤2000）、tags（≤10×32）、created_at/updated_at（epoch 秒）。
- 读写端点：`GET /api/library/annotations?book_id=`、`POST /api/library/annotations`（op=create/update/delete，body 顶层字段直传，复用 progress 的传输形态）。回访判定服务端执行：段落文本变化→quote 不再是子串→`needs_relocate` 态（原 quote/comment 保留，绝不静默换锚）；source_hash 失配→显式标注来源版本已变。

## 4. 资源边界与错误（冻结）

- 搜索：新增后端扫描端点（TXT/MD 走 meta 章窗口 read_text_range；EPUB 走既有章缓存路径），逐章段粒度匹配、每章/总量上限（扫描章数 ≤200、结果 ≤50），不整书一次性载入内存。
- 导出：后端 `POST /api/library/export` 生成 `<data>/exports/<book_id>-annotations-<ts>.md`（书名/作者/版本身份/每条注释的章节+段 locator+原句+人工注释+标签），写侧 verified_write+读回校验，返回 {ok,path,count}；Notes 缺席不阻塞（纯本地文件，A-03 以独立 Python 解析核对）。文件导出≠真实接收（B 阶段另账）。
- 错误面：全部沿 001/003 既有形态——{"ok":false,"message"} 同构错误、缺书/缺章/损坏/越界诚实失败、无虚假 saved；前端保存失败提示可重试（F-05 先例）。

## 5. 具名平台缺口（交 owner，不阻塞 A 交付）

| id | 缺口 | A 内落地方式 |
|---|---|---|
| N-002-A-1 | 无内联子串样式 span / 富文本 widget（两轨同缺，与 N-003-7 image 同类） | 高亮以段级标记（border/bg + 注释数 chip）+ 注释列表/对话框承载原句；annotation 身份/回访不受影响 |
| N-002-A-2 | 原生 VM 轨 text_input 的 IME composition 事件面与 web 轨差异未在本仓实测 | T-04 双端验证时实录；若原生轨无 composition 守卫面，以 widget 级键位绑定规避，缺口如实记录 |

## 6. 结论

A 阶段全部需求可在现平台有界落地：注释锚模型（D：段级+子串+出现序）、搜索（段粒度+上限）、导出（后端文件）、双端真实操作（input/textarea/按钮 + Playwright/AutoUI MCP 通道）。两处平台缺口具名，不以 mock 冒充，不重写 003，不扩全局重构。进入 T-01。
