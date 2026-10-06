# Spec：auto-reader 真实导入、书库存储与位置恢复（READER-001 实现态）

状态：implemented（READER-001 T-00~T-04 交付；Phase 2 修复 T-05~T-10
2026-10-05 交付（SD-02~05）；Phase 3 修复 T-11~T-16 2026-10-06 交付
（SD-06~10，本版））；权威来源为本文件 + 代码与测试证据。变更须经计划复审。

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
library.json          {"version":1,"books":[BookRecord...]}（索引）
library.json.bak      上一次提交前的索引备份（写入读回校验；AC-05）
library.json.tmp      暂存物（提交前写并读回校验；与最终提交内容一致）
removed.jsonl         移除登记（JSONL；restore 后行剔除，清理经读回校验）
reading/<book_id>.json        ReadingState（覆写前 .bak，备份读回校验）
books/<hash 目录>/original.<ext>      受管副本主槽位（内容寻址）
books/<hash 目录>/d<N>/original.<ext> 隔离槽位（d1..d64，碰撞/损坏时分配）
```

BookRecord（library.json 内）：`book_id(uuid) source_hash(ph1) title author
format(txt|md) original_path managed_path size chapter_count import_version(=1)
created_at(=0，见 §6)`。字段以 record_json 实际输出为准。

写协议（所有持久化写共用，F-06 落地）：运行时**无 rename/delete 原语**
（T-00 映射集），协议为「已验证的暂存-提交-恢复」尽力保证，**不冒充断电级
原子性**——`verified_write` 写后必读回逐字比较（write_text 对目录等失败
形态会静默返回 rc=0，t05 探针实测）；目标已存在时先写 .bak 并读回校验
（备份失败/现内容为空/目标被目录占位一律中止，目标零触碰），.tmp 暂存读回
通过后才提交正式文件，提交读回不符时尽力从 .bak 还原。

## 3. 导入事务（POST /api/library/import）

1. 校验：路径非空 → 存在 → 非目录 → size>0（空文件拒绝）。
2. 解码门（双轨）：`File.read_text_range` 头部 64KB envelope `total==-1`
   → decode_error；全文 `read_text` 长度 ≠ file_size → decode_error
   （非法 UTF-8 双轨均使 read_text 回 ""）。
3. 指纹（候选索引，F-02 修正）：`ph1:<size>:<fold>`（逐行：行字节长+
   前 64 字符码点，模 1e9+7；外拼 size）。ph1 同值**只作候选**——对每个
   同指纹记录读其受管副本与本次全文**逐字比较**：相等才判 duplicate
   （existing_id 指向已有书目）；不等即碰撞，不误判重；副本缺失（记录在
   文件失）无法证实同文，同样不判重。`force=true` 创建独立档案。
4. 受管资产槽位（F-02/F-03 修正）：候选顺序 = 主槽 `books/<hash 目录>/
   original.<ext>` → `d1` → … → `d64`；首个「不存在」或「内容与本次全文
   逐字相等」的槽位命中（相等即复用，中断幂等语义，无重写）。内容不符的
   资产永不复用（碰撞不串文、损坏不误用）；新分配槽位写入后**读回校验**
   （F-03：新写入读回与源一致才允许建索引记录）。
5. 章节计数：importers.parse_book_json（txt 规则：第X章/节/回 ≤60B、
   Chapter N ≤60B、序章/楔子/引子/尾声 ≤20B；md 规则：`# `/`## ` 开新章，
   ### 留正文；章头前内容成"开篇"章；无章头 → 单章以文件主名为题）。
6. 索引追加 + 经写协议落盘；失败不落索引（无进程内状态）。

错误码：`ok | duplicate | invalid_path | is_dir | empty_file |
decode_error | io_error`。编码错误不给假成功；备份失败/索引写入失败时
索引保持原状（写协议中止，见 §2）。

