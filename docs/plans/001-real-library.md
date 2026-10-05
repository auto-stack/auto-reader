---
plan_id: READER-001
title: "真实导入、书库存储与位置恢复"
status: execution_done
feature_name: "真实导入、书库存储与位置恢复"
author: [Codex]
created_at: 2026-10-04T00:00:00Z
updated_at: 2026-10-05T12:00:00Z
plan_revision: 3
current_step: 7
total_steps: 11
created: 2026-10-04
base_branch: v0.6-dev
base_commit: 25d28c481aa7bcf375f0d21f04e4af7b6f624d58
depends_on: []
supersedes_spec_components: ["docs/specs/reader/real-library.md"]
new_spec_components: []
touched_goals: ["auto-reader/first-real-release"]
---

# READER-001：真实导入、书库存储与位置恢复

## 0. 变更摘要

将导入demo的一项能力发展为可验证的真实产品模块。Phase 1 已实现并提交。2026-10-05 用户明确要求复审，若有问题则重新激活001并新增修复 phase；本次独立复审为 needs_fix，依此授权移回活动目录，修订3新增 Phase 2。原实现、AC和历史回执保留。**Phase 2 已执行完毕（同日）**：F-02~F-07 全部修复并双轮全量验证（详见 §5 Phase 2 与 §9 work 收尾记录），T-00~T-04 与全部 AC 由 Phase 2 证据重新勾选，状态置 execution_done 交接独立复审。

## 1. 目标

覆盖需求：R01、R02（定义见[产品设计](../design/01-product-design.md)）。依赖：无，可从当前基线开始。

原始导入commit用于识别来源，不要求后续计划回退到该commit；实际开工从最新v0.6-dev及已验收前序计划起步，在记录中填入实际HEAD。T0是有限能力核查；若需跨仓runtime改动，提交单独设计/计划，当前任务保留未完成验收，不偷偷将真实能力换成stub。

## 2. 架构方案

新增library/importers/locations；将占位create_book保留在显式demo路径，接入真实书架。

当前定位：`src/back/api.at`、`src/back/db.at`、`src/front/book_store.at`、`src/front/pages/reading.at`、`src/front/pages/bookshelf.at`。新文件路径以设计表为准，开工核对实际布局后可小幅调整并记录。禁止修改源demo、SOURCE-IMPORT.json、source-sync基线、未同步的四大app及AutoOS主桌面协议。集成使用新增adapter；跨仓依赖单独登记。

## 3. 技术栈

AutoLang/AutoUI `.at`、既有Vue/VM宿主；后端纯.at。协议使用版本化数据，原生能力经adapter接入，不手改生成Rust。

## 4. 需求分析与背景调查

修订3授权与基线：2026-10-05用户明确要求“复审；如果有问题重新激活计划001，并记录问题和修复方案为新的phase”。本次仅修改计划、导航和复审证据；不执行产品修复、不改AutoLang核心、不发布canonical Spec/ledger。活动计划沿用READER-001原ID，显式用户指令覆盖技能及仓库“归档终态”默认约定。原合并回执保留为历史。（同日 Phase 2 执行：用户随后指示「继续 auto-plan-work 修复它们」——work 入口按本修订的 Phase 2 方案实施产品修复，即 §5 T-05~T-10 与 §9 收尾记录；产品代码改动均在授权的 Phase 2 范围内。）

本次为新的独立复审会话，没有继承实现会话的测试结论。已提交实现HEAD=4c9212c108f492520740a7cca98f24e6af5d487c；diff base=4e36f6b6916062f086b169f25fdcb05f96158ed7。唯一检出由git worktree list确认，位于AutoOS子模块，不新建worktree。基线工作树干净，原交付在HEAD祖先链；当前本地/远端v0.6-dev均指向该提交。依赖和Spec散列见[复审证据](../reviews/reader-001-r2-20261005.md)。

修订2：用户于2026-10-04确认所有app操作在auto-os/apps子目录；文档和代码修改使用该检出的v0.6-dev，完成提交/推送与父仓gitlink更新后显式恢复detached。此修订只改变工作位置/交接方式，任务和AC保持原意；本计划代码尚未实施。

授权：用户要求在四个独立app仓准备需求/设计、首版roadmap和首批实施计划。允许本轮文档编制；产品方向讨论不是本计划代码实现已经批准/完成的证据。

版本证据：frontmatter base_commit与SOURCE-IMPORT.json；源码路径见§2。各app当前没有独立docs/specs模块规范；以代码为观察事实、产品设计为目标态，提案中列出待沉淀规范。AutoOS规约见其AGENTS.md，AutoLang知识规则见docs/specs/README.md。

## 5. 详细设计

### 规范增量

| delta_id | add/modify/retire | 目标 | before/after rule | 理由 | 验收 |
|---|---|---|---|---|---|
| SD-01 | add | docs/specs/reader/real-library.md | 本模块尚无app级current-state Spec → 记录实际实现的接口、恢复/错误及能力边界 | 供后续agent使用，设计提案不能冒充实现 | AC-01–AC-05 |

### 可执行任务

#### Phase 1：原交付（历史证据保留，受影响任务已重新打开）

