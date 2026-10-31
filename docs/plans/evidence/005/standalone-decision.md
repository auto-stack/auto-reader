# READER-005 T-00 决策稿：独立运行、媒体链、输入链与资源预算（2026-10-31）

状态：T-00 交付（work 阶段）。原始探针日志与夹具在
`D:/autostack/plan-artifacts/plan-005/`（本地暂存，不入库）；本文只记结论、
命令形态与关键数字。探针消费者 = 真实 auto-reader 应用；框架夹具仅用于
区分故障归属，不作为验收面。

## 1. 工具身份与发现顺序（本轮实测冻结）

| 组件 | 版本/身份 | SHA256 |
|---|---|---|
| `auto` CLI | `0.1.0+plan-890-verified-r7-t19-2-gbe740b6`（2026-10-31 构建） | `e7dd7df1be8f4d341a4f356e59dd887efe374245dacff92570e4c63c5246dcf8` |
| `auto-ui-tool` | 004 重建后同一二进制（`4d2198b8` pin 保持） | `4d2198b8bceba015c9f46157691fac2380cce720d0a5914fdec03c1cb39db47d` |
| auto-ui 仓 | `d85edbb`（与 Plan §4 观察值一致，未漂移） | — |
| auto-photos 仓 | `5eec01b`（与 Plan §4 观察值一致，未漂移） | — |

- 二进制位置：`D:/autostack/auto-man/target/debug/{auto,auto-ui-tool}.exe`。
- 发现顺序（驱动统一口径）：显式 `--auto-bin`/`AUTO_BIN` env → PATH `auto`。
  与 001 r9 记录的 CLI（`v0.0.20-118-ge6cc06f`/C049ABE3…）相比 **CLI 已升级**；
  001 归档中的运行时绑定 hash 只证明其冻结版本，本轮全部关键门按上表重新绑定。
- 旧缺口归因修订：N-003-7「AutoUI 无 image widget」**作废为前置事实**——
  Vue 发射器 `"image"|"Image" => "img"`（vue.rs L10626/L17014，src/alt/fit props），
  原生 `aura_view_builder` `convert_image_or_icon` → `View::Image{src,style}`。
  N-003-8（flattener zip 编译失败）保持历史记录；本轮 split-host 直连 profiles
  全程使用上表 CLI+tool，未再观察到该形态。

## 2. 真实 startup profiles（R-01/T-01 口径）

- **vue+vm（缺省交付面）**：`AUTO_READER_DATA=<隔离目录> AUTO_HTTP_STEP_BUDGET=1e9
  AUTO_HTTP_REQUEST_TIMEOUT_MS=300000 auto run --server=vm`。本轮实测：后端
  `GET /api/library/books → 200`（双层编码 JSON），vite 前端 `200`。端口
  front 17824（vite 监听 `localhost`，IPv6 回环）/ back 17825。
- **vm+vm（分离模式）**：`auto run -r vm --server=vm`，同 env；T-01 在端口
  空闲时以同法实测后补记录（本轮 vue+vm 实例占用 17824/17825，遵守一实例
  一写入者纪律未并行抢占）。
- 失败控制（R-01 负例）：错误 `--auto-bin` → 驱动启动超时非零退出；
  端口占用 → 服务器启动失败非零退出、既有实例不受影响（001 t01 驱动
  已有该形态，T-01 收口为 verify_standalone 入口断言）。
- 实测登记：直连 `POST /api/library/import` **缺省 `force` 形参 → HTTP 400**
  （框架按声明形参严格绑定）——驱动/真实 UI 均须显式传 `force:false`。

## 3. 图片/媒体链决策（T-02 依据，探针实测）

**实测事实**（探针：真实 EPUB 含两个可解码 PNG，导入→读章→URI 回读）：

1. `epub_chapter_json` 首读返回 `images:[{k,uri}]`，uri =
   `/api/__auto/media/<ticket>/<rev>`（`image.thumb` 票据）。
2. **VM HTTP 后端对该路径回 404**（`curl 127.0.0.1:17825/api/__auto/media/…`
   → 404）：媒体 HTTP 规则（`media_response_for_vm_request`）在 auto-lang/
   auto-man 全树 **无调用方**——生成的 a2r Rust 服务臂才有（plan811 消费者
   测试佐证），本应用不声明 rust 轨。
3. 媒体票据注册表是**进程局所**（global per-process）：split-host 拓扑下
   票据住后端进程，原生前端进程（iced）`resolve_media_render` 只查本进程
   → 两端都无法用 `image.thumb` 票据 URI 显示图片（Vue 无 HTTP 面，原生
   跨进程查无票据）。