索引加载语义（F-06 修正）：**缺文件**才初始化为空表；存在但为空（0 字节）、
解析失败（畸形/截断）、`version` ≠ 1（含 v0 旧形）、缺 books 或记录缺
字段——一律 refuse-to-load（books_json 返回 ""，调用方以 io_error 或
显式错误拒绝，消息含「人工迁移」），**保留原件逐字不变**，不静默清空、
不自动改写、不把损坏索引当新库覆盖（t06 规格实测）。迁移为人工动作；
library.json.bak 供回退。

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
| POST /api/library/progress | 写状态（body {book_id, payload, para_text}；payload 为状态 JSON 字符串经 jsonx.valid_state 词法门，para_text 为顶层内容锚点字段经 §5 核对；拒绝全族以 `{"ok":false,"message"}` 返回，与成功响应同构） |

错误消息历史形态（纯字符串）仅剩端点加载层；`/api/library/progress` 写
端点自 Phase 2 起统一 `{"ok":bool,"message"}`（框架绑定缺参为 HTTP 400
`{"error":...}` 形态）。写端点用 POST（VM HTTP 层 PUT+str 返回丢响应体，
T-02 实测）。**直连客户端请求体必须 ASCII 安全（\u 转义）**——VM HTTP
层把原始多字节请求体按非 UTF-8 解码（§6；浏览器经 vite 代理不受影响）。

## 5. Locator v1 与 ReadingState（Phase 3 内容锚点语义）

```json
{"book_id":"<uuid>","chapter_number":N,"paragraph_index":M,
 "para_hash":"sig1:<长度>:<行数>","para_text":"<段文本逐字全文>",
 "quote_prefix":"<可选≤64>","font_size":"medium|small|large",
 "line_height":"comfy|compact","updated_at":0}
```

- 段落 = 正文按 `\n` 切分去空行后的行序（idx = 原文行号）；
  `paragraph_index = -1` 表示章级书签（无内容锚点）。
- **内容锚点（F-08/F-10 修正，SD-06/SD-07）**：`para_text` 存段文本
  **逐字全文**，作为内容证明——**任何长度/行数签名（sig1 等）都不构成
  内容证明**（等长替换必碰撞，实测复现；r3 文本的「字节/字符双口径
  跨轨可用」表述自本版废止）。锚点核对 = 字符串相等（跨轨安全的唯一
  比较形态）；para_hash 仅作格式兼容位随 payload 发送，不参与内容判定。
- **写侧词法门**（put_reading_json + jsonx，F-09 修正）：payload 经
  `jsonx.valid_state` 词法校验——真实结构、已知键类型精确（整数键必须
  整数字面量：数字串/浮点/null/bool 拒绝）、已知键重复拒绝（含转义
  归一后重复）、合法空白与转义属性名兼容、尾随逗号拒绝；payload 内夹带
  para_text 拒绝（内容锚点由顶层 body 字段承载）。语义校验：book_id
  严格相等（藏无关字段无效）、chapter ∈ [1, 记录章节数]、paragraph ∈
  {-1} ∪ {指向本章非空行且 para_text 与该行逐字相等}、font/line 枚举、
  quote_prefix ≤64。任一拒绝不落盘、不触碰上一有效状态。
- **存储形态**：后端拥有文件形态——校验通过后构建规范 JSON（已知字段 +
  注入的 para_text；段级定位注入、章级书签不注入），经备份/暂存/提交
  协议（§2）落盘。
- **读侧容错**：状态文件存在但为空/解析失败 → 读回 ""（不冒充有效状态），
  损坏文件原样保留供诊断。
- **恢复语义**（reading.at，F-05/F-08 修正）：章节号一律以路由为准（显式
  /chapter/N 入口不被旧状态覆盖）；恢复须「保存章节 == 打开章节 + 段在场
  + 存储态 para_text 与当前段落逐字相等」齐备才标记「已恢复」；**缺内容
  锚点（旧 sig1 态）/内容失配/段失位**分别给诚实提示，不标记、不假恢复。
  保存须响应含 `"ok":true` 才显示成功，失败给可重试提示。
