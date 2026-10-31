# reading-annotations — 本地阅读体验、注释与导出（READER-002 阶段A 现实现规范）

状态：current-state（阶段A 实际交付面）。来源：READER-002 r3（phase review PASS on 1ea4dfd，phase merge 沉淀）。B 阶段（Notes 真实交接/离线待发/幂等回执）尚未实现，不在此文档宣称。

## 注释锚模型（格式无关）

- 注释记录：`annotation_id`（服务端 `str.uuid()` 分配，创建后不变）、`kind`（bookmark|highlight|comment）、`chapter_number`、`para_idx`（原行号口径，与前端 split_paragraphs 同式：空行占位不产段）、`quote`（锚段 trim 后行文本的**逐字子串**）、`occurrence`（段内第几次出现，1-based 重叠计数）、`comment`（≤2000）、`tags`（≤10×≤32 非空串）、`created_at`/`updated_at`（epoch 秒，服务端 `time.now_sec()`）。
- 锚核验在服务端：创建时章可达、段行在界非空、quote 为段文本逐字子串、`count_occurrences(para, quote) >= occurrence`（滑窗 substr 逐位比较——find 偏移不喂 substr，多字节/字节口径错位防御，t10 S11 回归钉死）；不满足诚实拒绝（`{"ok":false,"message"}`），不静默换锚。
- update 只允许 kind/comment/tags；锚字段（chapter/para/quote/occurrence/created_at/annotation_id）不可变。换锚 = 删除 + 新建。
- 回访重定位：消费面按同式重算（段落文本变化 → quote 出现序不足 → `needs_relocate` 诚实态，原摘录保留，绝不静默跳错）；源版本变化后新建旧锚被拒绝（t10 S10）。

## 存储

- per-book 边车 `<AUTO_READER_DATA>/annotations/<book_id>.json`：`{"version":1,"book_id","source_hash","updated_at","annotations":[...]}`（服务器拥有文件形态）。
- 词法门 `jsonx.valid_annotations`：结构/类型精确/重复键拒绝/kind 枚举/tags 上限/长度上限；坏文件 refuse-to-load（读侧 `ok:false` 诚实报错，原件保留，不冒充空集）。
- 写协议沿 001 put_reading：严格校验 → write_with_backup（.bak/暂存/提交，全读回校验）→ 失败不落盘；空现文件拒绝覆写。
- 端点：`GET /api/library/annotations?book_id=`、`POST /api/library/annotations`（op=create|update|delete；用户文本一律顶层字段直传，多字节传输安全与 progress 同源）。

## 全文搜索

- `POST /api/library/search {book_id, query}`：段粒度**精确子串**（不做大小写折叠——VM 无 to_lower 映射，双轨一致性优先）；para_idx 与段模型同口径；上限扫描 ≤2000 章、结果 ≤50（`truncated` 如实标注）；空 query/缺书诚实拒绝。

## Markdown 导出（本地离线交付，≠真实接收）

- `POST /api/library/export {book_id}` → `<data>/exports/<book_id>-annotations-<uuid8>.md`：书名/作者/书目 ID/来源指纹（source_hash）/导出时间/注释数，每条注释含章节+段 locator、原句（blockquote）、段内出现序注、批注、标签、annotation_id。
- verified_write + 读回校验；空集合诚实 `count:0 path:""`（无文件产生）。文件导出是 A 阶段离线能力，不等同于 Notes 真实接收（B 阶段另账）。

## 双端 UI 边界（Vue + 原生 VM 同源 reading_page）

- 快捷键裁决：**无全局键盘 handler**（AutoUI 无可靠 document focus 查询面）；搜索 onenter、注释对话框按钮、widget 级触发——输入框/IME 组词不被抢（ui_checks L-U03 实测键入不导航）。
- 搜索抽屉（结果点击 JumpTo：跨章先装载序列再 `scroll_to_child(p<idx>)` 锚点定位）；注释抽屉（回访跳转/编辑/删除/导出按钮/需重定位徽标——徽标仅对当前章核对，未核章不做未证断言）；注释对话框（quote 预填整段可编辑截取、occurrence 序号、comment/tags）。
- 点段=记位置（001 Locator v1 行为不变）；注释入口在当前段动作行「＋ 注释/书签」。
- 排版偏好扩展：`layout`（narrow|medium|wide 阅读列宽）与 `theme`（light|sepia|dark 沉浸面底色）随 reading 状态持久化（见 real-library.md SD-02 扩展节）。

## 具名平台缺口（owner 框架侧，不阻塞本规范交付面）

- N-002-A-1：无内联子串样式 span/富文本 widget（两轨同缺，与 N-003-7 同类）——高亮以段级标记+chip 承载，注释身份/回访不受影响。
- N-002-A-2：原生 VM 轨 text_input IME composition 事件面差异未实测——N-003-8（auto run flattener zip 编译失败）修复后随原生轨 UI e2e 一并实录。
- N-003-8（003 在案）：`auto run --server=vm` flattener 对 zip 模块编译失败——双端验证绕行为 `auto service --server vm` 直连 + gen/front/vue vite 独立前端（verify_local.py 永久入口承载）。

## 永久验证入口

- `python tests/annotations/verify_local.py --profile vue|vm [--auto]`：A-01..04 面（3 格式导入、20+ 注释、重复句 occurrence、诚实拒绝、导出独立解析、损坏诚实、layout/theme 持久、冷重启 annotation_id 稳定、Playwright UI 面）。基线成绩：vue 50/50、vm 49+1SKIP（N-003-8）。
- `auto tests/spec/t10_annotations_spec.as`：服务端规格 69 检查（CRUD/occurrence/锚点拒绝/损坏容错/搜索/导出/layout-theme/源改版/CRLF+多字节计数）。
