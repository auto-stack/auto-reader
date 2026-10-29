# Spec：auto-reader 真实导入、书库存储与位置恢复（READER-001 实现态）

状态：implemented（READER-001 T-00~T-04 交付；Phase 2 修复 T-05~T-10
2026-10-05 交付（SD-02~05）；Phase 3 修复 T-11~T-16 2026-10-06 交付
（SD-06~10）；Phase 4 修复 T-17~T-21 2026-10-06 交付（SD-11~15，本版；
T-22 终审 pass，F-12 混排视口恢复与 10MiB 成功导入两项显式未验收））；
权威来源为本文件 + 代码与测试证据。变更须经计划复审。

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
**整数元数据协议（F-15 修正，SD-13）**：size/chapter_count/import_version/
created_at 必须为整数字面量（小数/指数如 1.5/1e2 拒绝）——jsonx.valid_index
在备份、资产与索引任何改写前统一校验（所有读改入口共享），错误形态拒绝时
索引与已有资产逐字保留；合法整数记录与空数组正常导入。

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
- **读侧入场门**（get_reading_json，F-14 修正，SD-12）：读状态即校验——
  jsonx.valid_state 词法（类型/重复键/结构）→ book_id 与请求 book_id
  **严格相等** → 必需字段（chapter_number/paragraph_index/font_size/
  line_height/updated_at）在位且枚举合法 → 否则返回 "" 且原件逐字保留
  （错书态/缺字段态/数字串态不冒充有效状态）。前端恢复另守身份（存储态
  book_id ≠ 路由即弃用）。**缺失判别用属性存在性**（`x != nil` 编译为
  宽松 `!= null`，覆盖 Vue undefined；F-13 修正，SD-11）——禁止把字符串
  "undefined"/"null" 归一为哨兵：合法正文含这些字面量时保存与恢复逐字
  成立（旧 sig1 缺锚点态仍诚实提示）。
- **恢复语义**（reading.at，F-05/F-08 修正）：章节号一律以路由为准（显式
  /chapter/N 入口不被旧状态覆盖）；恢复须「保存章节 == 打开章节 + 段在场
  + 存储态 para_text 与当前段落逐字相等」齐备才标记「已恢复」；**缺内容
  锚点（旧 sig1 态）/内容失配/段失位**分别给诚实提示，不标记、不假恢复。
  保存须响应含 `"ok":true` 才显示成功，失败给可重试提示。
- **恢复滚动（F-12，r8 落地 / r9 双轨出证；SD-09/SD-14 的「占比估算 v1」自本版废止）**：
  正文列为 scroll-pane；reading_page 每个段落带**稳定子 key**（`p<行号>`，
  PLAN-781 `scroll-anchor` DSL，Vue/VM 双轨同源）；恢复路径在「保存章节 ==
  打开章节 + 段在场 + para_text 逐字相等」齐备后，把目标段以
  **`scroll_to_child`（元素级 intent）** 入队，滚动由产品自行完成——不再
  使用「累计字符占比 × 可滚动跨度」估算（混排构型下占比≠排版高度，实测
  目标落 pane 外）。**验收 oracle = 目标段 rect 与 `[data-scroll-pane]` 的
  正面积交集（V-20）**：Vue 轨 = Playwright `tests/real-book.spec.ts` T-R10
  （已由 fixme 转正）；VM 轨 = 原生驱动 `tests/review/reader001_r8_native_vm_restore.py`
  的 `autoui_visibility`（¶50 正面积可见）+ pane offset>2000（深位）+ ¶100
  尾部反差。框架原语 owner=auto-lang PLAN-781（已归档），app 不越权改核心。
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
- **10MiB 长文导入（原阻断项；r8 关闭、r9 复验）**：PLAN-781 交付宿主可信
  预算配置——`AUTO_HTTP_STEP_BUDGET`（可配至 4e9，`run_fresh_server.sh` 注入
  1e9）与 `AUTO_HTTP_REQUEST_TIMEOUT_MS`（300000）。**成功导入为已验收门**：
  10MiB / 2001 章 t04 **19 PASS / 0 FAIL**（章数对账 + 首/中/末章逐字前缀）+
  deep 全章 oracle（`tests/spec/t26_deep_10mib_verify.py`，EXIT=0，重启前后
  两轮逐字 + 受管副本 SHA256==原件）。默认 10M 指令预算下的**显式拒绝**仍是
  负例保护（错误保护 ≠ 成功门）。
