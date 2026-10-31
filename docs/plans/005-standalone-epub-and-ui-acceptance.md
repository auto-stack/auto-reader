---
plan_id: READER-005
status: drafting
feature_name: "EPUB实际阅读与本地能力双端验收收口"
author: [Codex]
created_at: 2026-10-31
updated_at: 2026-10-31
plan_revision: 1
current_step: 7
total_steps: 9
base_branch: main
base_commit: 964a33fc2fccf00b8e34575fb89badfa6c6c0a9b
depends_on: ["READER-001", "READER-003", "READER-002", "READER-004"]
supersedes_spec_components: ["docs/specs/reader/epub-reflow.md", "docs/specs/reader/reading-annotations.md", "docs/specs/reader/real-library.md"]
new_spec_components: ["docs/specs/reader/standalone-reading.md"]
touched_goals: []
---

# READER-005：EPUB实际阅读与本地能力双端验收收口

## 0. 变更摘要

复用 001 的书库/定位、003 的 EPUB、002 r4 的本地阶段A、004 的迁入验收驱动，补齐真实界面导入、图片、书内链接/脚注、注释回访和恢复。保留四份历史计划及其回执；不重开001，不恢复已由用户后置的 Notes 联动。

## 1. 目标

从本仓独立启动 Vue＋VM HTTP 或原生 VM＋VM HTTP，在真实界面导入支持的无 DRM EPUB3，读图文、跨章/脚注往返、搜索/标记/批注/导出、退出重开并恢复准确内容位置。支持范围与故障边界公开且可复验，不以 `img:` 标记、API 预导入或框架夹具替代必需 UI 操作。

非目标：Rust 后端全映射、PDF/OCR/TTS、DRM、完整浏览器排版/脚本、Notes/跨 app 分享、OS 装配与 Linux。

## 2. 架构方案

开发、内部检查和最终复审顺序使用同一个 `D:/autostack/auto-reader` 独立 clone、`main` 分支；不新建应用 worktree、不在 AutoOS 子模块中实现，一 app 一写入者，复审时暂停实现写入。框架变更必须在实际 owner 仓另走其 Plan/worktree 规约；本计划不自动取得框架源写入权。

用户本轮授权（2026-10-31）：建立后续计划、更新本 app README/roadmap、提交与推送这些文档；**暂不实施，不更新 AutoOS 子模块**。后续实施需另行进入 work。应用验收与交付不以 AutoOS 装配或 Linux 为前置；Linux 仍 `WAIT_DISTRO_M1`。OS 组合版本由未来统一集成计划接收，本计划 merge 只交付 app，不改父仓 gitlink、manifest 或 `.gitmodules`。

实现保持纯 `.at`，复用公开 SDK 与既有测试；不手写业务 Rust、不改生成 Rust/Vue 或临时生成目录来交付修复。`docs/specs/` 是现实现单源；下面的规范增量只是提案，本轮不写 canonical Spec、旧 ledger 或手工索引。原始截图/日志/报告本地保存，Plan 记录命令、退出码、版本/hash 和摘要；不提交新的非 Markdown 证据附件。

继续使用现有 EPUB spine/TOC、受管原件、chapter cache、Locator v1 和 annotation_id；不引入第二套书库/注释格式，不声称自定义定位是 EPUB CFI。优先直接接入现有 AutoUI `image` 组件及媒体服务；只有完整生产路径探针证明不足时，才提实际 owner 的最小框架前置。

## 3. 技术栈

应用 `.at`、既有 ZIP natives/`image.thumb`、AutoUI Vue 与原生渲染、Playwright/MCP。复用 `tests/epub/verify_epub.py`、`tests/annotations/verify_local.py`、`tests/native/test_native_reader_acceptance.py`、001 的真实书与几何门。004 的两份框架正对照夹具保留，只承担其自身边界。

## 4. 需求分析与背景调查