4. 原生 iced `load_image_bytes`（renderer.rs L8152）src 词汇：
   `/api/__auto/media/*`（本进程票据）→ **相对 `/api/*` URL 按
   `AUTO_HTTP_BASE`/`AUTO_HTTP_PORT` 展开走 HTTP**（`auto run` 在父进程
   set_var，子进程继承）→ 本地文件路径（1s 负缓存自愈）。Vue `<img>` 走
   vite `/api` 代理（gen/front/vue/vite.config.ts）。
5. `http.file_response(root, relative_path, options)`（stdlib/auto/http.at
   L356；PLAN-729）从 `#[api]` GET/HEAD handler 返回即由 **VM 缺省 HTTP
   transport** 服务文件：单区间、条件请求、root 越界（..、绝对路径、盘符、
   UNC、DOS 设备）403。纯 .at 应用级能力，无框架前置。
6. `zip.extract_entry` 契约（zip_io.rs）：内存读侧 `take()` 硬闸 + 炸弹
   探针（-2 超闸），**读全后才单次 `fs::write`**——失败形态（-1/-2）不落
   dest、无半写残留（app 无 delete 原语亦安全）。

**决策（T-02 实施）**：

- 放弃 `image.thumb` 票据 URI 作为章图消费路径；图片资源经既有
  `zip.extract_entry`（12MiB 闸）落 `<managed>.chapters/`，由**应用自有
  稳定 URI** `GET /api/reader/media/:book_id/:res`（`http.file_response`
  承载）提供字节。该 URI 首读/缓存命中/冷重启逐字稳定，两端同源：
  Vue `<img src>` 经 vite 代理；原生 `image(src:)` 经 AUTO_HTTP_BASE HTTP。
- 缓存命中（dest 已存在）**同样返回可消费 URI**（修复 §4/Plan 已观察缺项）。
- 扁平化碰撞修复：`_`→`__`、`/`→`_` 双步转义（双射）——`a/b_c.png` →
  `a__b_c.png` 与 `a_b/c.png` → `a_b__c.png` 不再同槽错图。
- **预算冻结**：单资源提取闸 12MiB（超闸 rc=-2 → 拒绝码 `img_too_large`）；
  支持扩展名 profile = png/jpg/jpeg/gif/bmp/webp（浏览器与 iced 公共分母；
  svg 等不支持形态 → 拒绝码 `img_unsupported_type`）；提取失败 →
  `img_extract_failed`；缺条目 → `img_missing`。无应用侧解码承诺：服务
  原始字节，字节级损坏由渲染端错误显示承载（诚实能力边界，不做假检测）；
  全书图片总量受输入 30MiB 上限间接约束。
- **错误可见**：images[] 每项 `{k, uri, err?}`；err 项前端渲染可见错误行
  （不静默丢、不删行、书与位置不受损）。
- 拒绝/失败不触碰他书：媒体端点 root 钉在目标书 `books/<hashdir>/…chapters/`，
  `:res` 经 file_response root 越界检查（403），不具跨书可达性。

## 4. 书内链接/脚注 profile（T-03 依据）

- 支持形态：资源相对 href（OPF 目录基准，复用 `epub_href_ok`/`epub_zip_path`
  安全检查）+ 可选 `#fragment`。目标解析 = (spine 章号, 段落行号)：
  href 命中 spine hrefs → 章号；fragment = 块级元素 `id="…"` → 目标章中该
  元素开启的文本行行号。无 fragment → 目标章首段。
- **正文行字节格式零变更**（`img:` 行、段落行与 003/002 缓存逐字兼容——
  注释锚/Locator v1 para_text 不受影响）；链接/锚点表走章 JSON 旁路字段 +
  `<n>.links.json` 边车缓存（旧章缓存无需失效：链接表按需从 XHTML 重建，
  XHTML 原件在受管副本内，12MiB 闸不变）。
- 拒绝面（诚实拒绝，不静默）：带 scheme 的外部 href（`http:`/`mailto:` 等，
  `epub_href_ok` 的 `:` 拒绝已覆盖）、百分号编码、逃逸路径、未知 fragment、
  指向不受管资源的 href——UI 显示可见提示，不跳转、不执行远程/脚本。
- 重复段落/相同 fragment 出现在不同章：目标恒按 (href 资源路径, fragment)
  二元组解析，不以章内序号近似。

## 5. 输入/MCP 能力（T-04 依据）

- 原生轨 MCP 词汇（driver 实用集）：`autoui_snapshot`（mode=rendered）、
  `autoui_action`（element_id press；`AUTOUI_TEST_FIXTURES=1` 下 fixture
  trigger 仅承担导航）、`autoui_scroll_state`、截图。**button 按压通道可用**
  （001 r8/004 持续使用）；col/row 按压在活视图有 004 在案失配（段落点选）。
