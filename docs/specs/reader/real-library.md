# Spec：auto-reader 真实导入、书库存储与位置恢复（READER-001 实现态）

状态：implemented（READER-001 T-00~T-04 验收交付，2026-10-05）；权威来源为
本文件 + 代码与测试证据。变更须经计划复审。

## 1. 模块与职责

| 模块 | 职责 | 边界 |
|---|---|---|
| src/back/pathx.at | 纯 .at 路径拼装/解析、JSON 转义、逐级建目录 | 只用双轨已映射 native；多字节安全（replace 链/find+substr 渐进切片，禁逐字节走查） |
| src/back/hashx.at | 内容指纹 ph1（source_hash） | 纯 .at；for-in 码点折叠（char_at 索引 VM 轨仅首字符有效，禁用）；非密码学 |
| src/back/importers.at | TXT/Markdown 章节切分（JSON 字符串面 + 内部 ChapterData） | 不改原文；EPUB 属 READER-003 |
| src/back/library.at | 书库存储、导入事务、去重、可恢复移除、阅读状态 | 无进程内缓存；JSON 字符串表面；单写入者/数据目录 |
| src/back/api.at + db.at | /api/library/* 端点（thin 体，db 委托） | 端点类型住 api.at；JSON 字符串返回 |
| src/front/book_store.at + pages/* | 合并书架（真实/Demo 徽标）、导入对话框、按段阅读、Locator 保存/恢复 | 前端不导入 back 模块；HTTP JSON 面 |

## 2. 数据布局（数据目录）

`AUTO_READER_DATA` env → `USERPROFILE/.autoreader` → `./.autoreader-data`。

```
library.json          {"version":1,"books":[BookRecord...]}（索引；写前 .bak）
library.json.bak      上一次成功写入前的索引备份（AC-05）
removed.jsonl         移除登记（JSONL；restore 后行剔除）
reading/<book_id>.json        ReadingState（覆写前 .bak）
books/<hash 目录>/original.<ext>   受管副本（内容寻址；同指纹 force 共享）
```

BookRecord（library.json 内）：`book_id(uuid) source_hash(ph1) title author
format(txt|md) original_path managed_path size chapter_count import_version(=1)
created_at(=0，见 §6)`。字段以 record_json 实际输出为准。

## 3. 导入事务（POST /api/library/import）

1. 校验：路径非空 → 存在 → 非目录 → size>0（空文件拒绝）。
2. 解码门（双轨）：`File.read_text_range` 头部 64KB envelope `total==-1`
   → decode_error；全文 `read_text` 长度 ≠ file_size → decode_error
   （非法 UTF-8 双轨均使 read_text 回 ""）。
3. 指纹：`ph1:<size>:<fold>`（逐行：行字节长+前 64 字符码点，模
   1e9+7；外拼 size）。同指纹默认 duplicate（existing_id 指向已有书目）；
   `force=true` 创建独立档案并共享受管副本。
4. 受管副本：`books/<hash>:→-目录>/original.<ext>`；已存在则复用。
5. 章节计数：importers.parse_book_json（txt 规则：第X章/节/回 ≤60B、
   Chapter N ≤60B、序章/楔子/引子/尾声 ≤20B；md 规则：`# `/`## ` 开新章，
   ### 留正文；章头前内容成"开篇"章；无章头 → 单章以文件主名为题）。
6. 索引追加 + 落盘；失败回滚语义 = 不落索引（无进程内状态）。

错误码：`ok | duplicate | invalid_path | is_dir | empty_file |
decode_error | io_error`。编码错误不给假成功；io_error 时索引保持原状。

索引版本门：library.json 的 `version` ≠ 1（含 v0 旧形/字段残缺）→ 索引
拒绝加载并**保留原件**（books_json 返回 ""，导入/移除/恢复以 io_error
或显式错误拒绝，消息含「人工迁移」），不静默清空、不自动改写（T-04
实测：脚本+HTTP 双面）。迁移为人工动作；library.json.bak 供回退。

## 4. 端点（JSON 字符串返回——双层编码，前端二次解析）

| 方法+路径 | 语义 |
|---|---|
| GET /api/library/books | 书目索引全文（`{"version":1,"books":[...]}`） |
| POST /api/library/import | 导入（body {path, author?, force?} → ImportOutcome JSON） |
| GET /api/library/books/:id | 单条记录；未找到返回 `""`（哨兵） |
| DELETE /api/library/books/:id | 可恢复移除：索引剔除 + removed.jsonl 登记；受管副本与用户原文件不动 |
| POST /api/library/books/:id/restore | 从 removed.jsonl 恢复 |
| GET /api/library/books/:id/toc | `[{"number":n,"title":t}]`（受管副本按需重切） |
| GET /api/library/chapter?book_id=&number= | 单章 JSON；缺失返回 title=内容缺失/章节不存在占位 |
| GET /api/library/progress?book_id= | ReadingState；无记录 `""` |
| POST /api/library/progress | 写状态（body {book_id, payload}，payload 为状态 JSON 字符串；校验书在库+对象+id 在场） |

错误消息以纯字符串返回（非 ok 包装）；校验失败 HTTP 500。写端点用
POST（VM HTTP 层 PUT+str 返回丢响应体，T-02 实测）。

## 5. Locator v1 与 ReadingState

```json
{"book_id":"<uuid>","chapter_number":N,"paragraph_index":M,
 "para_hash":"sig1:<byte长>:<行数>","font_size":"medium|small|large",
 "line_height":"comfy|compact","updated_at":0}
```

- 段落 = 正文按 `\n` 切分去空行后的行序（idx = 原行号）。
- para_hash 为**同轨一致**的长度签名（非跨轨内容指纹）：Vue `char_at`=
  JS charAt（字符）、VM=码点，双轨语义错位使跨轨指纹不可用（T-03 实测）；
  跨轨恢复由章节号+段序号定位。exact_quote 升级待传输层多字节修复。
- 设计文档（design/01-product-design.md §3）的 Locator v1 exact_quote/
  text_offset 字段由 para_hash + paragraph_index 承接，升级不改变存储
  键名（import_version 可扩展）。
- settings（font_size/line_height）随状态持久化；前端排版偏好先读状态、
  退回 storage。

## 6. 已登记能力边界（不伪装）

- **sha256 不可用**：hash.* 无 a2r 映射（VM-only）→ source_hash 用 ph1；
  同文件稳定，不同内容撞值概率极低但非密码学零（撞值表现为重复提示，
  用户可 force 保留独立副本）。
- **10MiB 长文导入被阻断**：VM 指令预算 `CPU_CUMULATIVE_STEP_BUDGET=10M`
  硬上限，实测 ≥1MiB 导入即超（512KB 边界：响应可超时但服务端完成）。
  跨仓能力计划候选（auto-lang）；本计划 AC 以「显式失败而非假成功」验收。
- **rust 后端轨（auto run 缺省 a2r）不可用**：动态 JSON 字段访问、
  uuid/time、substr cast、path-form use 等缺陷群（清单见
  docs/research/20261005-t00-runtime-capability.md §12）。交付轨 =
  `auto run --server=vm` 与 `auto run -r vm --server=vm`（均实测）。
- **VM HTTP 请求体多字节损坏**：写端点请求体必须 ASCII 安全（\u 转义，
  标准 JSON；读回 json.parse 正常还原）。响应体正常 UTF-8。
- created_at/updated_at 恒 0（a2r_std 缺 time）。
- ph1 折叠只取每行前 64 字符码点（行长字节信息单独入折）。

## 7. 前端纪律（T-03 实测，违反即坏）

- widget 内局部 fn 不支持（parse error）——逻辑内联于 handler，纯计算
  下沉文件级 fn。
- 文件级 fn 的参数名禁与 widget model 变量同名（codegen 误加 `.value`
  → undefined）。
- f-string 插值内不放二元 `+`（被吞）；嵌套 if/else 配对不可靠（else 挂
  内层）——用独立正卫栅格。
- `json.from_value` 在 Vue 轨未映射（ReferenceError 被 catch 吞——基线
  AddBook 同缺陷）；Http.post 实参用裸映射字面量，且不得嵌套在
  json.parse 实参位（codegen 静默失败）。
- /api/library/* 响应双层编码：Http.get_json 后需再 json.parse；
  纯文本错误消息非 JSON（双解需容错）。

## 8. 验证资产

- 单测（#[test]，pathx/hashx 自包含）：`auto test`（8 通过）。
- 脚本规格（VM 脚本轨，跨模块无 #[test] 装置缺陷）：
  `auto tests/spec/t01_library_spec.as`（34）、`t02_reading_spec.as`（13）、
  `t04_library_spec.as`（14）——全 PASS。
- 应用级 HTTP：`python tests/spec/t01_http_verify.py`（39）、
  `t02_http_verify.py`（12）、`t04_http_verify.py`（11）——全 PASS。
- 浏览器端到端（Vue 轨）：导入对话框→书架真实卡→阅读段落逐字→点段
  保存→刷新恢复（T-03，IAB 实测）。
- 干净数据目录启动：`bash tests/spec/run_fresh_server.sh`。