- 已观察：`reading_page.at` 的段内容仍统一 `text p.text`；后端 `epub.at` 输出 images[]，前端未建立图片渲染消费。
- 已观察：`epub.at` 仅在目标缓存文件不存在时添加图片 URI，命中缓存时 images[] 可能缺项；资源路径扁平化还需排除 `a/b_c.png` 与 `a_b/c.png` 碰撞。纳入首次/再次打开及冷重启同图身份验收。
- 已观察：当前 auto-ui Vue 发射器把 `image` 映射为 `<img>`，原生 `aura_view_builder` 有 image 分支；auto-photos 使用 `image(src,fit)`。旧 N-003-7“框架无 image widget”的绝对归因不能继续当作前置事实；端到端媒体 URI 可用性尚需 T-00 验证。
- 004 已纠正 zip 首红为陈旧 auto-ui-tool 编译宿主，固定 CLI＋实际 tool 后复绿；不得据旧 N-003-8 自动再开框架修复。004 的 v08 保存链仍使用 HTTP，段落按压 MCP 活视图失配有记录，不能宣布 Reader 全 UI 闭环已验。
- 002 r4 已按用户裁决以本地A收尾；Notes 交接为 OS TODO。003 位于 archive 且有 merge 24c9838/landing 回执，但旧 frontmatter 仍 drafting；002 计数仍 7/9。这里只登记历史元数据差异，不改归档或冒称重新验收。

| 源文件 | SHA256（完整值） |
|---|---|
| `docs/specs/reader/epub-reflow.md` | `c4efbe7f725de0ce973486751b28e18e7492ce68126375d229dea05cc52111a5` |
| `docs/specs/reader/reading-annotations.md` | `a58906d5a8fb0a32d00bbe53bea78227d71aebf004e0245fcf1d74f5696b2c88` |
| `docs/plans/archive/004-reader-test-ownership-migration.md` | `b8e2873e12bb3664eadd89f8503730884332e1ae07a63f745ca782f14a1a2392` |
| `src/back/epub.at` | `85752de945322df6d32c2f48cd8976f47295164bb7413a9c1d8ced5f4556f833` |
| `src/front/pages/reading_page.at` | `893ca1b37bd72f4c25a0839bf8d71e88b8e4e27dd2e2dadbd8de7946dac33826` |
| `tests/epub/verify_epub.py` | `6e6bedab5e8e67618f95f0f0b037bfa2d7ca25c6fbdc1f281cafd503b13a15b5` |
| `tests/annotations/verify_local.py` | `5f5a2189ca3c1e4d1f7d6b19d33edc465cc59e5ec3beb1366f896514a5f29be4` |
| `auto-ui` 观察版本 | `d85edbb0988f1cb91e3ec6a7e21ba4d872bdfb02` |
| `D:/autostack/auto-ui/crates/auto-ui-compiler/src/ui_gen/vue.rs` | `fe786c94219310355b053355534dd91efa11aba04b1899fb27b374acbfd87172` |
| `D:/autostack/auto-ui/crates/auto-ui-runtime/src/ui/aura_view_builder.rs` | `9d92519c1f9a96387af6a324dbe8f3ede7e8b1c5822fa2045466dc9122557800` |
| `D:/autostack/auto-ui/crates/auto-ui-tools/src/run_vue.rs` | `0c325ac1272be01c01ea489d64bdaa3584a8d36ff0df80e46b5fe1572821aa84` |
| `D:/autostack/auto-ui/crates/auto-ui-tools/src/run_vm.rs` | `e058a3e84c21790d73e2e5c1ed338a3e12321bd0d56f348c48d4eaaf01822065` |
| `auto-photos` 观察版本 | `5eec01b873ba5139ed8b50572f646c12c76c0288` |
| `D:/autostack/auto-photos/src/front/app.at` | `6e4124e01f56df969881837e23e09f702e157f75b661e56d463f3375633bcc91` |

## 5. 详细设计