- 裁决：链接 affordance = **button chips**（双轨可按压面）；段落点选保持
  col onclick（Vue Playwright 面 + 原生 MCP 失配在 T-04 先定位
  driver/工具/产品责任，不得永久以 HTTP 保存绕过 UI 门）。
- Vue 轨输入：Playwright 全量（点击/键入/IME 不抢导航——002 L-U03 口径）。
- `text` → `span`（vue.rs L10587），行内子串点击不是双轨公共面——不作为
  链接交互形态（N-002-A-1 边界保持）。

## 6. 聚合与回归接续（T-05 口径）

- 新增 `tests/basic/verify_standalone.py --profile vue|vm`：聚合 R-01..06
  与受影响旧门（verify_epub、verify_local、native acceptance required 集、
  real-book/smoke Playwright），复用脚本旧入口保持可独立运行。
- 旧 skip 重判：verify_local vm 轨 1 SKIP（N-003-8 时代）须以本轮 CLI+tool
  重判；必需原生任务不得继承 skip。004 的两份正对照夹具只承担其自身边界，
  不顶替真实 app 结果。

## 7. 实施定稿补充（T-06 as-built，2026-11-01）

T-00 决策经 T-02..T-05 实施与聚合门验证后的落定形态（与 §3/§4 的差异与细化）：

- **媒体端点分层**：`GET /api/reader/media/:bid/:res` 落地于
  api.at → db.at `reader_media` → library.at `epub_media_response`
  （codegen db.rs 一致性门要求端点经 db 面；`auto build` 红即具名）。
  root = 书目受管副本 `<managed>.chapters`；`res_` 前缀 + [A-Za-z0-9._-]
  白名单；content type 按 res 扩展名（image/png|jpeg|gif|bmp|webp）。
- **拒绝码 as-built**：`img_too_large`（13MiB 实测 rc=-2）、
  `img_extract_failed`（缺条目 rc=-1；`img_missing` 为存在性后守卫，
  常态由 extract_failed 承载）、`img_unsupported_type`（bad.svg 实测）、
  `img_name_unsupported`（未收编字符，未在探针书触发——profile 边界）。
- **链接表**：`<n>.links.json` 边车（正文 .txt 零变更实证——行对齐由
  目标段逐字断言钉死）；章内容相对 href 以**自章 ZIP 目录**为基准
  （sub/ch3.xhtml 与 ../ch1.xhtml 双向实测）；无 fragment → 章首
  (para=-1)；三类诚实拒绝（外部 scheme/缺章/未知 fragment）+ 故意缺失
  的自章 fragment 同拒绝（#fn1 探针）。
- **输入回写**：搜索框/注释对话框 5 输入项真 oninput handler
  （`SearchInput` 等 str 形参——VM 轨事件通道按 handler 名送达，
  `NoOp` 丢值；auto-photos SetSearch 同款约定；Vue 24/24 回归不变）。
- **vue codegen 缺陷回避（跨仓债，当前 pinned CLI 实测）**：
  ①文件级 fn 形参与 widget model 字段同名 → codegen 对形参误加 `.value`
  （merge_marks `chapter_src`→`csrc` 改名，mount 即崩）；
  ②style 三元分支为 model 引用时被发空串（`(cond ? '' : '')`）——段标记
  类改字面量嵌套三元；连带 001 T-R10 V-20 在该 CLI 下恢复（real-book
  11/11）。两项 owner=auto-ui（vue.rs）。
- **原生 UI 通道边界（T-04 诊断矩阵，owner=auto-ui-runtime/auto-man）**：
  同窗同刻顶栏/抽屉/TOC 行按压 status:ok；scroll-pane 子树内全部按压
  （段落 col、chips button）"View not found at path"（styled_vtree↔typed
  view path 分歧）。VM 前端 `Http.post` 记录体缺参（400 missing param
  book_id 后端日志锚）+ 直连多字节体劣化（001 在案）→ 原生 UI 写传输
  缺口；纯 .at 无干净回避。原生读/导航/渲染面 + state_changes（写意图）
  + 服务端锚定数据契约由 tests/native/test_native_standalone_ui.py
  永久承载（37 records / 0 FAIL / 3 具名 GAP）。
- **顺带修复（003 遗留缺陷）**：EPUB 章标题恒回落"第 N 章"（titles
  双管道围栏）——T-02 探针实证后修复，章标题=nav 标签实测。
- **漂移核对（T-06）**：CLI e7dd7df1 / tool 4d2198b8 与 T-00 冻结一致；
  auto-ui d85edbb、auto-photos 5eec01b 未漂移。