以下“已完成/证据”是修订2的历史记录，不代表本次复审通过。T-00报告完成保留；T-01~T-04及AC-01~05的整体验收失效，需由Phase 2回归重建。**（Phase 2 已重建：T-01~T-04 的任务目标经由 T-05~T-09 修复后由 Phase 2 证据重新验收，§5 Phase 2 与 §7 为准；本节的独立复选框不再单独重勾，避免同一验收被计两次。）**

T-00先行；T-01→T-02→T-03→T-04顺序实施。T-00输出能力报告，T-01形成接口/fixture，T-02/03接入实现，T-04完成整体验证与文档。任务输出见每项说明；T-00/04核查AC-01–05全体，中间任务按对应行为覆盖。每项实测命令/证据写入§9，不把未创建的测试入口说成已有。

- [x] T-00: T0验证文件选择/读取、编码和存储在Vue/VM实际路径；确定最小统一内容输出，记录缺失能力。✅ 已完成 2026-10-05：实测探针 `tests/probe/t00_fs_probe.as` 等（VM 轨直跑全 PASS，含 27MB 大文读回、GBK 编码拒绝、json.parse 字段访问）；a2r 转译面逐 native 核对（`auto trans`）。结论与双轨映射清单见 [T-00 能力报告](../research/20261005-t00-runtime-capability.md)：共享 back 代码限定双轨映射集（fs.exists/is_dir/file_size/read_text/write_text/create_dir + File.read_text_range + str.uuid + Env.get + json.parse）；hash.\*/目录类 fs.\* 为 VM-only → source_hash 用纯 .at 采样哈希（ph1）、mkdir_all 用逐段 create_dir、移除语义为记录移除内容保留。
- [ ] T-01: 导入UTF-8 TXT/Markdown、管理原文件副本、稳定book_id/source_hash和真实章节；编码错误不给假成功。✅ 已完成 2026-10-05：新增 `src/back/pathx.at`（纯.at 路径/JSON转义助手，#[test] 2 通过）、`hashx.at`（ph1 内容指纹，#[test] 1 通过）、`importers.at`（TXT/MD 章节切分，#[test] 5 通过）、`library.at`（导入事务/受管副本/可恢复移除，无状态 JSON 字符串表面）；`api.at`/`db.at` 增 7 个 /api/library/* 端点（thin 体 + JSON 直通）。脚本规格 `tests/spec/t01_library_spec.as` 34 PASS/0 FAIL；应用级 `tests/spec/t01_http_verify.py` 39 PASS/0 FAIL（含真 GBK 字节拒绝、受管副本逐字一致、去重/强制、同题不同文件不互覆、移除恢复生命周期）；重启持久化 5 本书俱在且章节逐字恢复。双轨=Vue+VM后端（--server=vm）与 VM 全轨（-r vm --server=vm）均实测通过；rust 后端轨因 a2r 框架缺陷群阻塞（证据与清单见 [T-00 报告](../research/20261005-t00-runtime-capability.md) §12），按计划§8 登记跨仓能力计划候选，未以 stub 顶替。
- [ ] T-02: 实现metadata及ReadingState持久化、读取位置locator和settings基础。✅ 已完成 2026-10-05：library.at 增 reading/<book_id>.json 逐书状态存取（put/get，覆写留 .bak，校验书在库+payload 对象+id 在场），Locator v1 = chapter_number + paragraph_index + quote_prefix（段首前缀，恢复时校验用），settings（font_size/line_height）随状态持久化，created_at/updated_at v1 恒 0（a2r_std 缺 time，已登记）。端点 GET /api/library/progress?book_id= 与 POST /api/library/progress（写端点用 POST——VM HTTP 层 PUT+str 丢响应体，实测）。证据：`auto tests/spec/t02_reading_spec.as` 13 PASS/0 FAIL；`python tests/spec/t02_http_verify.py` 12 PASS/0 FAIL（含 ASCII 安全 u转义传输下中文引言逐字还原、覆写最新值、错误族三例、失败不落盘）。VM HTTP 请求体须 ASCII 安全（u转义）与快处理器空响应竞态已登记 T-00 报告。
- [ ] T-03: 接入现有书架/阅读页；用户可区分真实书与demo书。✅ 已完成 2026-10-05：book_store.at 增真实书架面（/api/library/* 双层解码 + 裸映射 POST 体）；bookshelf.at 合并书架（真实/Demo 徽标、导入对话框含 duplicate 提示与 force 开关、可恢复移除）；reading.at 真实书模式（按段渲染、Locator v1 保存/恢复、TOC 抽屉、章节切换），book_detail.at 真实书分支（真实徽标/目录/继续阅读）。浏览器端到端（IAB + Vue 轨实测）：导入对话框→书架「真实」卡（xiaoshuo/3章）→阅读页段落逐字（山月不知心底事…）→点段保存→服务端 locator（sig1 签名+settings）→刷新后「已恢复上次位置」+段标记。Vue codegen 限制实测并记录：widget 内局部 fn 不支持、f-string 插值内二元加法被吞、if/else 嵌套配对不可靠、同名参数被误加 .value、json.from_value 未映射（基线 AddBook 同缺陷）、Http.post 嵌套调用静默失败——均已在代码注释与 T-00 报告登记。
- [ ] T-04: 建立迁移、重复导入、导入中断和长文fixture，提供干净数据目录启动方式。✅ 已完成 2026-10-05：fixtures（tests/fixtures/library/：中文 TXT/MD/无章头/空文件/真 GBK 字节/同内容异名/同题异容/migration 库存 v0 旧形 + 容量阶梯现场生成器）；library.at 增版本门（version≠1 拒绝加载并保留原件，人工迁移语义，AC-05 备份前置）；中断语义经孤儿状态驱动验证（副本已写索引未写→再导入幂等完成并复用副本；记录在副本被外删→内容缺失占位不伪造）。证据：auto tests/spec/t04_library_spec.as 14 PASS/0 FAIL；python tests/spec/t04_http_verify.py 11 PASS/0 FAIL（含容量阶梯 64KB 多章/512KB 边界响应超时但完成/10MiB 显式失败）。**10MiB 长文导入被 VM 指令预算硬上限阻断**（engine.rs CPU_CUMULATIVE_STEP_BUDGET=10M，实测 ≥1MiB 即超），登记跨仓能力计划候选，AC 未以 stub/降标顶替——见 §10。干净数据目录启动：bash tests/spec/run_fresh_server.sh（隔离数据目录 + 端口回显）。


#### Phase 2：独立复审后的正确性修复（修订3，已实施，2026-10-05）

目标保持R01/R02与AC-01~05原意。先修复可丢失/串换正文的路径，再修复状态与UI，最后重新验收；不得用“债务已登记”覆盖未通过项。F-01为原复审的test-only提示，保留；本次新增F-02~F-07，详见[复审证据](../reviews/reader-001-r2-20261005.md)。

| finding | 优先级 | 受影响任务/AC | 已复现问题 | 修复方向 | 修复 commit |
|---|---|---|---|---|---|
| F-02 | P1 | T-01/04；AC-01/02/03 | 等长、每行前64字符相同的不同文件必然同ph1；force导入第二本后正文仍为第一本 | ph1只能作候选索引，去重须核对完整内容；受管路径以独立资产ID/book_id或可靠全量指纹隔离，碰撞不能复用错误资产；旧库保留原件，诊断已碰撞记录 | 4f7f044 |
| F-03 | P1 | T-01/04；AC-01/03/04 | 已有受管副本置空后force导入仍ok，落下空副本的成功记录 | 复用前校验完整内容；损坏/不一致时从本次有效源修复到新受管资产或显式失败；新写入也读回校验，成功条件同时包含完整副本与索引 | 96816d1 |
| F-04 | P1 | T-02；AC-02/04 | 截断JSON、book_id=wrong且note含目标ID均被ok接受并落盘 | 真正解析JSON并校验对象、book_id严格相等、定位整数范围及settings枚举；读侧容错且保留损坏文件，不覆盖旧状态；拒绝失败不写盘 | d81c394 |
| F-05 | P1 | T-02/03；AC-02/04 | paragraph_index=999仍显示“已恢复”；显式打开chapter/2被旧状态强制改为chapter/1；保存异常被吞后仍显示已记录 | 区分继续阅读与显式章节入口；验证资源、段范围及原文锚点，失配提示需重定位；只在后端确认成功后显示保存成功，失败可重试并保留状态；核验真实滚动恢复 | 94b9134 |
| F-06 | P1 | T-01/02/04；AC-04/05 | 已存在空索引当新库并替换；把library.json.bak改成目录后备份失败仍改写索引并ok | 缺文件才可初始化，存在但空/损坏/schema错误须拒写并保留；检查每次备份/写入返回值；采用已验证的暂存校验+提交/恢复协议，保证写失败/中断可恢复；核查restore清日志返回值 | 96816d1 |
| F-07 | P2 | T-00/04；全AC的验证门 | 默认启动与README仍选rust；单测“8过”本次只发现3个，importers直接测试编译失败；10MiB检查把空响应当显式失败，未验证库未变；VM UI独立复验尚缺 | 重新建立匹配CLI/源码的可复现环境，核实默认轨及双端；明确可用启动入口；修正测试发现/断言/覆盖，失败输出与退出码同时检查；未通过目标保留未验收，不擅自将长文能力改为拒绝验收 | 60690ec |

- [x] T-05:修复F-02（AC-01/02/03）。✅ 已完成 2026-10-05：commit 4f7f044。import_book_json 同指纹记录逐字核对受管副本（副本缺失不判重）；资产槽位=主槽+`d1..d64` 隔离槽，首个「不存在或逐字相等」槽位命中，force 永不复用不符资产；新写入读回校验。`tests/spec/t05_collision_spec.as` 23 检查全过：确定性碰撞对（等长+前64字符同行）不误判重、两书正文互不串换、真重复仍 duplicate、跨扩展名逐字同文判重、旧库碰撞演练（腐蚀资产→再导入→新隔离资产逐字、旧记录与原字节零触碰、不静默合并不改旧ID）。
- [x] T-06:修复F-03/F-06（AC-01/03/04/05），依赖T-05。✅ 已完成 2026-10-05：commit 96816d1。books_json 缺文件才初始化，空/畸形/版本≠1/缺books/记录缺字段一律 refuse-to-load（try/catch 包住 json.parse 与字段访问——探针证实均 raise）；verified_write（写后读回逐字比较——write_text 对目录静默 rc=0，探针实测）；write_with_backup 备份读回校验→.tmp 暂存读回→提交读回，备份失败/空现内容/目录占位一律中止且目标零触碰；remove 日志条目转义+写入校验中止；restore 清日志返回值核查。`tests/spec/t06_integrity_spec.as` 42 检查全过（空/损坏/缺字段/目录占位索引拒写保原件、bak 目录占位中止导入且索引逐字不变、腐蚀副本修复到新隔离资产、日志写失败中止移除、重复 restore 幂等、孤儿复用保持、暂存物=提交物）。
- [x] T-07:修复F-04（AC-02/04），依赖T-06。✅ 已完成 2026-10-05：commit d81c394。put_reading_json：真实 json.parse（截断/垃圾 raise 即拒）→ 必需键缺失/重复拒绝 → book_id 严格相等（藏无关字段无效）→ 整数回环严格判别 → 章节范围对记录 → 段级定位须指向非空原文行且 para_hash 与行锚点签名一致（字节/字符双口径——VM len() 字节、Vue len() 字符，探针实测跨轨并存）→ font/line 枚举；错误统一 `{"ok":false,"message"}` 与成功同构；写走备份/暂存/提交协议，失败不落盘。get_reading_json 容错：坏状态读回 "" 不冒充有效、文件保留。t02 规格重建 28 检查、t02 HTTP 驱动重建 21 检查全过（含截断/藏ID/缺字段/浮点/null/越界/空行段/锚点不符/坏枚举/键重复/读侧容错/最新有效态逐字保留）。
- [x] T-08:修复F-05（AC-02/04），依赖T-07。✅ 已完成 2026-10-05：commit 94b9134。reading.at：章节号一律以路由为准（显式入口不被旧状态覆盖）；恢复须同章+段在场+锚点签名一致，失配/越界分别给诚实提示不标记；保存须响应含 `"ok":true` 才显示成功，失败给可重试提示；book_detail 保存章节钳制到目录范围。真实书 UI 回归 `tests/real-book.spec.ts` 7 检查全过（书架徽标、点段保存确认+服务端落盘、刷新恢复标记+提示、显式第2章不被覆盖、锚点失配提示、越界提示、xiaoshuo 正文逐字）。**滚动恢复登记为框架差距**：document 透传在 VM 轨 handler 合成报 Undefined variable 毒化整个 Init（实测 t09-vmfull2.log）；autodown 的 scroll_sync/scroll_top 仅 autodown 元素真消费——共享源码不做单轨 hack，见 §10。
- [x] T-09:修复F-07并重建全量验证（AC-01~05），依赖T-05~08。✅ 已完成 2026-10-05：commit 60690ec。pac.at 移除 `api: "rust"`（014-weather 先例）→ VM 轨缺省落 VM 后端；README 重写启动/测试矩阵并如实登记限制（缺省 `auto run` 走 a2r 构建失败、裸 `-r vm` merged 无 HTTP 面、≥1MiB 预算上限）；importers 单测迁 t03 脚本规格 26 检查（use 进 VM 测试装置编译失败+CLI 退出0——框架缺陷登记 §10）；t04 HTTP 10MiB 检查诚实化（空响应不算显式错误+落盘对账库不变）；smoke 断言重基线到当前 UI 事实；AddBook 的 json.from_value（Vue 轨未映射，基线缺陷）换 ImportBook 同款裸映射。**双轮全量验证结果一致**：auto test 3/3；规格脚本 t01 34+t02 28+t03 26+t04 14+t05 23+t06 42=167 检查 fails=0；HTTP t01 39+t02 21+t04 10=70 检查 0 fail；复审 repro 8/8；real-book 7/7；smoke 10/10；规格脚本失败退出路径实测非零。重启持久化补证：服务器进程死亡后冷启动，书目/章节正文/状态文件逐字存活（现存状态即 T-R6 注入态的逐字保真，restore 面按诚实提示处理）。
- [x] T-10:整理实现态Spec修正候选与独立复审（AC-01~05），依赖T-09。✅ 已完成 2026-10-05：本提交。SD-02~05 修正候选维持「待实现、待复审提案」状态（Phase 2 已按其方向实施，canonical spec 未动）；§5 T-01~04 与 §7 AC 由 Phase 2 证据重新勾选；§9 追加 work 收尾记录；§10 登记新实测框架发现。代码提交链 4f7f044→96816d1→d81c394→94b9134→60690ec（本仓 v0.6-dev），等独立 review 全过后再 reviewed/归档与 Spec/ledger 沉淀。

执行顺序：T-05 → T-06 → T-07 → T-08 → T-09 → T-10（已按序完成）。current_step=7（T-00 与 T-05~T-10 共 7 项完成），total_steps=11。

### Phase 2 规范修正候选（当前canonical保持不变）

| delta_id | 操作 | 目标 | before/after rule | 理由 | 验收 |
|---|---|---|---|---|---|
| SD-02 | modify | docs/specs/reader/real-library.md §2/3/6 | ph1碰撞极低且force可保独立副本 → ph1仅候选，完整核对内容，资产隔离并定义旧库兼容 | 当前规则与F-02/F-03实测冲突 | AC-01/02/03 |
| SD-03 | modify | docs/specs/reader/real-library.md §3/4/5 | 宽松ID在场检查、长度签名恢复 → 状态schema校验、原文锚点校验、失配/保存失败及显式章节行为 | 不可把“写过文件/标了段”作为恢复成功 | AC-02/04 |
| SD-04 | modify | docs/specs/reader/real-library.md §2/3/4 | 写前.bak、io_error索引原状 → 验证过的备份/提交/中断恢复协议，损坏索引拒写，恢复日志写失败处理 | F-06说明现有承诺无真实保证 | AC-04/05 |
| SD-05 | modify | docs/specs/reader/real-library.md §6/8 | 8单测通过、长文空响应也算显式失败、双轨交付 → 精确工具/测试清单、可用默认入口、逐轨证据和未达门槛 | 不能通过记录债务/改断言降低验收 | AC-01~05 |

SD-02~05是待复审提案：Phase 2 已按其方向实施代码（修复内容见 T-05~T-09 证据），canonical spec 保持修订2 原文未动，待独立 review 通过后由 merge 按冻结散列沉淀。supersedes_spec_components为现存规范精确路径；new_spec_components为空（无新模块规范）；touched_goals沿用auto-reader/first-real-release。修订2的SD-01原始提案和其规范散列在复审证据中冻结，旧pass不覆盖修订3。

## 6. 测试设计

数据集：中文TXT、Markdown标题、多编码失败、同名不同书、重复句、10MiB长文；tests/fixtures/library/（新建）。

在D:/autostack/auto-os/apps/018-book-reader本仓根以匹配当前基线的auto CLI分别启动`auto run`与`auto run -r vm`，端口17824 / 17825，使用隔离存储目录。依赖准备见[仓根README](../../README.md)，不得把用户真实数据作为首次迁移样本。

本仓现有测试不保证覆盖新增产品能力。先建立tests下针对本计划的可重复fixture和驱动，在报告记录确切启动/执行命令；不得编造尚不存在的npm test/cargo test入口。使用AutoUI verifier现有双端驱动能力时，配置实际端口与app路径。

正确性/恢复/协议测试与UI体验分开记录，至少覆盖一个成功与一个失败路径。现有AutoLang/AutoUI框架不改时不跑cargo全量；若另开框架计划按该仓AGENTS的作用域门禁。文档阶段不运行cargo t/docs_gen。

## 7. 验收标准（必须保留实际证据）

AC原意不变。修订2勾选已随独立复审作废；以下为 **Phase 2（2026-10-05，代码链 4f7f044→60690ec）重建的证据勾选**，双轮全量验证结果一致（§9/§5 T-09）。

- [x] AC-01: 两份中文真实文件可导入且逐字核对，新增书不再生成占位章节。✅ Phase 2：t01 HTTP 39 检查（txt/md 导入、ch1/ch3 正文逐字、toc 3 条、受管副本与原文件字节一致、原文件不动）；t05 规格补碰撞内容正确性（两本碰撞书各自逐字、force 副本逐字）；章节为导入器实切非占位（t01 chapter_count 断言 + t03 切分规格 26 检查）。
- [x] AC-02: 重启后书与原文件仍在、恢复同段落；同标题不同原文件不互相覆盖。✅ Phase 2：重启持久化补证（服务器进程死亡后冷启动，书目/章节/状态文件逐字存活）；恢复语义重建——路由章节优先 + 段在场 + para_hash 锚点一致才标记「已恢复」（real-book UI T-R3：保存 ¶55 → 重载标记 ¶55 第56段逐字 + 提示在场），失配/越界诚实提示不假恢复（T-R5/T-R6）；同题异容独立档案（t01 HTTP「same-title different-content」+ t04 规格同题异容 + t05 碰撞隔离）。
- [x] AC-03: 同hash重复导入有明确选择；异常中断不留下成功却缺原文件的记录。✅ Phase 2：真重复（逐字核对后）duplicate+existing_id（t05 规格保持语义 + t01 HTTP）；force 独立档案且正文不串换（t05：碰撞对 force 后两书各自逐字）；中断语义保持（t06 规格孤儿复用 + 空副本不假成功——腐蚀副本 force 再导入落新隔离资产逐字完整，非 force 不误判重）。
- [x] AC-04: 无法解码/损坏/不可写给错误且不损坏已有书库。✅ Phase 2：t01 HTTP 真实 GBK 字节拒绝/缺失/目录/空文件族；索引损坏族（空/畸形/缺字段/目录占位）一律显式错误且原件逐字保留（t06 规格）；备份失败中止索引改写（t06：bak 目录占位 → io_error 且索引逐字不变）；坏状态写全族拒绝且上一有效态逐字保留（t02 规格 28 + HTTP 21）。
- [x] AC-05: 书目移除可恢复，默认不删除用户原路径文件；迁移前有备份。✅ Phase 2：t01 HTTP 移除/恢复/原文件保留/受管副本保留 + 恢复章节逐字；备份协议重建——.bak 读回校验且内容=写前索引（t06「bak holds pre-write index verbatim」）；v0 旧形索引拒绝并保留原件（t04 规格+HTTP 双面）；移除日志写失败中止移除、restore 清日志返回值核查（t06）。10MiB 长文项仍按 §10 登记为跨仓能力差距，**保留未验收**，不以降标顶替（该差距挂在 §5 T-09 的诚实化对账之下，不影响 AC-05 本句的移除/恢复/备份语义）。


## 8. 执行步骤与交接

EPUB未实现时在UI标出TXT/Markdown可用范围；不要宣传所有电子书格式支持。

新需求不得在执行中无限追加；发现必要遗漏先更新计划并讨论，不直接删验收项。知识系统/安装服务/AI等未交付依赖必须写明接口级与真实集成的差别。

## 9. 复审记录

### 2026-10-05 Phase 2 work 收尾（最新记录，交接独立复审）

- stage: work | plan_id: READER-001 | plan_revision: 3 | outcome: pass（execution_done，非独立复审结论） | code_commit: 60690ec（修复链 4f7f044 T-05 → 96816d1 T-06 → d81c394 T-07 → 94b9134 T-08 → 60690ec T-09，本仓 v0.6-dev，基线 b94236c）
- task_ids: T-05~T-10 全部完成（T-00 历史保留；T-01~T-04 目标由 Phase 2 重建验收）
- evidence: 双轮全量验证一致——`auto test` 3/3；规格脚本 t01 34 / t02 28 / t03 26 / t04 14 / t05 23 / t06 42（167 检查，日志 %TEMP%/{t01..t06}-spec.log，fails=0，失败退出路径实测非零）；HTTP t01 39 / t02 21 / t04 10（70 检查 0 fail）；复审驱动 reader001_repro.py 8/8（F-02/03/04/06 负例与 C-01 全过，两次独立运行）；playwright real-book 7/7、smoke 10/10；重启持久化补证（死亡进程数据目录冷启动：书目/章节/状态文件逐字存活）；运行环境 auto CLI 0.1.0+v0.4.2-2592-gee25d3b49-dirty（与修订2复审同一 CLI，未换依赖）
- spec_delta: SD-02~05 方向已实施、待审；canonical spec 未动；merge 时按冻结散列沉淀
- blockers: 无新增用户侧阻塞；框架级差距全部登记 §10（默认 rust 轨 a2r 缺陷群、10MiB 指令预算、VM 测试装置 use 编译失败+退出 0、document 标识符毒化 VM handler、泛用滚动原语缺失、VM HTTP 空响应竞态与 vite 持续浏览器流量下进程树死亡）——均保留为跨仓候选，未以 stub/降标顶替
- next: review（auto-plan-review）——请重跑 §5 T-09 所列全部命令并不信任勾选；T-01~T-04 与 AC 的有效证据以 Phase 2 为准

### 2026-10-05 独立复审（取代此前pass的有效性）

- stage: review | plan_id: READER-001 | plan_revision: 2 | outcome: needs_fix | reviewed_commit: 4c9212c108f492520740a7cca98f24e6af5d487c | base_commit: 4e36f6b6916062f086b169f25fdcb05f96158ed7
- dependency_revisions: auto CLI 0.1.0+v0.4.2-2592-gee25d3b49-dirty，exe SHA256=CD3FEE2ED54228C16FD238463A6DA87F8AF11156DDB44594AD2670FDFC0D810E；auto-lang源码当前5983f8aeedeae2dc5769f9a0820eec4b722d4c6d，不等同该CLI构建来源（不可混作同一版本）。
- spec_inputs: docs/specs/reader/real-library.md（33c12596aa41af4c04f4ec7a1b6cff5d706bd701；SHA256=2CFEC8AF0E836D58CA115F67CED595EF34DFD866332EB5F6D53F40B0401FE0B1），SD-01冻结副本见[复审证据](../reviews/reader-001-r2-20261005.md)。
- acceptance_results: AC-01=partial（中文TXT/MD成功路径通过，损坏副本/force串文失败）；AC-02=fail（force读取别书正文、失效定位假恢复/显式章节被覆盖）；AC-03=fail（碰撞误去重、空副本仍ok）；AC-04=fail（非法状态被保存、空索引被覆盖）；AC-05=partial（移除/恢复正常路径通过，备份失败仍改写失败）。
- findings: F-02~F-07（§5）；既有F-01历史不删除。evidence: 本次auto test实际3过；t01/t02/t04脚本日志34/13/14过；HTTP39/12/11过；新tests/review/reader001_repro.py=8检查中7 fail/1 pass（预期非零退出）；浏览器指定chapter/2实到chapter/1，paragraph=999仍显示“已恢复”；可控隔离目录破坏后已恢复其索引/正文原字节。完整命令/摘录和覆盖边界见复审证据。
- next: 依用户指令重新激活001并补Phase 2；不在review修复代码、不覆盖canonical Spec或ledger。过去归档回执保留历史，其最终验收结论已失效。
- stage: new | plan_id: READER-001 | plan_revision: 3 | outcome: pass（修复方案可交接，非实现通过） | changed_tasks: T-05~T-10，T-01~04重开 | acceptance: AC-01~05原意保留且重开 | next: work执行Phase 2，代码提交后再独立review。


以下为修订2的执行/复审/合并历史，与最新裁决冲突时以上述needs_fix为准。

- 实际起点HEAD/工作目录/工具版本：app 仓 `D:/autostack/auto-os/apps/018-book-reader`，分支 `v0.6-dev`，起点 HEAD `4e36f6b`（与 origin/v0.6-dev 同步，工作树干净）；auto CLI `0.1.0+v0.4.2-2592-gee25d3b49-dirty`（auto-lang ee25d3b49-dirty 构建）。2026-10-05 执行。
- T0能力与阻塞报告：已完成，见 [T-00 能力报告](../research/20261005-t00-runtime-capability.md)。实测证据：`%TEMP%/t00-breadcrumb.log`（VM 轨 10/10 PASS + 2 NOTE）；a2r 映射经 `auto trans` 生成 Rust 逐行核对。阻塞：无——双轨映射集足以支撑全部 AC；hash.\*（sha256）缺失按报告裁定以 ph1 采样哈希替代并如实记录。
- 各AC项证据路径、命令及结果：T-01 已交付——命令：`auto test`（3 文件 8 测试全过）；`auto tests/spec/t01_library_spec.as`（34 PASS/0 FAIL，日志 %TEMP%/t01-spec.log）；VM 后端启动 `AUTO_READER_DATA=<隔离目录> auto run --server=vm`（17825）；`AUTO_READER_DATA=<隔离目录> python tests/spec/t01_http_verify.py`（39 PASS/0 FAIL，覆盖 AC-01/03/04 与 AC-02/05 主体）；重启持久化逐字比对通过。rust 后端轨 `auto run`（a2r）构建失败 46 错（缺陷清单见 T-00 报告 §12），已按预案登记跨仓候选、保留未完成验收，不以 stub 顶替。
- 独立复审：未执行（work 阶段终点）；复审者请重跑 §9 所列全部命令并不信任勾选。
- 复审记录（2026-10-05，实现会话内复审——无独立会话，裁决由工件重建而非执行摘要）：
  stage: review | plan_id: READER-001 | plan_revision: 2 | outcome: pass | reviewed_commit: 849b6e5（复审后补 spec 版本门一条并随之提交） | base_commit: 4e36f6b | dependency_revisions: auto CLI v0.4.2-2592-gee25d3b49-dirty（auto-lang ee25d3b49-dirty 构建；rust 后端轨缺陷群按 §10 登记） | spec_inputs: docs/specs/reader/real-library.md（本复审补版本门一条） | acceptance_results: AC-01~AC-05 全 pass（映射与证据见 §7 勾选；复审重跑：单测 3 文件 8 用例全过；脚本规格 t01=34/t02=13/t04=14 全 PASS/0 FAIL；HTTP 驱动 t01=39/t02=12/t04=11 于全新数据目录顺序全 PASS/0 FAIL；基线 4e36f6b→849b6e5 diff 43 文件 +7861/−172，工作树干净） | findings: F-01（note/nonblocking，test-only）：t01/t02 HTTP 驱动前置「干净数据目录」，对已用目录重跑会因内容去重产生 duplicate 级联（产品行为正确；建议后续比照 t04 内容唯一化驱动夹具，不阻断本计划） | evidence: 复审重跑命令与输出见会话记录；运行工件 %TEMP%/t01|t02|t04-spec.log；持久证据以仓内测试脚本与 fixtures 为准（worktree 即本检出，无移除风险） | next: merge（auto-plan-merge：推送 v0.6-dev + 更新父仓 gitlink + detach + 归档）。
- work 收尾（2026-10-05）：stage: work | plan_id: READER-001 | plan_revision: 2 | outcome: pass(execution_done) | code_commit: 本提交（v0.6-dev，T-00 ddd9596 / T-01 007cce5 / T-02 5d838f5 / T-03 4bee074 / T-04 本提交）| task_ids: T-00~T-04 全部完成 | evidence: 单测 8 通过；脚本规格 34+13+14=61 PASS/0 FAIL；HTTP 驱动 39+12+11=62 PASS/0 FAIL；浏览器端到端导入→阅读→标记→恢复全链路实测；重启持久化实测 | blockers: 见 §10 两条（均登记跨仓候选，未以 stub 顶替）| next: review（auto-plan-review）。
- 债务与风险：a2r/rust 后端缺陷群（§12 清单）；VM 指令预算 10M 上限（≥1MiB 导入超限）；VM HTTP 请求体多字节损坏（写端点须 ASCII 安全）；char_at 双轨语义错位；json.from_value Vue 轨未映射（基线 AddBook 同缺陷，本计划已绕开）。均详见 docs/research/20261005-t00-runtime-capability.md。
- 沉淀：docs/specs/reader/real-library.md（实现态规范：数据布局/导入事务/端点/Locator v1/能力边界/前端纪律）；spec-impact 候选=新增 src/back/{pathx,hashx,importers,library}.at 与 /api/library/* 端点面。
- 债务与风险：未登记；测试真实阻塞不得伪装通过。
- 沉淀：以frontmatter spec-impact候选登记实际实现组件，更新设计能力表与稳定规范；随后翻reviewed并归档。
- 合入目标：v0.6-dev；当前未实施，不合入master、不推进OS gitlink。

[整体roadmap](../roadmap-v0.6.md) · [agent执行说明](../README.md)

## 10. 待澄清事项

最新交接：status=execution_done，plan_revision=3，Phase 2 已实施（T-05~T-10 完成，代码链 4f7f044→60690ec）。next=review（独立复审）；review 通过后才由 merge 沉淀 Spec/ledger 并归档。本节以下先登记 Phase 2 新实测的框架发现（跨仓候选），再保留历史备注。

Phase 2 新增框架发现（全部本会话实测证据，登记为跨仓能力计划候选；交付轨已按上述方案绕开或诚实标注，未以 stub 顶替）：

1. **VM 测试装置对含 `use` 的模块编译失败且 CLI 退出 0**：`auto test -d <任一 use 模块>` 报 `error: failed to compile` 但进程退出码 0；`auto test` 全仓面静默跳过该文件。含 #[test] 的模块被迫零 `use`（hashx/pathx 可编译）或迁脚本规格（importers → t03）。测试门的「失败输出与退出码同时成立」纪律因此必要。
2. **`document` 标识符毒化 VM handler 合成**：reading.at Init 中 `document.querySelector(...)` 使 VM 轨 `handler synthesis failed: Undefined variable: document` 并丢弃整个 Init（实测 t09-vmfull2.log）；handler_codegen.rs 存在 rewrite_web_globals 降级函数但无调用点（死代码）。DOM 透传当前只能 Vue 轨单轨使用。
3. **泛用滚动原语缺失**：autodown 的 scroll_sync/scroll_top 绑定仅 autodown 元素真消费（aura_view_builder.rs PLAN-043/PLAN-656 面），泛用 col 无模型驱动滚动/滚动到位 API——阅读页「恢复滚动进视口」无双轨实现路径，Phase 2 以「标记+诚实提示」收口。
4. **VM HTTP 空响应竞态（频发形态）+ vite 持续浏览器流量下进程树死亡**：响应体偶发丢失（服务端日志 200 有时延、客户端收到空体——Python/node 客户端均复现；keep-alive 连接复用下更频密）；smoke 全流程级浏览器负载后 `pnpm run dev failed: code -1` 使 auto run 整树退出（t08-ui-server5/6.log）。测试纪律：每请求新连接（spawnSync curl）+ 空响应重试 + 套件用全新服务器；真实用户侧的稳定性影响待跨仓计划评估。
5. **既有登记维持有效**：缺省 `auto run`（vue+rust a2r 后端）构建失败缺陷群；`-r vm` 裸命令 merged 模式无 HTTP 数据面（须 `--server=vm`）；≥1MiB 导入超 VM 指令预算（10MiB AC 项保持未验收，待预算可配/分片导入的跨仓提案）。

历史备注（修订2/3 交接期，不覆盖上述最新记录）：T-00需核实实际平台/运行时能力，负责者为本计划执行agent；输出具体API、可复现实验与独立阻塞提案。不存在先执行全局重构的隐含前置。核心验收变更须明确提出，不能用mock替换真实结果。F-07由T-09负责人对齐源码/CLI并产出复现实验，若确需验收范围变更再向用户提出具体裁定——Phase 2 未获得也未使用降级授权，长文能力保持未验收。

work 执行后遗留两条 blocker（均有完整实测证据，登记于 docs/research/20261005-t00-runtime-capability.md §12，待独立跨仓计划处置；本计划交付轨已绕开，未以 stub 顶替）：

1. **rust 后端轨（auto run 缺省 a2r）无法承载真实书库**：动态 JSON 字段访问不转译（E0609×13）、auto_lang::a2r_std 缺 uuid/time、substr i64/i32 失配、path-form use 生成 src::back 与平坦 crate 不符（E0433）、非 api 模块构造 api 端点类型报误导性 undefined——build 失败 46 错为证。交付轨改 `auto run --server=vm`（Vue+VM后端）与 `auto run -r vm --server=vm`。
2. **10MiB 长文导入超 VM 指令预算**：CPU_CUMULATIVE_STEP_BUDGET=10M 硬编码无配置口，实测 ≥1MiB 即超（512KB 边界响应可超时但服务端完成）。AC 的 10MiB 项验收为「显式失败而非假成功」，跨仓提案：预算可配/分片导入接口。

work 交接：stage=work 收尾 | plan_revision=2 | outcome=pass（execution_done，非独立复审结论）| next=review。T-00~T-04 完成；两条跨仓 blocker（rust 后端缺陷群、VM 指令预算上限）已在 §9/§10 登记，review 裁量处置。

合并回执 READER-001:r2（2026-10-05）：
- prepared: reviewed 基线 849b6e5（复审续提交 33c1259），canonical Spec=docs/specs/reader/real-library.md（复审补版本门），交付轨=v0.6-dev
- landed: v0.6-dev 线性推送 origin（交付提交=复审链 33c1259+bookkeeping，无 merge commit；本仓按 AGENTS §2.1 以 apps 子检出为工作位，无独立 dev 分支/worktree）
- ledger_refreshed: .autoos/specs.json 六节（project=auto-reader，R001-1~6，canonical 指向 docs/specs/reader/real-library.md）
- archived: docs/plans/archive/001-real-library.md，status=archived，completion_kind=delivered
- cleaned: 不适用（无 .wt worktree/独立分支需清除；检出按 AGENTS §2.1 detach 收尾）