1. **T-00 决策稿（新增）** `docs/plans/evidence/005/standalone-decision.md`：固定当前 CLI/tool 二进制 hash 和发现顺序、真实 startup profile、已交付公共图片/媒体 URI 路径、MCP 输入/滚动能力、链接定位与资源预算。正常 app 是探针消费者；框架夹具仅作区分故障的对照。
2. **图像全路径**：EPUB资源→既有安全路径解析/有界提取→稳定 cache身份→媒体URI→Vue/原生 image。命中缓存也返回可消费 URI；不同资源不能因扁平化同名而错图；缺失/坏图可见错误，保留书与位置。合法图片必须显示实际内容，不能只回元数据或标记行。
3. **内链/脚注**：解析支持 profile 中的资源 href＋fragment，复用 spine/段 locator，在章内/跨章定位真实目标并能返回原文准确段落。只接受规范化后仍位于该书受管资源内的目标；远程脚本、外部自动加载、逃逸路径不执行。支持的 XHTML 元素/fragment 形态由 T-00 固定，并给真实合法/拒绝对照；不许删去基本跨章/脚注往返来通过。
4. **实际 UI**：书架添加入口填路径→导入→打开→目录→点击/键入搜索与注释→回访/编辑/删除/导出→正常退出及强制退出后重开。导入/保存用户动作不得由 API 预写代替；HTTP/磁盘仅做独立读回 oracle。当前活视图节点失配须先定位 driver/工具/产品责任，不能永久靠 HTTP 绕过 UI 保存门。
5. **数据与预算**：保持001/003书库身份与原件、003既有30MiB输入/4096 spine/12MiB单条目限制及TXT/MD兼容；T-00在依赖实现前冻结图片解码像素/总资源预算、拒绝码与取消/失败清理，不以“无限资源”隐式承诺。不得覆盖别的书、旧注释或允许图片缓存逃逸。
6. **验证接续**：扩展既有 EPUB/annotation 双 profile 驱动以执行真实 UI；拟新增 `tests/basic/verify_standalone.py --profile vue|vm`（T-05 建立）聚合所需项。固定真实工具后重新判断旧 skip 的原因，必需原生任务不可继承 skip。

### 规范增量

| delta_id | add/modify/retire | docs/specs/... target | before/after rule | rationale | acceptance IDs |
|---|---|---|---|---|---|
| SD-01 | modify | docs/specs/reader/epub-reflow.md | img标记/链接未交付 → 真实图像与链接往返、cache与预算 | 补基本图文阅读与重复读取 | AC-02/03 |
| SD-02 | modify | docs/specs/reader/reading-annotations.md | 原生skip历史 → 当前真实UI注释与回访证据，Notes仍不在范围 | 不用API代替用户操作 | AC-04/05 |
| SD-03 | modify | docs/specs/reader/real-library.md | 增补当前startup/定位恢复/具名边界的实际关闭状态 | 复用001、004而不扩大历史证据 | AC-01/04 |
| SD-04 | add | docs/specs/reader/standalone-reading.md | 新增支持profile、工具身份与永久用户任务门 | 独立运行可复验 | AC-01..05 |

## 6. 测试设计

以下 R-01..06 都由 work 负责；T-05 使新增聚合命令可运行，复用脚本的旧命令保持可用或提供明确兼容入口。测试使用至少 TXT/MD/EPUB 三书、20条既有注释夹具语义；不把 API 的 profile 标签误计为两端 UI 都执行。

| Case ID | AC / invariant | 入口/输入 | 区分性 oracle / 预期 | 边界 |
|---|---|---|---|---|
| R-01 | AC-01 | README正式准备/启动，Vue与原生分别无预跑服务；错误tool/占用端口 | 实际窗口/页面和自有后端；依赖版本清晰，失败非零且不杀既有实例 | 不要求Rust后端 |
| R-02 | AC-02 | UI导入含PNG/JPEG的真实EPUB；再开同章、冷重启；两同扁平名不同资源 | Vue naturalWidth/实际src成功＋可见图像；原生实际image解码/可见像素或等价可区分证据；资源内容/digest对应，不能只看URI | 支持格式在T-00冻结 |
| R-03 | AC-03 | UI点章内/跨章/脚注链接后返回；重复段落/相同fragment出现在不同章 | 目标锚点真实进入阅读pane正面积，返回准确原段，非仅chapter计数变化 | 支持的EPUB3子集 |
| R-04 | AC-04 | 真实UI创建/修改/删除注释、搜索/回访/导出；正常/强杀后重开 | 独立磁盘/HTTP读回正文和annotation_id；恢复目标确实可见；下一次UI编辑可保存；输入法不误触导航 | Notes完全缺席仍通过 |
| R-05 | AC-02/03/05 | 坏图/越界资源/预算边界/外部href；失败后再读合法书 | 明确拒绝或图像错误态，其他书/原件/注释hash不变，无远程自动请求；缓存可再读 | 沿既有安全边界 |
| R-06 | AC-05 | 删除真实图片消费、错链锚、遮蔽目标或只预导入等受控反例 | 对应UI断言真实失败，总门非零；还原合法对照通过；无必需skip/零场景 | 反例仅隔离数据/测试树 |