- **恢复滚动（F-12 修正，SD-09）**：正文列为 scroll-pane（PLAN-656 双轨
  controller）；恢复采用**两段式占比估算定位 v1**——渲染后溢出 scroll_to
  触发测量与 onscroll，再按「累计字符占比 × 可滚动跨度」精化。**精度
  边界（如实）**：均匀段落精确（直测入视口通过），极端混排有偏差；
  元素级定位原语缺失（无 child-anchor intent），登记为 auto-lang 框架
  前置提案——估算定位不是元素级精确恢复的替代承诺。
- 设计文档（design/01-product-design.md §3）的 Locator v1 exact_quote/
  text_offset 字段由 para_text + paragraph_index 承接，升级不改变存储
  键名（import_version 可扩展）。
- settings（font_size/line_height）随状态持久化；前端排版偏好先读状态、
  退回 storage。

## 6. 已登记能力边界（不伪装）

- **sha256 不可用**：hash.* 无 a2r 映射（VM-only）→ source_hash 用 ph1。
  ph1 为**候选索引**，前 64 字符采样折叠存在**确定性碰撞**（等长、每行前
  64 字符相同而行尾不同的文件必同值——非小概率事件，Phase 2 实测复现）；
  去重与资产复用一律经完整逐字内容核对（§3），碰撞内容隔离到独立槽位，
  不串文、不误判重。
- **10MiB 长文导入被阻断（保持未验收）**：VM 指令预算
  `CPU_CUMULATIVE_STEP_BUDGET=10M` 硬上限，实测 ≥1MiB 导入即超（512KB
  边界：响应可超时但服务端完成；t04 HTTP 已诚实化——空响应不算显式
  错误，并落盘对账库不变）。跨仓能力计划候选（auto-lang：预算可配/分片
  导入）；**本项 AC 目标保留未验收**，不以降标或「显式失败」替代通过。
- **rust 后端轨（`auto run` 缺省 vue+a2r）不可用**：动态 JSON 字段访问、
  uuid/time、substr cast、path-form use 等缺陷群（清单见
  docs/research/20261005-t00-runtime-capability.md §12）。pac.at 已按
  014-weather 先例不声明 `api: "rust"`。可用入口（README 同源，实测）：
  `auto run --server=vm`（Vue+VM）与 `auto run -r vm --server=vm`（VM
  全轨，分离模式）。裸 `-r vm` 会进 merged 模式——本应用前端数据面走
  HTTP（PLAN-043），merged 无 HTTP 服务器，**不可用**（实测）。
- **VM HTTP 请求体多字节损坏**：写端点请求体必须 ASCII 安全（\u 转义，
  标准 JSON；读回 json.parse 正常还原）。响应体正常 UTF-8。
- **VM HTTP 空响应竞态 + vite 进程树稳定性**（Phase 2 新登记）：响应体
  偶发丢失（服务端日志 200 有时延、客户端空体）；keep-alive 复用下更
  频密，浏览器全流程负载后观测过 `pnpm run dev` 退出带崩整个 `auto run`
  （code -1）。测试纪律 = 每请求新连接（spawnSync curl）+ 空响应重试 +
  每套件全新服务器。跨仓候选。
- **VM 测试装置对含 `use` 的模块编译失败且 CLI 退出 0**（Phase 2 新登记）：
  含 #[test] 的模块被迫零 `use` 或迁脚本规格；测试门必须「失败输出与
  退出码」同时成立。
- **document/window 等 DOM 透传仍为 Vue 轨单轨能力**（毒化实测维持）；
  但程序化滚动自 Phase 3 起有双轨路径——PLAN-656 scroll 控制器族
  （scroll_controller/scroll_to/scroll_by/scroll_state + onscroll，Vue=JS
  helper、VM=native+renderer intent），泛用列可用；缺的是**元素级定位**
  intent（无 child-anchor）——恢复滚动现以「占比估算定位 v1」实现（§5）。
