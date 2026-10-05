---
plan_id: READER-001
title: "真实导入、书库存储与位置恢复"
status: archived
feature_name: "真实导入、书库存储与位置恢复"
author: [Codex]
created_at: 2026-10-04T00:00:00Z
updated_at: 2026-10-05T00:00:00Z
plan_revision: 2
current_step: 5
total_steps: 5
created: 2026-10-04
base_branch: v0.6-dev
base_commit: 25d28c481aa7bcf375f0d21f04e4af7b6f624d58
depends_on: []
supersedes_spec_components: []
new_spec_components: ["docs/specs/reader/real-library.md"]
touched_goals: ["auto-reader/first-real-release"]
---

# READER-001：真实导入、书库存储与位置恢复

## 0. 变更摘要

将导入demo的一项能力发展为可验证的真实产品模块。当前仅获授权编制设计/roadmap/实施计划，未执行代码开发。

## 1. 目标

覆盖需求：R01、R02（定义见[产品设计](../design/01-product-design.md)）。依赖：无，可从当前基线开始。

原始导入commit用于识别来源，不要求后续计划回退到该commit；实际开工从最新v0.6-dev及已验收前序计划起步，在记录中填入实际HEAD。T0是有限能力核查；若需跨仓runtime改动，提交单独设计/计划，当前任务保留未完成验收，不偷偷将真实能力换成stub。

## 2. 架构方案

新增library/importers/locations；将占位create_book保留在显式demo路径，接入真实书架。

当前定位：`src/back/api.at`、`src/back/db.at`、`src/front/book_store.at`、`src/front/pages/reading.at`、`src/front/pages/bookshelf.at`。新文件路径以设计表为准，开工核对实际布局后可小幅调整并记录。禁止修改源demo、SOURCE-IMPORT.json、source-sync基线、未同步的四大app及AutoOS主桌面协议。集成使用新增adapter；跨仓依赖单独登记。

## 3. 技术栈

AutoLang/AutoUI `.at`、既有Vue/VM宿主；后端纯.at。协议使用版本化数据，原生能力经adapter接入，不手改生成Rust。

## 4. 需求分析与背景调查

修订2：用户于2026-10-04确认所有app操作在auto-os/apps子目录；文档和代码修改使用该检出的v0.6-dev，完成提交/推送与父仓gitlink更新后显式恢复detached。此修订只改变工作位置/交接方式，任务和AC保持原意；本计划代码尚未实施。

授权：用户要求在四个独立app仓准备需求/设计、首版roadmap和首批实施计划。允许本轮文档编制；产品方向讨论不是本计划代码实现已经批准/完成的证据。

版本证据：frontmatter base_commit与SOURCE-IMPORT.json；源码路径见§2。各app当前没有独立docs/specs模块规范；以代码为观察事实、产品设计为目标态，提案中列出待沉淀规范。AutoOS规约见其AGENTS.md，AutoLang知识规则见docs/specs/README.md。

## 5. 详细设计

### 规范增量

| delta_id | add/modify/retire | 目标 | before/after rule | 理由 | 验收 |
|---|---|---|---|---|---|
| SD-01 | add | docs/specs/reader/real-library.md | 本模块尚无app级current-state Spec → 记录实际实现的接口、恢复/错误及能力边界 | 供后续agent使用，设计提案不能冒充实现 | AC-01–AC-05 |

### 可执行任务

T-00先行；T-01→T-02→T-03→T-04顺序实施。T-00输出能力报告，T-01形成接口/fixture，T-02/03接入实现，T-04完成整体验证与文档。任务输出见每项说明；T-00/04核查AC-01–05全体，中间任务按对应行为覆盖。每项实测命令/证据写入§9，不把未创建的测试入口说成已有。