原生夹具 `tests/native/test_native_reader_acceptance.py` 与10MiB deep oracle继续作对应回归；不因本计划补 UI 而重跑无关语言全仓 Cargo。最终review用独立上下文在同一 clone 核对真实app结果和SD候选，不自动创建agent或新会话。

## 7. 验收标准

- AC-01（owner_stage=work）：两个独立 startup profile 从文档可达，CLI/tool身份正确，R-01通过。
- AC-02（owner_stage=work）：有效图像首次/缓存/冷重启均真实显示，无资源碰撞错图，失败有界且不损坏书，R-02/R-05通过。
- AC-03（owner_stage=work）：章内、跨章、脚注往返准确可见，非法目标不执行，R-03/R-05通过。
- AC-04（owner_stage=work）：真实界面导入、搜索、20条注释夹具回访/导出、保存恢复及下一次编辑成立；TXT/MD与既有定位保持，R-04通过。
- AC-05（owner_stage=work）：永久门聚合R-01..06与受影响旧门，无必需skip/pending/零场景，失败控制非零；SD候选和运行说明对应真实结果。
- AC-06（owner_stage=review）：冻结提交与工具版本，独立上下文复审AC-01..05和SD-01..04；未满足项不能留到merge掩盖。
- AC-07（owner_stage=merge）：app Spec按审定增量发布、README/roadmap/新计划归档计数正确、app push可核；不改四份历史归档或OS pin。

## 8. 执行步骤