- **MSYS 环境变量路径转换按进程不一**（Phase 3 登记）：MSYS 启动的
  auto.exe 会把 POSIX 形态 env 路径转为 Windows 形态，node/python 不会
  ——跨进程测试的数据目录定位须按进程分别核对（r4 复审 N-1）。
- **Vue 轨缺失字段拼接得 "undefined" 字符串**（Phase 3 登记）：`"" +
  obj.missing` 在 Vue 为字符串 "undefined"、在 VM 为 raise——跨轨守卫须
  双形态归一（reading.at 恢复路径已归一）。
- created_at/updated_at 恒 0（a2r_std 缺 time）。
- ph1 折叠只取每行前 64 字符码点（行长字节信息单独入折）。

## 7. 前端纪律（T-03 实测，违反即坏）

- widget 内局部 fn 不支持（parse error）——逻辑内联于 handler，纯计算
  下沉文件级 fn。
- 文件级 fn 的参数名禁与 widget model 变量同名（codegen 误加 `.value`
  → undefined）。
- f-string 插值内不放二元 `+`（被吞）；嵌套 if/else 配对不可靠（else 挂
  内层）——用独立正卫栅格。
- `json.from_value` 在 Vue 轨未映射（ReferenceError 被 catch 吞）；Http.post
  实参用裸映射字面量，且不得嵌套在 json.parse 实参位（codegen 静默失败）。
  store 层一律裸映射（AddBook/ImportBook/SetProgress 同款）。
- /api/library/* 响应双层编码：Http.get_json 后需再 json.parse。
- 路由为 hash 模式（`#/book/<uuid>/chapter/<n>`）；UI 测试导航须带 `#`。

## 8. 验证资产（Phase 3 重建，双轮一致；CLI 构建绑定见复审记录）

- 模块单测（#[test]，自包含零 use）：`auto test` → 5 通过
  （hashx 1 + pathx 2 + jsonx 2；importers 单测因「use 进测试装置编译
  失败」缺陷迁脚本规格 t03——CLI 对该失败退出 0 的缺陷已登记）。
- 脚本规格（VM 脚本轨；**失败输出与退出码同时判**，日志 %TEMP%/tNN-spec.log）：
  t01_library_spec（34）/ t02_reading_spec（38）/ t03_importers_spec（26）/
  t04_library_spec（14）/ t05_collision_spec（23）/ t06_integrity_spec（51）
  = 186 检查，全 PASS fails=0。
- 应用级 HTTP（全新隔离目录 + `auto run --server=vm`；直连请求体 ASCII
  转义）：t01（39）/ t02（26，词法/锚点/跨轨组）/ t04（12，10MiB 项
  空响应不算显式错误 + 落盘对账）= 77 检查。
- 复审驱动（数据目录名须 reader001-review-*）：
  `tests/review/reader001_repro.py` → 8/8（F-02/03/04/06）；
  `tests/review/reader001_r3_repro.py` → 12/0（F-08/09/10/11 Phase 3
  契约形态；原 r3 反例语义保留、F-10 按 content-anchor 契约重述——
  演进保真经 r4 复审逐例核定）。
- UI（Playwright，每套件全新服务器；PW_CHROMIUM 可覆盖浏览器可执行）：
  tests/real-book.spec.ts（9——含产品自滚视口直测与 emoji 真实点击
  回环）+ tests/smoke.spec.ts（10）。
- 独立复审（2026-10-06 r4）：双轮全量一致 + 全新向量行为探针 12/12
  有效 + 冷启动持久化 + VM 全轨零毒化——见计划 §9 复审记录。
- 干净数据目录启动：`bash tests/spec/run_fresh_server.sh`。
- **10MiB 成功导入保持未验收**（§6）；错误保护（显式失败 + 落盘对账
  库不变）为通过项单列。