- **handler 合成是「整 handler 编译期门」（N-r8-2，r9 定案）**：VM 轨 handler
  内对 `let` 变量重赋值（身份守卫 `pr = null` 即实例）会使**整个 handler**
  编译失败；框架把未产出 prolog 的导出按 Plan 423 P5 判毒丢弃（**判定正确**，
  否则运行期从指令中间进入栈失衡）。框架侧原缺陷是**失败静默**（合成失败只进
  未接线的 `log::warn`）；auto-lang PLAN-886 后恒出 stderr：`[SYNTH-FAIL]
  handler synthesis failed: <原因>` 与 `[CODEGEN] dropping poisoned export
  '<name>': entry <addr> is not FN_PROLOG (byte, code_len, ±4 窗口)`。
  **app 纪律**：handler 内可变绑定一律 `var`；「页面挂载但 Init 不执行/内容空」
  先看 stderr 的 `[SYNTH-FAIL]`。早期"模块名 `reading` 触发 outlet"结论已撤销
  （污染期误读）。
- **N-r8-2b（Vue codegen int 降档，维持）**：文件级 fn 形参不进 int 证明集，
  `/` 裸发射且 `as int` 退化为 `Number()` 不截断 → 后端 int 参数严格拒 float
  （进度 PUT 400）。app 侧用除法自由环（`pct_of` / `pct_bookshelf` /
  `pct_detail`）规避；跨仓 codegen 债。
- **N-r8-1 / N-r8-3（预存，非本仓门）**：①VM 轨导入对话框 store→`Http.post`
  裸记录体缺参（400 `missing param path`，Vue 轨同路径正常）——验收驱动改走
  library HTTP（与 UI 点段/导入传输等价）；②`autoui_action` press 派发的
  handler 内 `router.push` 为 no-op（书卡为 col onclick、MCP 无 col 点击原语）
  ——原生导航经 `AUTOUI_TEST_FIXTURES=1` 的 fixture trigger 承担（仅导航、
  不注入恢复行为）。
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

## 8. 验证资产（r9 全量重跑；构建绑定见复审记录）

- 模块单测（`#[test]`，自包含零 use）：`auto test` → **6/6**。
- 脚本规格（VM 脚本轨；**失败输出与退出码同时判**，日志 %TEMP%/tNN-spec.log）：
  t01（34）/ t02（38）/ t03（26）/ t04（14）/ t05（23）/ t06（91=56+35 S13）/
  t07（67，章 meta 索引 parity）= **293 检查 0 FAIL**。
- 应用级 HTTP（全新隔离目录 + `auto run --server=vm`；直连请求体 ASCII 转义）：
  t01（39）/ t02（26）/ t04（**19 PASS/0 FAIL**，含 10MiB 成功门）= **84 检查**。
- 复审驱动（数据目录名须 `reader001-review-*`；每份配全新服务器）：
  `reader001_repro.py` → **8**；`reader001_r3_repro.py` → **12**；
  `reader001_r4_repro.py` → **8**；`reader001_r5_repro.py` → **5**；
  `reader001_r6_repro.py` → **24**；`reader001_r7_repro.py` → **14**
  （全部 pass 记录、0 fail；r7 为独立向量：信封/record 准入、fail-closed、
  i32 边界、重复恢复幂等）。
- UI（Playwright，每套件全新服务器；`PW_CHROMIUM` 可覆盖浏览器可执行）：
  `tests/real-book.spec.ts` → **11/11**（T-R10 混排视口恢复转正，V-20 正面积
  几何门）；`tests/smoke.spec.ts` → **10/10**。
- 原生 VM 轨（PLAN-781 通道，AutoUI MCP + fixture trigger 导航）：
  `tests/review/reader001_r8_native_vm_restore.py` → **16 记录 / 0 fails**
  （boot → 导入 → 保存 → 冷重启 → 导航 → ¶50 正面积可见 + pane 深位 + ¶100 反差）。
- 干净数据目录启动：`bash tests/spec/run_fresh_server.sh`。
- 运行时绑定（r9，两个二进制均须含 PLAN-886 诊断面）：`auto` =
  `0.1.0+v0.0.20-118-ge6cc06f`，SHA256=`C049ABE3385D3E3634301A5DD1EE843E41A4CAACD2DE4214EA8D942EAB43D72E`；
  `auto-ui-tool`（VM 轨真正执行 handler 合成的进程），SHA256=
  `C1F54640120A19A9054ABD4B7C732B07F37F687D501A1891A59427DD368E1651`。
- 原两项显式未验收（10MiB 成功导入、F-12 混排入 pane）**已于 r8/r9 关闭**，
  证据见计划 §9 的 r8/r9 回执；不再保留"未验收"残留表述。