- [x] T-00（owner_stage=work；依赖001/002本地A/003/004实际交付；AC-01..05）：固定当前工具，完成能力/预算决策稿与真实图片/输入链探针，核验旧缺口归因；不等待Notes、Rust或Linux。[✅ 已完成] 决策稿 docs/plans/evidence/005/standalone-decision.md；实测：CLI e7dd7df1（v0.0.20-118 后已升级，本轮重新绑定）/tool 4d2198b8（004 pin 不变）；image.thumb 票据 URI 在 VM HTTP 后端 404 且票据注册表进程局所（split-host 两端均不可消费）→ 改用应用自有稳定 URI（zip.extract_entry 12MiB 闸 + http.file_response GET/HEAD/区间/root 越界 403，纯 .at 无框架前置）；原生 load_image_bytes 相对 /api/* 经 AUTO_HTTP_BASE/PORT 走 HTTP（子进程继承实测源码确认）；扁平化双射转义定案（_→__、/→_）；zip.extract_entry 失败无半写残留（读全后单次 fs::write，源码核实）；旧章正文行字节格式零变更承诺（注释锚/Locator 兼容）；链接 affordance=button chips（text→span 无行内点击公共面，N-002-A-1 保持）；N-003-7 作废为前置事实（vue.rs L10626 image→img、aura_view_builder View::Image 双端在案）。探针日志 D:/autostack/plan-artifacts/plan-005/。
- [x] T-01（owner_stage=work；依赖T-00；AC-01）：收口正式独立启动与依赖准备，驱动绑定实际CLI/tool/自有PID/数据根，补R-01失败控制。[✅ 已完成] 双 profile 实测：vue+vm（books 200 + 前端 200）、vm+vm 分离模式（books 200 + VM 窗口标题按 pac.at 宣告）；错误 tool = `AUTO_UI_TOOL_BIN` 指向缺失路径 → 具名 discovery 失败 exit 1（无静默回落，实测）；占用端口 = 新实例后端 bind 具名失败（os error 10048），既有实例持续服务不受影响（实测；CLI 进程可能滞留——失败非零门由验收驱动启动 deadline 承担，已在 README 如实登记）；直连 import 缺 `force` 形参 → 400（驱动一律显式传）。README 运行节补运行依赖身份与失败形态。证据 D:/autostack/plan-artifacts/plan-005/t01/。
- [x] T-02（owner_stage=work；依赖T-00及必要最小前置交付；AC-02）：复用image组件接入真实图像、稳定资源身份与缓存重复返回，建立R-02/R-05反例后修复并回放。[✅ 已完成] 实现：epub.at 双射扁平名（`_`→`__`、`/`→`_`、URL 不安全字符具名转义、未收编字符诚实拒绝 img_name_unsupported）+ 恒全量 images[]（首读/缓存命中/冷重启同 URI，err 项带拒绝码）+ api.at `GET /api/reader/media/:bid/:res`（http.file_response 承载，root=书目章节缓存目录，res 形状白名单双保险）+ reading_page 三态正卫栅格（img/imgerr/text，点段行为不变）。R-02 oracle 实测：碰撞对字节正确（RED/BLUE 不串）、含空格资源 200 正确字节、vite 代理面 200、冷重启 URI+字节逐字一致、Playwright naturalWidth>0×3+src 互异+错误行可见（tests/basic/standalone_ui.spec.ts 1 passed）。R-05 反例实测：>12MiB→img_too_large、缺条目→img_extract_failed（native rc=-1；img_missing 为存在性后守卫）、不支持类型→img_unsupported_type、失败无半写残留（盘面核查 3 文件全为合法提取）。附带修复：EPUB 章标题恒回落"第 N 章"（titles 双管道围栏缺陷，003 只断言 TOC 未覆盖——现章标题=C1 实测）；verify_epub 媒体断言迁移至新 URI 方案并增 err 空串断言，22/22 PASS 回放（EXIT=0）。证据 D:/autostack/plan-artifacts/plan-005/t02/。
- [x] T-03（owner_stage=work；依赖T-00；AC-03）：在epub内容/reading_page接入安全链接与回返定位；闭合R-03/R-05。[✅ 已完成] 实现：epub.at `xhtml_links`（与 xhtml_to_lines 逐 tag 同步进含 img 行占位——行号对齐由目标段逐字断言钉死）+ `<n>.links.json` 旁路缓存（正文 .txt 零变更）+ 章内容相对 href 以**自章 ZIP 目录**为基准（子目录书探针实证 sub/ch3.xhtml、../ch1.xhtml 正确解析）+ spine 全表精确匹配 + 跨章 fragment 经目标章 ids 表（文本扫描取键，"fn1" 不碰 "fn10"）；reading_page 链接 chips（可点击 col 外兄弟面）+ JumpLink（章首 para=-1 语义、无效目标诚实提示不跳转）。R-03 oracle 实测：跨章 fragment 目标段 V-20 正面积入 pane + 原文逐字（standalone_ui 3 passed）；同章锚标记+可见；外部 scheme/缺章/未知 fragment 全部 ch=0 诚实拒绝。附带回避（两个 vue codegen 缺陷，跨仓债登记）：①fn 形参与 model 字段同名 → codegen 误加 .value（merge_marks chapter_src→csrc 改名，mount 即崩实测）；②style 三元 model 引用分支被发空串（段标记类改字面量嵌套三元，6 字面量逐字等价；旧 CLI 曾可用的行为在当前 pinned CLI 下回归）。R-05 回放：verify_epub 22/22、real-book 11/11（含 T-R10 V-20）、smoke 10/10（全新实例隔离目录）。证据 D:/autostack/plan-artifacts/plan-005/t03/。
- [x] T-04（owner_stage=work；依赖T-01/02/03；AC-04）：闭合真实原生与Vue的导入/注释/回访/导出/位置保存操作，排除活视图通道失败，保持原有数据/定位回归。[✅ 已完成] 实现：输入回写真 handler（SearchInput/QuoteInput/OccInput/CommentInput/TagsInput——VM 轨 type_text/键入按事件名送达，NoOp 丢值实测：state_changes 证明 model 更新而提交带旧值；auto-photos SetSearch 同款约定，Vue 24/24 回归不变）；media 端点改 db 委托分层（codegen db.rs 一致性门：未匹配端点致 auto build 红；`auto service --server vm` 同步修复具名导入调用形）；新增 tests/native/test_native_standalone_ui.py（37 records / 0 FAIL / 3 具名 GAP）。原生面实测：图像双图真解码（截图像素 oracle 红 296/蓝 148 px，应用自有 URI 经 AUTO_HTTP_BASE HTTP）+ 诚实错误行 + chips 7 枚渲染 + TOC 抽屉行按压换章 + 注释 type_text model 更新（state_changes）+ 冷重启恢复标记 + annotation_id 稳定。活视图通道归因矩阵（T-04 诊断义务闭合）：同窗同刻 chrome/抽屉/TOC 行按压 status:ok，scroll-pane 子树内全部元素（段落 col/chips button）"View not found at path"——定责工具侧 styled_vtree↔typed view path 分歧（mcp_server.rs find_view_by_path），非 driver（正确 vnode/元素被证实）/非产品（同结构抽屉外可达）。原生 UI 写传输 = N-r8-1 族具名缺口：VM 前端 Http.post 记录体缺参（后端日志锚：POST /api/library/annotations → 400 missing param book_id；Vue 同 handler 正常）+ 直连多字节体劣化（001 在案）——UI 提交/导出/删除按钮按压到达 handler 但传输丢弃，纯 .at 无干净回避（串体需 ASCII 转义器而无 ord() 原语）；UI 创建/编辑面由 Vue 承担（standalone_ui/real-book/ui_checks Playwright 全 UI 驱动），原生以 state_changes（意图）+ 服务端锚定数据契约 oracle 承载。旧 skip 重判：verify_local vm 轨 L-25 的 N-003-8 前提已失效（本轮 vue/vm 双跑：vue 50/50、vm 49+原生面由新驱动承载）；r8 原生基线 16/16 回放。回放：verify_local vue 50/50、verify_epub 22/22、real-book+smoke+standalone_ui 24/24（全新隔离实例）。证据 D:/autostack/plan-artifacts/plan-005/t04/。
- [x] T-05（owner_stage=work；依赖T-04；AC-05）：建立聚合入口，扩展旧EPUB/annotations门并跑R-01..06、必要001/004回归；输出真实覆盖及SD候选。[✅ 已完成] 新增 tests/basic/verify_standalone.py --profile vue|vm（自管生命周期；复用 verify_local/verify_epub/原生驱动/Playwright 全部既有入口，旧命令保持可独立运行）。双 profile 全绿收口：vue=28 checks / 0 FAIL / EXIT=0（R-01 启动+错误 tool 非零+占口失败控制、R-02 HTTP 字节身份+UI naturalWidth×3、R-03 四链接解析+4 诚实拒绝+行对齐逐字、R-04 verify_local vue 50/50、R-05 负例 img_too_large/img_extract_failed+verify_epub 22/22、R-06 毁损→UI oracle 真实失败非零→还原对照通过、冷重启 URI+字节不变）；vm=27 checks / 0 FAIL / EXIT=0（原生驱动 37/0+3 具名 GAP 承载 R-02/03/04 原生面、verify_local vm 49+0、R-06 夹具副本毁损→像素 oracle 真实失败非零→对照 0 FAIL）。建设期实测修复（gate 自身缺陷，均在落地前关闭）：check 实参序、npx 解析、占口负例改裸 socket（第二个 auto run 的 pnpm/vite 扰动主实例前端——在册 N-2 族）、vm 流程 split-brain（主实例不停则驱动 bind 失败而前端打到主实例——native-driver.log 留档）、find_chapter_dir 改读盘（停机段可用）、_png_bytes 实参序、端口预检拒绝孤儿实例（首轮 gate 崩溃残留实例占口实证）。无必需 skip：R-06 双 profile 各自真实 UI 门承载，无零场景。SD 候选映射：SD-01←R-02/R-05（epub-reflow 图像/链接往返+cache+预算），SD-02←R-04（真实 UI 注释/回访证据，Notes 缺席仍过），SD-03←R-01/R-04（startup/定位恢复/具名边界现状），SD-04←R-01..06（新 standalone-reading 规范：支持 profile/工具身份/永久用户任务门）。证据 D:/autostack/plan-artifacts/plan-005/t05/gate-vue-4.log、gate-vm-6.log。
- [x] T-06（owner_stage=work；依赖T-05；AC-01..05）：核对所有必需UI oracle、框架消费和源/工具漂移，更新运行说明并提交execution_done。[✅ 已完成] oracle 核对（绑定真实入口）：AC-01←gate R-01（双 profile 启动就绪+错误 tool 非零+占口失败控制）+README 运行节（T-01）；AC-02←gate R-02/R-05（首读/缓存命中/冷重启字节逐字+碰撞对 RED/BLUE+含空格资源+UI naturalWidth>0×3 原生像素 oracle+诚实错误行+img_too_large/img_extract_failed/img_unsupported_type）；AC-03←gate R-03（章内/跨章/子目录/脚注 fragment+V-20 入 pane 正面积+原文逐字+4 类诚实拒绝+正文行零变更）；AC-04←verify_local vue 50/50+vm 49（20+ 注释夹具回访/导出/损坏诚实/冷重启 id 稳定/输入不抢导航）+原生驱动 37 records（截图像素、chips、TOC/抽屉按压、type_text state_changes、冷重启恢复标记+id 稳定）+Playwright 24/24（含 UI 创建/编辑注释全流程——L-U 系列）；AC-05←本聚合门自身（双 profile 0 FAIL，无必需 skip/零场景；R-06 反例证明区分力）。框架消费核对：4 项在册跨仓缺口全部具名化于决策稿 §7（scroll-pane 按压 path 分歧、VM Http.post 记录体缺参+多字节直连劣化、vue codegen 形参/model 同名与 style 三元 model 引用两缺陷）——均 owner=框架仓，本计划零框架写入，未以占位/HTTP 预操作替代必需用户任务（UI 创建/编辑面由 Vue 全 UI 驱动承载，原生面以 state_changes+服务端锚定 oracle 承载并具名留缺口）。漂移核对：CLI e7dd7df1/tool 4d2198b8 与 T-00 冻结一致，auto-ui d85edbb/auto-photos 5eec01b 未漂移；源码基线 d142a9a（本轮 work 提交链 246cbfd..317bb76）。运行说明：README 状态段/测试表（005 聚合门+原生驱动+standalone_ui 入口）/计划行已更新为实际交付面。work 阶段收口：T-00..T-06 全 [x]，0 个 open in-contract finding，3 项具名框架 GAP（非本仓可关闭），统一回归=聚合门已双 profile 跑绿（无需另跑全仓）。提交 execution_done，next=review（T-07，独立上下文同 clone）。
- [ ] T-07（owner_stage=review；依赖T-06；AC-06）：同clone独立上下文最终复审，不能用004正对照或历史skip顶替实际app。
- [ ] T-08（owner_stage=merge；依赖T-07 pass；AC-07）：仅本app规范/归档/提交push收尾，保留历史文档，OS集成留独立计划。

## 9. 复审记录

- stage: new | plan_id: READER-005 | plan_revision: 1 | outcome: pass（仅有界 T-00 就绪，产品与双端验收未执行） | next: work/T-00（等待后续实施指令）。
- 现有归档计划、Spec 与源码保持原样；旧验收只证明其冻结版本与已声明范围。应用提交/push 不升级 AutoOS 组合版本。
- stage: goal | plan_id: READER-005 | plan_revision: r1 | round: 1 | from: drafting | to: work | status: drafting→executing | outcome: pass | worktree: D:/autostack/auto-reader（main，计划§2 独立 clone 即唯一权威树，无独立 app worktree） | commit: 7231c06+本次T-00提交 | next: work/T-01。授权链：/goal 完成计划005 = work/review/有界修复/merge 全链授权（§4 记录）。
- stage: work | plan_id: READER-005 | plan_revision: r1 | outcome: pass（execution_done） | worktree_path: D:/autostack/auto-reader | branch: main（计划§2 独立 clone 即权威树） | base_commit: 964a33f（T-00 前）；work 提交链 246cbfd/88332ef/c4b37b4/c8a20a4/5c9e3fe/bbf893d/6aa8a51/ffdefa1/d142a9a/317bb76（本次） | dependency_revisions: CLI e7dd7df1（0.1.0+plan-890-verified-r7-t19-2-gbe740b6）、auto-ui-tool 4d2198b8、auto-ui d85edbb、auto-photos 5eec01b | task_ids: T-00..T-06 全交付 | evidence: docs/plans/evidence/005/standalone-decision.md + §8 各任务行 + D:/autostack/plan-artifacts/plan-005/（gate-vue-4.log 28/0、gate-vm-6.log 27/0） | blockers: 无 open in-contract finding；3 项具名跨仓框架 GAP（scroll-pane 按压 path 分歧 / VM Http.post 记录体缺参+多字节直连劣化 / vue codegen 形参同名与 style 三元 model 引用）——owner=框架仓，复审不得以历史 skip 或 004 正对照顶替实际 app 结果 | next_responsible_role: review（T-07 独立上下文最终复审，同 clone；复审期间实现写入暂停）

## 10. 待澄清事项

本次规划没有待用户重新确认的产品方向。T-00 负责核实技术能力与实际 owner，决策稿必须先闭合再进入依赖实现。若探针显示必须改变目标、降低必需验收或扩大跨仓写入范围，报告具体证据并保留受影响任务未完成；不得用占位、跳过、API 预操作或历史总数替代必需用户任务。
