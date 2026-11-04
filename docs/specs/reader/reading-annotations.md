# reading-annotations — 本地阅读体验、注释与导出（READER-002 阶段A + READER-005 双端 UI 收口）

状态：current-state（阶段A 实际交付面 + 005 r1 真实 UI 验收扩展）。来源：READER-002 r3（phase review PASS on 1ea4dfd，phase merge 沉淀）；READER-005 r1（final review pass，2026-11-01）。B 阶段（Notes 真实交接/离线待发/幂等回执）尚未实现，不在此文档宣称。

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

## 双端 UI 验收现状（READER-005 r1）

- Vue 轨：注释创建/编辑/删除/回访/导出、搜索、恢复全流程真实 UI 驱动
  （Playwright ui_checks 11/11 + standalone_ui 3/3 + real-book 11/11）。
  输入回写 = 真 oninput handler（str 形参——VM 事件通道按 handler 名
  送达；`NoOp` 会丢值，005 修复）。
- 原生轨：注释抽屉/编辑对话框真实按压可达（MCP），type_text 经事件通道
  回写 model（state_changes 证明）；图像/链接/chips 渲染 + 冷重启恢复 +
  annotation_id 稳定由 `tests/native/test_native_standalone_ui.py`
  永久承载（37 records）。原生 **UI 写传输**受两项在册框架缺口阻断：
  ①VM 前端 `Http.post` 记录体缺参（400 missing param，N-r8-1 族）；
  ②直连多字节请求体劣化（001 在案）——创建/编辑的 UI 面由 Vue 承担，
  原生以 state_changes（写意图）+ 服务端锚定数据契约 oracle 承载；
  框架修复后重跑驱动即转正（驱动 GAP 判定内置）。
- scroll-pane 子树按压失配（004 在案）T-04 定责矩阵收口：同窗同刻
  chrome/抽屉/TOC 行按压 ok，子树内全失败——工具侧 styled_vtree↔typed
  view path 分歧（mcp_server.rs find_view_by_path），非 driver/产品。

## 具名平台缺口（owner 框架侧，不阻塞本规范交付面）

- N-002-A-1：无内联子串样式 span/富文本 widget（两轨同缺）——高亮以
  段级标记+chip 承载，注释身份/回访不受影响。
- N-002-A-2：原生 VM 轨 text_input IME composition 事件面——005 实测
  type_text/键入经真 oninput handler 双轨回写正常（SearchInput 等同款）；
  IME 组合键面差异仍未专项实测。
- N-003-8（003 在案，**前提已失效**）：`auto run --server=vm` flattener
  zip 编译失败为陈旧 auto-ui-tool 宿主误判（004 定案）——当前
  CLI+tool 双 profile 直连正常；verify_local vm 轨的原生 SKIP 前提由
  005 原生驱动承载转正。
- N-005-A-1（005 在案）：scroll-pane 子树 MCP 按压 path 分歧（见上）。
- N-005-A-2（005 在案）：VM 前端 Http.post 记录体缺参 + 多字节直连体
  劣化（见上）。
- vue codegen 两缺陷（005 实测，owner=auto-ui）：文件级 fn 形参与 widget
  model 字段同名 → 形参被误加 `.value`；style 三元 model 引用分支被发
  空串。应用以改名/字面量嵌套三元等价回避。

## 永久验证入口

- `python tests/annotations/verify_local.py --profile vue|vm [--auto]`：A-01..04 面（3 格式导入、20+ 注释、重复句 occurrence、诚实拒绝、导出独立解析、损坏诚实、layout/theme 持久、冷重启 annotation_id 稳定、Playwright UI 面）。基线成绩（005 r1，CLI e7dd7df1/tool 4d2198b8）：vue 50/50、vm 49+原生面由 005 驱动承载。
- `python tests/native/test_native_standalone_ui.py --auto-bin <auto.exe>`：原生注释抽屉/对话框按压、type_text model 回写、导出/删除数据契约、冷重启恢复（005 交付）。
- `auto tests/spec/t10_annotations_spec.as`：服务端规格 69 检查（CRUD/occurrence/锚点拒绝/损坏容错/搜索/导出/layout-theme/源改版/CRLF+多字节计数）。

## 精确 range 新形态与版本化导出（READER-007 T-05/T-07 交付）

- v2 记录 = v1 字段恒在场（回退面，跨段/引擎选区诚实章级 pi=-1）+ 可选
  canonical `locator` 对象（SD-02 语义）。create 经
  `/api/library/annotations-v2` 携带（恢复环核验 + 同一性通过才落盘）；
  op=anchor 为存量 v1 追加（唯一映射证明才生成）；锚字段不可变。
- 永久门：`tests/product/verify_epub_product.py` P-04（重复句第 2 处/
  跨段范围真实 UI 选区→canonical locator→v2 落盘→verify-ann 匹配→
  编辑/删除）、P-05.v2-anchor（唯一映射锚定/已锚拒绝/TXT 不可映射/
  多义 context 错位 needs_relocate）、P-08.mutation-matrix（身份链/
  资源身份/位次/上下文六变异具名拒+零写入）。
- 导出：v2 记录追加「定位（v2）：spine=N cfi=<start.cfi>
  occurrence=scope#idx」行（canonical 字段直取，独立可解析；纯 v1 记录
  无此行不伪造定位）——P-07.export 独立解析门 PASS。