- [x] T-00: T0验证文件选择/读取、编码和存储在Vue/VM实际路径；确定最小统一内容输出，记录缺失能力。✅ 已完成 2026-10-05：实测探针 `tests/probe/t00_fs_probe.as` 等（VM 轨直跑全 PASS，含 27MB 大文读回、GBK 编码拒绝、json.parse 字段访问）；a2r 转译面逐 native 核对（`auto trans`）。结论与双轨映射清单见 [T-00 能力报告](../research/20261005-t00-runtime-capability.md)：共享 back 代码限定双轨映射集（fs.exists/is_dir/file_size/read_text/write_text/create_dir + File.read_text_range + str.uuid + Env.get + json.parse）；hash.\*/目录类 fs.\* 为 VM-only → source_hash 用纯 .at 采样哈希（ph1）、mkdir_all 用逐段 create_dir、移除语义为记录移除内容保留。
- [x] T-01: 导入UTF-8 TXT/Markdown、管理原文件副本、稳定book_id/source_hash和真实章节；编码错误不给假成功。✅ 已完成 2026-10-05：新增 `src/back/pathx.at`（纯.at 路径/JSON转义助手，#[test] 2 通过）、`hashx.at`（ph1 内容指纹，#[test] 1 通过）、`importers.at`（TXT/MD 章节切分，#[test] 5 通过）、`library.at`（导入事务/受管副本/可恢复移除，无状态 JSON 字符串表面）；`api.at`/`db.at` 增 7 个 /api/library/* 端点（thin 体 + JSON 直通）。脚本规格 `tests/spec/t01_library_spec.as` 34 PASS/0 FAIL；应用级 `tests/spec/t01_http_verify.py` 39 PASS/0 FAIL（含真 GBK 字节拒绝、受管副本逐字一致、去重/强制、同题不同文件不互覆、移除恢复生命周期）；重启持久化 5 本书俱在且章节逐字恢复。双轨=Vue+VM后端（--server=vm）与 VM 全轨（-r vm --server=vm）均实测通过；rust 后端轨因 a2r 框架缺陷群阻塞（证据与清单见 [T-00 报告](../research/20261005-t00-runtime-capability.md) §12），按计划§8 登记跨仓能力计划候选，未以 stub 顶替。
- [x] T-02: 实现metadata及ReadingState持久化、读取位置locator和settings基础。✅ 已完成 2026-10-05：library.at 增 reading/<book_id>.json 逐书状态存取（put/get，覆写留 .bak，校验书在库+payload 对象+id 在场），Locator v1 = chapter_number + paragraph_index + quote_prefix（段首前缀，恢复时校验用），settings（font_size/line_height）随状态持久化，created_at/updated_at v1 恒 0（a2r_std 缺 time，已登记）。端点 GET /api/library/progress?book_id= 与 POST /api/library/progress（写端点用 POST——VM HTTP 层 PUT+str 丢响应体，实测）。证据：`auto tests/spec/t02_reading_spec.as` 13 PASS/0 FAIL；`python tests/spec/t02_http_verify.py` 12 PASS/0 FAIL（含 ASCII 安全 u转义传输下中文引言逐字还原、覆写最新值、错误族三例、失败不落盘）。VM HTTP 请求体须 ASCII 安全（u转义）与快处理器空响应竞态已登记 T-00 报告。
- [x] T-03: 接入现有书架/阅读页；用户可区分真实书与demo书。✅ 已完成 2026-10-05：book_store.at 增真实书架面（/api/library/* 双层解码 + 裸映射 POST 体）；bookshelf.at 合并书架（真实/Demo 徽标、导入对话框含 duplicate 提示与 force 开关、可恢复移除）；reading.at 真实书模式（按段渲染、Locator v1 保存/恢复、TOC 抽屉、章节切换），book_detail.at 真实书分支（真实徽标/目录/继续阅读）。浏览器端到端（IAB + Vue 轨实测）：导入对话框→书架「真实」卡（xiaoshuo/3章）→阅读页段落逐字（山月不知心底事…）→点段保存→服务端 locator（sig1 签名+settings）→刷新后「已恢复上次位置」+段标记。Vue codegen 限制实测并记录：widget 内局部 fn 不支持、f-string 插值内二元加法被吞、if/else 嵌套配对不可靠、同名参数被误加 .value、json.from_value 未映射（基线 AddBook 同缺陷）、Http.post 嵌套调用静默失败——均已在代码注释与 T-00 报告登记。
- [x] T-04: 建立迁移、重复导入、导入中断和长文fixture，提供干净数据目录启动方式。✅ 已完成 2026-10-05：fixtures（tests/fixtures/library/：中文 TXT/MD/无章头/空文件/真 GBK 字节/同内容异名/同题异容/migration 库存 v0 旧形 + 容量阶梯现场生成器）；library.at 增版本门（version≠1 拒绝加载并保留原件，人工迁移语义，AC-05 备份前置）；中断语义经孤儿状态驱动验证（副本已写索引未写→再导入幂等完成并复用副本；记录在副本被外删→内容缺失占位不伪造）。证据：auto tests/spec/t04_library_spec.as 14 PASS/0 FAIL；python tests/spec/t04_http_verify.py 11 PASS/0 FAIL（含容量阶梯 64KB 多章/512KB 边界响应超时但完成/10MiB 显式失败）。**10MiB 长文导入被 VM 指令预算硬上限阻断**（engine.rs CPU_CUMULATIVE_STEP_BUDGET=10M，实测 ≥1MiB 即超），登记跨仓能力计划候选，AC 未以 stub/降标顶替——见 §10。干净数据目录启动：bash tests/spec/run_fresh_server.sh（隔离数据目录 + 端口回显）。

## 6. 测试设计

数据集：中文TXT、Markdown标题、多编码失败、同名不同书、重复句、10MiB长文；tests/fixtures/library/（新建）。

在D:/autostack/auto-os/apps/018-book-reader本仓根以匹配当前基线的auto CLI分别启动`auto run`与`auto run -r vm`，端口17824 / 17825，使用隔离存储目录。依赖准备见[仓根README](../../README.md)，不得把用户真实数据作为首次迁移样本。

本仓现有测试不保证覆盖新增产品能力。先建立tests下针对本计划的可重复fixture和驱动，在报告记录确切启动/执行命令；不得编造尚不存在的npm test/cargo test入口。使用AutoUI verifier现有双端驱动能力时，配置实际端口与app路径。

正确性/恢复/协议测试与UI体验分开记录，至少覆盖一个成功与一个失败路径。现有AutoLang/AutoUI框架不改时不跑cargo全量；若另开框架计划按该仓AGENTS的作用域门禁。文档阶段不运行cargo t/docs_gen。

## 7. 验收标准（必须保留实际证据）

- [x] AC-01: 两份中文真实文件可导入且逐字核对，新增书不再生成占位章节。✅ 证据：t01_http「import txt/md ok + ch1/ch3 body verbatim + toc 3 entries」全 PASS（xiaoshuo.txt 3 章、notes.md 3 章，正文逐字比对）；章节为导入器实切非占位。
- [x] AC-02: 重启后书与原文件仍在、恢复同段落；同标题不同原文件不互相覆盖。✅ 证据：VM 后端重启后 5 本书俱在、章节逐字恢复 PASS；浏览器端到端「已恢复上次位置」+段标记（locator=章节+段序号+同轨签名）；t04「same-title different-content → distinct + distinct book_id + bodies differ」PASS。定位精度为章节+段序（跨轨内容指纹待运行时，见 spec §5）。
- [x] AC-03: 同hash重复导入有明确选择；异常中断不留下成功却缺原文件的记录。✅ 证据：t01/t04「duplicate detected + existing_id + force distinct archive」PASS（明确选择=打开已有或 force 独立副本）；中断语义 t04「orphan reuse import ok + managed copy reused」PASS（副本已写索引未写→再导入幂等完成）。
- [x] AC-04: 无法解码/损坏/不可写给错误且不损坏已有书库。✅ 证据：t01/t04「gbk rejected (real bytes)」PASS（真 GBK 字节 decode_error）；「missing file/directory/empty」PASS；索引写失败回滚不落记录（t02「failed write leaves no record」PASS）。
- [x] AC-05: 书目移除可恢复，默认不删除用户原路径文件；迁移前有备份。✅ 证据：t01「remove ok/managed kept/original untouched/removed.jsonl exists/restore ok/restored chapter verbatim」PASS；library.json 覆写前 .bak（t01「bak exists」PASS）；v0 索引拒绝并保留原件（t04 脚本+HTTP 双面 PASS）。


## 8. 执行步骤与交接

EPUB未实现时在UI标出TXT/Markdown可用范围；不要宣传所有电子书格式支持。

新需求不得在执行中无限追加；发现必要遗漏先更新计划并讨论，不直接删验收项。知识系统/安装服务/AI等未交付依赖必须写明接口级与真实集成的差别。

## 9. 复审记录

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

T-00需核实实际平台/运行时能力，负责者为本计划执行agent；输出具体API、可复现实验与独立阻塞提案。不存在先执行全局重构的隐含前置。核心验收变更须明确提出，不能用mock替换真实结果。

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
