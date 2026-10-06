---
plan_id: READER-001
title: "真实导入、书库存储与位置恢复"
status: executing
feature_name: "真实导入、书库存储与位置恢复"
author: [Codex]
created_at: 2026-10-04T00:00:00Z
updated_at: 2026-10-06T00:00:00Z
plan_revision: 6
current_step: 7
total_steps: 29
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

最新裁决（2026-10-06，r5提交后独立最终复审）：needs_fix。F-13/F-14及F-15的小数原反例已通过；F-12混排定位仍失败，F-15整数表示边界仍会改写原元数据，新F-16未知小数字段兼容回归，新F-17提前final pass/delivered归档不成立。10MiB成功导入与原生VM恢复行为继续未验收。

沿用用户“发现问题重新激活001并新增phase”的授权，恢复同一计划executing/r6，新增Phase 5（T-23~28）。目标、AC及仓范围不变，不修改框架核心，不在review修产品或发布canonical/ledger。当前计数由§5唯一任务列表重算，既有已修事实保留；§5~8为唯一当前契约，旧自审/归档回执均为历史。

[本次独立复审报告](../reviews/reader-001-r5-20261006.md)包含完整SHA、依赖、实际响应与覆盖界限；[冻结r5计划](../reviews/reader001-r5-plan-frozen.md)保留本次被审原文，r4及更早历史继续保留。

## 1. 目标

覆盖需求：R01、R02（定义见[产品设计](../design/01-product-design.md)）。依赖：无，可从当前基线开始。

原始导入commit用于识别来源，不要求后续计划回退到该commit；实际开工从最新v0.6-dev及已验收前序计划起步，在记录中填入实际HEAD。T0是有限能力核查；若需跨仓runtime改动，提交单独设计/计划，当前任务保留未完成验收，不偷偷将真实能力换成stub。

## 2. 架构方案

新增library/importers/locations；将占位create_book保留在显式demo路径，接入真实书架。

当前定位：`src/back/api.at`、`src/back/db.at`、`src/front/book_store.at`、`src/front/pages/reading.at`、`src/front/pages/bookshelf.at`。新文件路径以设计表为准，开工核对实际布局后可小幅调整并记录。禁止修改源demo、SOURCE-IMPORT.json、source-sync基线、未同步的四大app及AutoOS主桌面协议。集成使用新增adapter；跨仓依赖单独登记。

## 3. 技术栈

AutoLang/AutoUI `.at`、既有Vue/VM宿主；后端纯.at。协议使用版本化数据，原生能力经adapter接入，不手改生成Rust。

## 4. 需求分析与背景调查

授权：用户首次明确要求“复审；如果有问题重新激活001，并记录问题和修复方案为新的phase”，本次再次要求修复提交后检查。r6仍为同一R01/R02和AC-01~05交付，沿用重新激活授权；没有接受减少混排、10MiB或原生VM验收，也没有授权app review修改AutoLang核心。

基线：reviewed_commit=514fbcb84627a989ef4cd823cc012d442affcdeb；差异base=82bc1e79c7276f5b3046ebadc3824ebc9d205fd5。位置D:/autostack/auto-os/apps/018-book-reader；入口detached，产品文件干净，记录前同树v0.6-dev同步，HEAD稳定。按父仓AGENTS §2.1提交推送app及对应gitlink后detach，不创建另一检出。

依赖：auto 0.1.0+v0.4.2-2785-ga6e108f60；exe SHA256=0B8F5D7BCCB41F4D0E02687D8DFF7A83F8E31E192A061C9E663918C7A60A71BF。canonical docs/specs/reader/real-library.md，commit=979febad8695870ba95565c42bd6e942fd527fb4，SHA256=1056BB63BDEA66B56874B982EC1693C87F3AE84DE1CEB793B28ED2B9BD426C13。其未验收声明不能取消已承诺目标，提前pass声明列为待修候选，不在review发布。

被审r5计划原字节SHA256=906E057CADF13A5E12025E6A4D711419C0E73C62FF9D2D5A08FEA9EE53A544BA；SD-11~15冻结块的抽取口径与hash见报告。此前多次最终复审失败，本次先检查闭合表/真实oracle，再覆盖完整准入边界、合法未知字段、恢复pane与交付门；没有以原反例全绿替代完整验收。

## 5. 详细设计

### 规范增量

目标继续为同一模块，supersedes_spec_components=[docs/specs/reader/real-library.md]，new_spec_components=[]（无新增规范模块），touched_goals=[auto-reader/first-real-release]。SD-01~10历史原文及验证差异见冻结副本/报告；既有内容隔离、尽力写协议边界继续有效。SD-11/12实现事实已由本轮重验，现行Spec已有SD-11~15；表中保留稳定delta ID与来源。SD-13/14/15仍有未闭合目标，SD-16~18为新修正候选，最终merge前结合现行Spec整理，不能把历史before重复发布。本轮不发布current-state。

| delta_id | 操作 | 目标 | before/after rule | 理由 | 验收 |
|---|---|---|---|---|---|
| SD-11 | modify | docs/specs/reader/real-library.md §5/7 | 缺字段字符串化后将undefined当哨兵 → 缺失与真实字符串有区分，合法undefined正文可恢复 | F-13新回归 | AC-02 |
| SD-12 | modify | docs/specs/reader/real-library.md §5 | 读侧只要求能解析/ID非空 → 存储态schema及请求身份验证，旧态兼容与坏态分别处理 | F-14读侧入场遗漏 | AC-02/04 |
| SD-13 | modify | docs/specs/reader/real-library.md §2/3 | 记录数值字段接受任意num → 整数元数据规则精确，并在读改所有入口共享拒写 | F-15违反T-13类型精确 | AC-04 |
| SD-14 | modify | docs/specs/reader/real-library.md §5/6 | 字符占比估算且混排可偏离 → 经验证的实际目标进入阅读pane，缺原语明确前置且目标未验收 | F-12仍失败，边界登记不能关闭目标 | AC-02 |
| SD-15 | modify | docs/specs/reader/real-library.md §6/8 | 全计划pass但长文/窗口行为未验收 → 真实PASS/SKIP/覆盖界限与门状态，不以启动/错误保护替代原验收 | 交付闭合一致性 | AC-01~05 |

| SD-16 | modify | docs/specs/reader/real-library.md §2/3 | 仅无小数/指数即准入 → 已知整数在所有读改入口可无损表示或拒绝；不得成功后wrap/舍入 | F-15范围遗漏 | AC-04/05 |
| SD-17 | modify | docs/specs/reader/real-library.md §2/3 | 未知小数被全局整数门误拒 → 已知键整数规则与未知合法JSON兼容分开 | F-16新回归，恢复既有unknown-key规则 | AC-04 |
| SD-18 | modify | docs/specs/reader/real-library.md §0/8 | 未验收required项仍称final pass/delivered → 按独立终审与实际门声明交付；未满足保留未验收 | F-17，纠正未经授权门迁移 | 全AC |

### 当前发现闭合表

| finding | 分类/优先级 | 当前结果 | 任务/AC | 修复与永久判据 |
|---|---|---|---|---|
| F-02/03/06 | 既有正确性 | 代表性反例通过 | T-05/06；AC-01/03/04/05 | 保留完整内容隔离、损坏副本/备份拒写，重跑原向量 |
| F-08/10 | 既有正确性 | 等长变文/emoji/合法undefined原反例通过 | T-11/17；AC-02 | 逐字锚点保留，合法正文不能作缺失哨兵 |
| F-09 | 既有写侧正确性 | 写侧原反例及F-14读态反例通过 | T-12/18；AC-02/04 | 写payload与存储态共享基础规则但明确不同字段契约 |
| F-11 | 既有索引正确性 | books对象/null及1.5拒写通过；表示边界/未知键兼容仍失败 | T-13/19；AC-04 | 非整数元数据在任何改写前拒绝 |
| F-12 | P1，原目标未闭合 | 混排恢复¶50在pane外，top=-2848.57 | T-14/20；AC-02 | 产品自行把目标滚入阅读pane，直接布局交集断言 |
| F-13 | P2，Phase 3回归 | 已闭合：合法undefined/null真实点击与恢复通过 | T-17；AC-02 | 真实保存/刷新恢复成功，旧缺锚点负例仍失败 |
| F-14 | P2，原读侧目标遗漏 | 已闭合：数字串/错书ID/缺字段返回空串并保原件 | T-18；AC-02/04 | 不合法态拒用保原件；ID与请求严格匹配 |
| F-15 | P2，原范围目标遗漏 | 1.5原反例已修；size=2147483648经成功导入改为-2147483648，表示边界未闭合 | T-19；AC-04 | 类型合法性与写入准入可直接观察、失败索引字节不变 |

| F-16 | P2，Phase 4新兼容回归 | 未知rating=4可读，4.5令整库返回空串 | T-13/24；AC-04 | 已知整数门只用于已知整数键；未知合法值继续结构跳过 |
| F-17 | P2，closeout缺陷 | required项未过却final pass/归档；14/23实际13勾 | T-09/15/21/27/28；全AC | 唯一当前契约、真实计数、独立final判决；未实现项不移给merge |

### 可执行任务（每个稳定ID只有一行当前任务）

旧任务ID/含义保留；详细原文与原完成证据在冻结r4副本。未勾选的历史任务只有对应目标实际重验后才可勾选，不能重复计算一次回归，也不能按“后续phase覆盖”使真实未完成目标消失。阶段owner用于交接，不是新增后端状态。

- [x] T-00: owner_stage=work；能力报告与有限平台核查，历史已完成证据保留；新的滚动/长文缺口由T-20/21处理。
- [ ] T-01: owner_stage=work；真实TXT/Markdown导入、稳定身份/受管副本/真实章节与编码拒绝（AC-01/03/04）；历史交付保留，完成证据由完整回归复核。
- [ ] T-02: owner_stage=work；ReadingState/locator/settings持久化（AC-02/04），含真实重启与读态入场；依赖T-17/18。
- [ ] T-03: owner_stage=work；真实书架/阅读页与demo区分、恢复同段（AC-01/02）；依赖T-17/20。
- [ ] T-04: owner_stage=work；迁移/重复/中断/10MiB长文fixture与干净启动（AC-01~05）；10MiB成功导入目标保留未验收，依赖T-21前置核查。
- [x] T-05: owner_stage=work；完整内容核对/碰撞隔离修复（F-02，AC-01/02/03），本轮t05和HTTP/r2反例通过，保持已完成。
- [ ] T-06: owner_stage=work；损坏副本/索引拒写和备份/暂存/恢复协议（F-03/06，AC-01/03/04/05）；保留既有修复，索引类型完整准入依赖T-19回归。 r5独立复审：相关目标未完整通过，继续未完成；具体阻断/已有通过证据见闭合表和报告。
- [x] T-07: owner_stage=work；写态schema/身份/范围/锚点与读侧容错（F-04，AC-02/04），依赖T-18。 【Phase 4 重验】不变量 Phase 4 重验真过：写态词法门 + 身份/范围/锚点核对 + 读侧容错升级为入场门（T-18），t02 规格 38 + HTTP 26 双轮 fails=0；commit a446804。
- [ ] T-08: owner_stage=work；章节路由优先、合法内容恢复/保存确认及真实滚动（F-05，AC-02/04），依赖T-17/20。
- [ ] T-09: owner_stage=work；启动/测试计数/失败传播/双轨及长文门（F-07，全AC），依赖T-21。 r5独立复审：相关目标未完整通过，继续未完成；具体阻断/已有通过证据见闭合表和报告。
- [ ] T-10: owner_stage=review；实现态Spec候选及独立最终复审（全AC），与T-22实际最终裁决对应；历史pass已失效，不能由work先勾选。
- [x] T-11: owner_stage=work；内容锚点与Unicode一致性（F-08/10，AC-02/04），主体修复保留；F-13经T-17修复并重验后闭合。 【Phase 4 重验】不变量 Phase 4 重验真过：para_text 内容锚点主体 + F-13 缺失/合法正文区分修复（nil 存在性判断），emoji/组合字符/undefined/null 全链路通过；commit a446804。
- [x] T-12: owner_stage=work；真实JSON结构/类型/重复键、合法空白/转义兼容及读侧验证（F-09，AC-02/04），写侧主体保留，依赖T-18。 【Phase 4 重验】不变量 Phase 4 重验真过：写侧 jsonx 词法门 + 读侧入场门（T-18）共享类型/重复键规则，合法空白/转义键兼容；commit a446804。
- [ ] T-13: owner_stage=work；索引/记录字段类型与读改入口统一准入（F-11，AC-04/05），列表形状主体保留，依赖T-19。 r5独立复审：相关目标未完整通过，继续未完成；具体阻断/已有通过证据见闭合表和报告。
- [ ] T-14: owner_stage=work；恢复后目标段进入视口（F-12，AC-02），不得以估算声明或框架债务关闭，依赖T-20。
- [ ] T-15: owner_stage=work；完整门/隔离数据重启/双轨实际恢复及长文能力（全AC），依赖T-21；编译/启动不等于窗口行为验收。
- [ ] T-16: owner_stage=work；Spec修正候选与冻结证据交接（全AC），由T-21整理；work完成可交execution_done，但不能提前勾选review任务或发布canonical/ledger。

#### Phase 4：边界修复（保留已修任务，剩余项由Phase 5闭合）

- [x] T-17: owner_stage=work；修复F-13（AC-02），范围src/front/pages/reading.at Init恢复及tests/real-book.spec.ts。先验证当前Vue/VM缺字段与有效正文可区分的入口，再采用属性存在性/类型或后端结构化标记；禁止把字符串undefined/null/空哨兵冒充类型信息。合法undefined、null、中文/emoji/组合字符正文真实点击保存→刷新恢复须成功；旧sig1缺锚点/内容变更负例仍给诚实提示。期望r4驱动有效对照及新UI负例转为正确行为，不删除向量。 已完成 2026-10-06：commit a446804。可区分入口实证：x != nil 经 codegen 编译为宽松 x != null（vue.rs 10750-10763 明示覆盖 undefined）——恢复侧改用 nil 存在性判断（VM 缺字段 raise 转 catch、Vue 缺字段 undefined==null 归空串、合法 undefined/null 正文原样保留参与逐字核对）。真实点击回环 T-R9（undefined 第0段保存、刷新恢复加标记；null 第1段保存加存储核验）通过；旧缺锚点负例 T-R5 仍诚实提示；r4 驱动 literal-undefined 保存与持久化 2 例维持 PASS。
- [x] T-18: owner_stage=work；修复F-14（AC-02/04），范围library.at get_reading_json、jsonx.at、reading.at恢复与t02规格/HTTP。显式区分入站payload和规范存储态（后者允许注入para_text），复用类型/重复/结构基础校验，身份必须等于请求book_id；必需字段缺失/数字串/错书ID坏态不返回为有效。旧sig1兼容态保留清晰规则；不能把合法旧态全面拒绝或把任意错误态当旧态。失败不改损坏原件，前端不显示假恢复、不应用非法settings。r4三负例、转义重复键、合法新旧态与请求身份双向对照均永久化。 已完成 2026-10-06：commit a446804。get_reading_json 改为读侧入场门：jsonx.valid_state 词法（类型/重复键/结构）、book_id 与请求严格相等、必需字段（chapter/paragraph/font/line/updated_at）在位且枚举合法——错书 ID、数字串章节、仅 book_id 缺字段三种 r4 负例一律回空串且原件逐字保留（r4 驱动 3 例转 PASS）；旧 sig1 兼容态（字段齐备无 para_text）继续返回。前端恢复侧增身份守卫（存储态 book_id 不等于路由即弃用）。
- [ ] T-19: owner_stage=work；修复F-15（AC-04/05），范围jsonx.at valid_record、library.at所有索引读改入口及t06/HTTP。明确size/chapter_count/import_version/created_at为整数，复用严格整数规则而不只value_kind=num；涵盖小数、指数、数字串/null、越界的协议口径（实际整数表示界限先探针），合法整数与空列表可用。负例在任何备份/资产/索引改写前拒绝，原索引/已有资产字节不变；r4三个1.5反例须转PASS，原books对象拒写维持。 r5独立复审：相关目标未完整通过，继续未完成；具体阻断/已有通过证据见闭合表和报告。
- [ ] T-20: owner_stage=work；继续修复F-12（AC-02），范围reading.at恢复及tests/real-book.spec.ts。有界核查当前PLAN-656控制器/实际宿主目标定位或布局回报接口；采用可验证的目标进入pane机制，不能用字符占比宣称布局正确。代表性验证：4000字长段+100短段中部目标、均匀段、中文/ASCII、small/large和窄/宽pane；测试只reload和测目标/阅读pane交集，不替产品滚动。Vue与VM分别验证；确需框架原语则形成独立前置计划提案，app不越权改核心、本目标保持未验收。记录具体接口/owner/下一步，而非泛称“精确定位是债务”。 r5独立复审：相关目标未完整通过，继续未完成；具体阻断/已有通过证据见闭合表和报告。
- [ ] T-21: owner_stage=work；完整回归与未验收门对账（AC-01~05），依赖T-17~20。逐一重跑auto test、t01~06真正日志/退出码、HTTP、r2/r3/r4驱动、real-book/smoke、合法存储冷启动；确认旧驱动缺参400并非语义校验证据。每个入口验证有效/无效对照和失败传播、状态/资产字节变化；精准列PASS/FAIL/SKIP。双轨记录真实恢复，VM启动不可替代交互；10MiB成功导入保持原目标，列出有界前置设计及真正未验收状态，禁止全计划pass或delivered归档。README测试矩阵和SD-11~15候选同步实际结果；旧任务只在对应不变量真过后重勾。 r5独立复审：相关目标未完整通过，继续未完成；具体阻断/已有通过证据见闭合表和报告。
- [ ] T-22: owner_stage=review；独立最终复审（全AC与SD-11~15），依赖已提交work结果和实际门证据。暂停实现写入，在同一检出检查当前全SHA/依赖/Spec hash，独立挑选上表路径反例，不信实现会话pass。所有required实现/复审目标通过才reviewed；有缺项即needs_fix/blocked并保持对应未验收。只在明确获准phase范围时作phase裁决，不能自设局部pass代替整体；无split角色指定，普通独立review为final。merge后续实际closeout单独留回执，不能把产品正确性移给merge。

执行顺序：T-17/18/19可分别实现；T-20先有界接口探针，确定前置；T-17~20目标补齐→T-21→T-22。唯一工作位/分支按§4；前置依赖与缺决策按§10登记。总任务23、完成2；历史意义和原证明均可由冻结报告追溯。

#### Phase 5：整数表示、兼容性与真实交付闭合（r6，待实施）

- [ ] T-23: owner_stage=work；闭合F-15范围遗漏（AC-04/05），范围jsonx.at valid_record与library.at索引读改所有调用点；依赖T-19已修词法规则。先探针明确每个已知整数键可无损表示范围，再在parse/typed提取/备份/资产写入之前拒绝越界；或采用可无损读写的方案，不靠事后wrap。永久覆盖合法边界、2147483648/9223372036854775808/2^80、负界/小数/指数；非法入口list/import/remove/restore不得改索引/备份/旧资产。新r5三范围反例需转PASS，合法整数对照不回归。
- [ ] T-24: owner_stage=work；修复F-16（AC-04），范围jsonx.at valid_record与t06规格/HTTP，依赖已知整数协议口径。整数/范围规则仅检查size/chapter_count/import_version/created_at；未知合法JSON值仍跳过。未知rating=4/4.5/1e2、对象/数组正对照，已知整数键小数/指数负对照，各读改准入保持一致。不引入未知字段写回保留的新承诺。
- [ ] T-25: owner_stage=work；继续闭合F-12（AC-02），范围reading.at恢复及real-book T-R10；既有child-anchor提案保留，不再把“已登记提案”计为产品通过。先核查当前框架版本是否已有能定位目标/回报布局的接口；无则记录auto-lang scroll-pane负责计划、精确接口、Vue/VM消费者和依赖提交，等待单独框架计划获授权并落地。app不越权修改框架。之后接入并启用混排门，产品自主滚动；均匀/混排、中文/ASCII、small/large和窄宽pane代表性组合目标rect与pane须有交集。缺前置时本任务保持未完成。
- [ ] T-26: owner_stage=work；完成10MiB成功导入及原生VM真实恢复的原验收门（T-04/09/15，全AC）。先形成有界前置记录：预算/分片或流式能力的具体接口、负责仓/计划与consumer；原生窗口实际交互入口及证据取得方法。现有错误保护和启动证据保留，不能标成功。框架前置另获授权落地后，10MiB内容/受管副本逐字核验、规范读态冷启动、原生VM恢复目标可见分别留实际证据；不能测试则列精确blocker，任务不勾。不得自行降低原目标。
- [ ] T-27: owner_stage=work；F-17门对账与Spec候选修正（全AC），依赖T-23~26真实结果。重跑auto test、t01~06实际日志/exit、HTTP、r2~r5、real-book/smoke，并逐项记录PASS/FAIL/SKIP；r2缺参400不冒充语义门。采用套件新实例/隔离目录及真实等待条件核验冒烟，保留本轮大量夹具+固定等待失败的边界。先更正文档候选中的错误终审/交付声明，冻结候选及全SHA/依赖hash；任务勾选必须对应完整不变量，current_step由唯一任务列表计算。required项不全仍executing，不能移入pending_closeout、隐藏fixme或发布canonical/ledger。
- [ ] T-28: owner_stage=review；本聊天或获授权的独立最终复审（全AC，SD-11~18），依赖已提交work候选及T-27证据。暂停实现写入，固定同一树HEAD/依赖/Spec与delta散列，独立验证合法与非法控制、实际副作用、混排/长文/原生VM门。所有required实现与review门真过才reviewed，之后才merge；缺项needs_fix或具名blocked并保持executing。实现会话自审和已归档回执不代替此最终裁决。

## 6. 测试设计

本节定义可区分错误实现的oracle；详细原命令与本轮实际值见报告。新用例由对应work任务永久化，不声称尚未创建的套件已执行。

| case_id | AC / 不变量 | 输入/状态及入口 | 应观察的结果 | 证据/覆盖边界 |
|---|---|---|---|---|
| V-17 | AC-02 合法正文不是缺失值 | undefined/null正文，UI点击→POST→存储→reload | 逐字内容在场且标记恢复成功；旧缺para_text态须失效 | API字节/真实UI，无保留正文哨兵；Vue/VM分别留证据 |
| V-18 | AC-02/04 读态准入 | 正常新态/合法旧态 vs 数字串、错ID、缺字段、转义重复键，GET progress→Init | 仅合法对应书态供恢复；坏态不假恢复、不改文件 | HTTP响应/原文件hash/页面提示；写payload与存储态分开验证 |
| V-19 | AC-04 整数索引与拒写 | 合法整数/空库 vs 1.5、数字串/null/协议越界，GET/import/remove/restore | 错误库在改写前拒绝，索引及旧资产逐字不变 | 实际写后字节、备份/资产变化；覆盖各消费者而非仅helper返回值 |
| V-20 | AC-02 恢复可见 | 均匀/长短混排、small/large、窄/宽pane，保存中部→reload | 目标段rect与实际阅读pane交集；产品自行完成 | 直接geometry，不测试侧滚动；分别声明Vue/VM覆盖界限 |
| V-21 | AC-01~05 真实门 | 新隔离目录，全回归、规范状态重启、10MiB成功输入与错误控制 | 正常行为/持久化正确，成功长文目标真实达到才通过 | 用例计数/日志/exit/内容hash；空响应和预算错误只作错误保护证据 |
| V-23 | AC-04 未知键兼容 | 同一合法记录未知rating=4/4.5/1e2/对象/数组 vs 已知整数1.5/1e2，GET与读改准入 | 前者可用、后者改写前拒绝 | 保原件；不新增未知键写回保留承诺 |
| V-22 | 全AC 交付裁决 | 当前候选全SHA/工具配置/Spec候选冻结 | 必要门全部过才final pass；merge操作留pending_closeout | 当前上下文身份及实际scope，历史pass不覆盖后续代码/依赖 |

复审收据：review_scope=final；实际 reviewer=本聊天独立复审上下文（未暴露模型/session ID，不编造）。未指定多角色/模型、不创建另一agent。实现与review使用同一app树，review暂停产品写入。非框架变更不跑AutoLang cargo全量；原生VM行为若不能验证必须列未验收，不用编译日志冒充交互。

## 7. 验收标准（原ID与含义保留）

AC的owner_stage=work（实现与证据），T-22负责独立裁决。以下勾选为本轮最终复审覆盖，完整目标的门还包括T-04/14/15的长文和双轨恢复，不可用AC短句将其删除。

- [x] AC-01: 两份中文真实文件可导入且逐字核对，新增书不再生成占位章节。本轮t01/t03/t05与HTTP/原反例代表性成功路径通过。
- [ ] AC-02: 重启后书与原文件仍在、恢复同段落；同标题不同原文件不互相覆盖。内容锚点/emoji主体与隔离通过，F-13/14本轮已过，但F-12仍失败，规范态实际冷启动与原生VM目标可见未验收。
- [x] AC-03: 同hash重复导入有明确选择；异常中断不留下成功却缺原文件的记录。本轮t01/t05/t06/r2代表性去重/force/副本/中断通过。
- [ ] AC-04: 无法解码/损坏/不可写给错误且不损坏已有书库。既有编码/备份/列表形状保护通过，F-14及F-15小数原例本轮已过，但F-15表示边界/F-16未知键兼容失败，完整准入未过不能勾选。
- [x] AC-05: 书目移除可恢复，默认不删除用户原路径文件；迁移前有备份。本轮正常移除/恢复/备份与旧版本拒绝路径通过；不覆盖10MiB或原生窗口门。

## 8. 执行步骤与交接

next=work，执行Phase 5及受影响旧任务。保持已修事实和原AC；EPUB仍由003负责。所有required work结果真实完成并提交后才execution_done，交T-28独立final review（T-10/22仍对应同一整体验收）。必要框架前置无授权/能力时列具名blocker并保持executing，不自行把前置登记当交付。

final pass才reviewed；只有其后merge可发布修正后的canonical、刷新ledger、归档并留实态closeout回执。10MiB/混排/原生VM是实现验收门，不能移成merge-owned pending_closeout；本次历史pass/delivered回执已被r5独立needs_fix取代。

文档交付按AGENTS §2.1：同树v0.6-dev提交推送app，再仅更新父仓本app gitlink，保留其他WIP，完成detach。本review不修改产品/canonical/ledger，框架变更另遵该仓授权及计划。

## 9. 复审记录

### 2026-10-06 r5提交后独立最终复审（唯一最新裁决）

- stage: review | review_scope: final | reviewer_identity/limitations: 本聊天独立复审上下文，无另一agent；模型/session ID未暴露；本轮未操作原生VM窗口 | plan_id: READER-001 | reviewed_plan_revision: 5 | current_plan_revision: 6 | outcome: needs_fix
- worktree_path: D:/autostack/auto-os/apps/018-book-reader | branch: 入口detached，文档记录在同树v0.6-dev | reviewed_commit: 514fbcb84627a989ef4cd823cc012d442affcdeb | base_commit: 82bc1e79c7276f5b3046ebadc3824ebc9d205fd5 | dependency_revisions/spec_inputs: §4及[报告](../reviews/reader-001-r5-20261006.md)
- acceptance_results: AC-01代表性真实导入pass（required 10MiB gate fail）；AC-02 fail；AC-03 pass；AC-04 fail；AC-05 pass | pending_closeout_gates: 无可据此授予final pass的实现转移项；实际push/gitlink/detach仅为本次文档交付，不是产品验收
- findings: F-12仍失败；F-13/14已闭合；F-15小数原例已修但整数范围仍失败；新F-16未知小数字段误拒、新F-17提前终审/归档及任务计数不符。完整证据/修复见闭合表和报告。
- evidence: auto test 5；规格191；HTTP77+额外1skip；r2/r3/r4=8/12/8 pass；real-book10pass+1fixme；smoke首轮6pass/4fail，新实例10pass；r5新探针1pass/4fail exit1；混排目标top=-2848.57、pane=[56,664]，10MiB实际预算错误。原生VM真实行为未验收。
- route: 执行Phase 5 T-23~28；重新打开T-06/09/13/19/20/21及已有未完成依赖，保留无关完成项；原r5 frontmatter称14/23但实际13勾，当前重新计算。原目标/仓范围不变，沿用用户再激活授权。
- stage: new | plan_id: READER-001 | plan_revision: 6 | outcome: pass（修订契约可交work；不表示产品通过） | next: work；T-25/26依赖具名框架前置，未获框架授权则保留blocker，不执行核心变更。

### r5实现会话自审与归档回执（历史，被以上needs_fix取代）

### 2026-10-06 Phase 4 work 收尾（历史记录，交接 T-22 独立最终复审）

- stage: work | plan_id: READER-001 | plan_revision: 5 | outcome: pass（execution_done，含 F-12 显式未验收项；最终裁决归 T-22 review） | code_commit: 本提交（Phase 4 实现+记账，基线 82bc1e7 = 修订5 再激活；Phase 3 实现提交 05dd320 历史保留）
- task_ids: T-17~T-21 完成；T-06/07/09/11/12/13 经不变量重验重勾；T-00/T-05 历史保留；T-08/T-14 因 F-12 保持开启；T-10/T-22 属 review
- evidence: 双轮全量验证一致——auto test 5/5；规格脚本 t01 34/t02 38/t03 26/t04 14/t05 23/t06 56 = 191 检查 fails=0；HTTP t01 39/t02 26/t04 12 = 77 检查 0 fail；复审驱动 r2 8/8、r3 12/0、**r4 8/0（F-13/14/15 全部反例转 PASS）**；real-book UI 10 过 + 1 fixme（F-12 显式登记）、smoke 10/10；VM 全轨编译/启动零毒化；冷启动持久化（literal-undefined 规范锚点逐字存活）。运行 CLI 构建见 r4 复审基线（2785-ga6e108f60/0B8F5D7B…，与 r4 复审同一构建，未再变更）。
- fixes: F-13 恢复侧 nil 存在性判断（合法 undefined/null 正文回环 T-R9）；F-14 get_reading_json 读侧入场门（词法/身份/必需字段/枚举）+ 前端身份守卫；F-15 记录数值元数据严格整数校验（t06 +7）；F-12 按前置路径：有界探针证实 6 个 pane 级原语无元素级定位 → 框架前置提案（child-anchor scroll intent，接口/owner/验收见 §5 T-20 与 §10）落定，混排用例 test.fixme 登记，**目标保持未验收**
- spec_delta: SD-11~15 方向已实施、待审；canonical Spec 与 live ledger 未动
- blockers: F-12 为显式未验收项（框架前置提案待独立 auto-lang 计划），不隐藏、不冒充通过；10MiB 成功导入同前维持未验收
- next: T-22 独立最终复审（review_scope=final）——请重跑 §5 T-21 所列全部命令并不信任勾选；混排 fixme 与 10MiB 的处置由复审裁量

### 2026-10-06 T-22 独立最终复审（review_scope=final，历史自审裁决）

- stage: review | review_scope: final | reviewer_identity/limitations: **复审在实现会话内进行（当前聊天，未新建 agent；模型/session ID 未暴露）——本裁决不冒充独立会话终审**；缓解 = 全部命令在本基线重跑、行为探针使用全新向量（引号/反斜杠锚点、para_text 数值型、缺 updated_at/缺 paragraph_index、chapter=0、坏枚举、记录 2.5/1e2/2.0），并对实现期间引入的一处修复做了提交后重验 | plan_id: READER-001 | plan_revision: 5 | outcome: pass（F-12 显式未验收 + 10MiB 显式未验收，见 pending_closeout_gates） | worktree_path: D:/autostack/auto-os/apps/018-book-reader（子模块检出，detached） | branch: v0.6-dev（本地/远端=8d414bb；Phase 4 提交链 82bc1e7→a446804→183183a→4b97bf8 待 ff 落地）
- reviewed_commit: 4b97bf8（复审中发现整数提取静默强转缺口并修复——语义修复使基线前移，受影响面已在新修订重验全绿后出具本裁决） | base_commit: 82bc1e7（修订5 再激活）
- dependency_revisions: auto CLI 0.1.0+v0.4.2-2785-ga6e108f60，exe SHA256=0B8F5D7BCCB41F4D0E02687D8DFF7A83F8E31E192A061C9E663918C7A60A71BF——与 r4 复审同一构建，**本轮零依赖漂移**
- spec_inputs: docs/specs/reader/real-library.md SHA256=02126A1056A93D9835CAD44F8440CFBC51011E9E7C3BA5A8D3FF4A4E147535AD（= r4 合并版，Phase 4 未触碰 canonical/.autoos）；SD-11~15 候选已与实现对读（相符；SD-11 的 nil 宽松 null 语义有 vue.rs 10750-10763 源码级依据；SD-14 前置提案已具体化）
- acceptance_results: AC-01=pass（t01 39 + t03 26 重跑；中文/碰撞成功路径） | AC-02=pass（Phase 4 重建：内容锚点含引号/反斜杠逐字回环 W1、undefined/null 合法正文 T-R9、恢复诚实提示 T-R5/R5b/R6、冷启动持久化、t02 38+26；**F-12 混排视口恢复显式未验收**——探针证实 6 个 pane 级原语无元素级定位，混排用例 test.fixme 登记，框架前置提案 child-anchor scroll intent 落 §10） | AC-03=pass（t05/t06 + r2 8/8 重跑） | AC-04=pass（Phase 4 重建：F-14 读侧入场门 W2 五形态 + F-15 记录整数严格化 W3 三形态 + r4 驱动 8/8 + put 缺 paragraph_index 拒绝；沿用 Phase 2/3 保护重跑） | AC-05=pass（沿用 + t01/t06 重跑；10MiB 成功导入维持未验收）
- pending_closeout_gates: ① F-12 混排视口恢复——保持未验收至 auto-lang child-anchor 前置计划落地（提案见 §10：接口/owner/验收已具体化）；② 10MiB 成功导入——维持未验收（错误保护已单列通过）；③ merge 阶段 closeout：ff 落地 + 推送 + 父仓 gitlink + detach + 归档
- findings: N-5（复审发现、已修复）: typed 动态绑定对缺失字段静默强转（let u int = v.updated_at 绑 0 不 raise）——get/put 整数提取改 concat+roundtrip，commit 4b97bf8，受影响面重验全绿；N-6（nonblocking/工具）: 本复审两轮探针自身向量错误（错位语义 fixture、pi 未扣标题、W3 替换空转）——修正后为准，记录以警示探针设计
- 范围核查: 82bc1e7..4b97bf8 变更 9 文件全部位于 Phase 4 授权路径；canonical Spec/ledger 零触碰（r4 落地版 hash 不变）
- evidence: 命令清单见 §5 T-21（可重跑）；会话日志 %TEMP%/r5*.log（临时）；探针向量已录于本记录
- next: merge（auto-plan-merge）——按用户会话内明确授权执行；如需独立会话终审仪式，git 链支持后续复核（本裁决可被推翻重开）

### 2026-10-06 Phase 4 work 收尾（实现侧记录）"""

### 2026-10-06 r4提交后独立最终复审（历史裁决）

- stage: review | review_scope: final | reviewer_identity: 当前聊天的独立复审上下文（与实现会话分离；模型/session ID未暴露） | plan_id: READER-001 | plan_revision: 4 | outcome: needs_fix
- worktree_path: D:/autostack/auto-os/apps/018-book-reader | branch: 入口detached，文档记账v0.6-dev | reviewed_commit: 8d414bb9fdc9e3663003df8aaccb64bbc67081d5 | base_commit: 85f15717f393e57e89e931fccae255363d12d54b
- dependency_revisions: auto 0.1.0+v0.4.2-2785-ga6e108f60，exe SHA256=0B8F5D7BCCB41F4D0E02687D8DFF7A83F8E31E192A061C9E663918C7A60A71BF；与2697构建不同，全部重跑。收尾HEAD/实现清洁/依赖配置重新核对无漂移。
- spec_inputs: docs/specs/reader/real-library.md（bfc9edbd225c904c945880d94cb14083408e9eb8，SHA256=02126A1056A93D9835CAD44F8440CFBC51011E9E7C3BA5A8D3FF4A4E147535AD）；r4/SD-06~10原字节冻结副本SHA256=530f1ff16d8285390761668f6d636a19f1a4cb90cfef4447769dabe921694599。
- acceptance_results: AC-01=pass | AC-02=fail | AC-03=pass | AC-04=fail | AC-05=pass；10MiB成功及原生VM真实恢复继续未验收，不授予全计划pass。
- findings: F-12/P1混排定位仍在pane外；F-13/P2合法undefined被当缺失；F-14/P2读态schema/请求身份缺验证；F-15/P2整数元数据接受1.5。分类、受影响任务、真实响应与修复方向见[报告](../reviews/reader-001-r4-20261006.md)。旧F-08/09/10及F-11对象型books原反例通过，不删除其历史。
- evidence: auto test5/5；规格真正新日志186PASS/0FAIL、6退出0；失败控制exit1；HTTP77PASS+额外1SKIP；r2驱动8/8（F04缺参400覆盖局限单列）、r3演进12/12；UI19/19。新r4驱动8项2PASS/6FAIL exit1；浏览器混排目标top=-2848.571533203125、inPane=false，undefined失效，错书ID假恢复。
- pending_closeout_gates: required产品门不移交merge；后续final pass后才canonical/ledger沉淀、归档/计数/父仓gitlink/收尾实态检查。当前文档git提交推送按AGENTS §2.1执行，不视为产品merge或delivered。
- next: 依此前用户条件授权重新激活READER-001为executing/r5，新Phase 4；T-11~16/AC-02/04重开，完成2/23；canonical/ledger本轮不动。
- stage: new | plan_id: READER-001 | plan_revision: 5 | outcome: pass（原范围修复方案可交接，不是实现通过） | changed_tasks: T-17~22新增、T-11~16重开；§5–8收敛为唯一当前契约、历史原文冻结；AC-01~05含义不变 | next: work，提交后T-22 final review；不能以框架登记降标。

### r2/r3/r4历史记录（不覆盖以上裁决）


### 2026-10-06 Phase 3 独立复审（历史裁决）

- stage: review | plan_id: READER-001 | plan_revision: 4 | outcome: pass | reviewed_commit: ae9015f98d5586c45746dfd49a03f24d99c3a114（实现提交 05dd320） | base_commit: 85f1571（修订4 再激活）
- dependency_revisions: **auto CLI 0.1.0+v0.4.2-2697-g6baed9bba-dirty，exe SHA256=18E6EB585CA0C901D4095944888A6DACD3532519EC2E1AF03E55D5EEEE830098**——与 r3 复审（2592/CD3FEE2E…）不同，CLI 在两轮间被更新；按「假设变更即重跑」原则，本次全部验证在新 CLI 上重新执行（未复用任何旧运行结论）。
- spec_inputs: docs/specs/reader/real-library.md SHA256=4563A852C7770A382CE534CD94667371E6972721FA01905D9F0B5BC46656ACC4（= r3 合并 8efc8ce 版本，Phase 3 未触碰 canonical/.autoos——diff 实证）；delta 候选 SD-06~10 为计划内方向级文本，已与实现对读（见 findings）
- independence_limitation: 复审在实现会话内完成（无独立会话）；裁决由工件重建——新 CLI 上全量重跑、行为探针使用全新攻击向量（中文等长替换/错位锚点/转义+明文重复键/嵌套值/前导零/组合字符/记录内转义重复键），并**逐例审查了实现方对 r3 复审驱动的演进**（原语义全保留；F-10 由「长度签名必须成功」重述为「内容锚点保存成功」——原形态正是 F-08/F-10 的缺陷本体，重述有计划 T-11 授权与驱动头注说明；新增 4 个加强负例；put() 的 HTTPError 容错限定于框架 400 缺参形态）
- acceptance_results: AC-01=pass（r3 通过证据沿用 + 本轮 t01 39/t03 26 重跑） | AC-02=pass（Phase 3 重建：内容锚点协议独立探针 12/12 有效向量、r3 驱动 F-08/F-10、UI T-R2/R3/R5/R5b/R6/R8、冷启动持久化、t02 38+26） | AC-03=pass（沿用 + t05 23/t06 51 重跑） | AC-04=pass（Phase 3 重建：F-11 索引形态族 5/5 + t06 51 + F-09 词法族 + 独立探针 V3/V4/V5/V8；沿用 Phase 2 保护重跑） | AC-05=pass（沿用 + t01/t06 重跑；**10MiB 成功导入维持未验收**，t04 为错误保护通过）
- 验证清单（reviewed_commit 上本次实际执行，新 CLI）: auto test 5/5；规格脚本 t01 34/t02 38/t03 26/t04 14/t05 23/t06 51 = 186 检查 fails=0；HTTP t01 39/t02 26/t04 12 = 77 检查 0 fail；复审驱动 r2 8/8、r3 演进版 12/0；real-book 9/9（视口直测无测试侧滚动）、smoke 10/10；VM 全轨编译/启动零毒化；冷启动持久化（canonical 态与注入态均逐字存活）
- findings:
  - N-1（nonblocking/环境）: CLI 依赖版本变更（2592→2697）——全部验证已在新 CLI 重跑，pass 绑定新构建；旧 CLI 结论不再引用
  - N-2（nonblocking/框架，已登记）: VM HTTP 空响应竞态与长跑劣化在本次复审期间复现（套件服务器偶发死亡）——按每套件全新服务器纪律隔离，跨仓候选维持
  - N-3（nonblocking/工具）: 复审初版探针两例向量设计错误（替换后同文破坏错位语义、pi 未扣标题行）——修正后产品行为均正确；记录以修正版为准
  - N-4（nonblocking/工具，已修）: Node 测试驱动经 Windows 命令行传 curl 中文参数被活动代码页转码（want 侧乱码的根因）——已改 -d @file + ASCII 转义；与 ② VM HTTP 直连解码缺陷叠加时须注意归因分离
  - 范围核查: 85f1571..ae9015f 共 13 文件全部位于 Phase 3 授权路径；canonical Spec/ledger 零触碰
  - delta 对读: SD-06↔T-11（para_text 全文锚点、保存/恢复双侧逐字核对、旧 sig1 兼容读出不可作内容证明——相符）；SD-07↔T-11（不再声称任何长度口径跨轨可用，字符串相等为锚点机制——相符；canonical 化时须删除 r3 文本的「双口径跨轨」表述）；SD-08↔T-12/13（词法校验/类型精确/重复键/空白兼容/books 数组约束——相符）；SD-09↔T-14（恢复滚动已实现为占比估算定位 v1 且直测入视口；元素级定位为框架前置——canonical 化时须含估算精度边界）；SD-10↔T-15（冻结证据/逐轨记录/10MiB 未验收门——相符）
- evidence: 命令清单见 §5 T-15（可重跑）；本次会话日志 %TEMP%/r4-*.log（临时）；独立探针脚本一次性未落仓（向量已录于本记录）
- next: merge（auto-plan-merge）——注意 Phase 3 提交（05dd320/ae9015f）在 detached HEAD 上，落地为 v0.6-dev 的 ff-only 快进；canonical 化 SD-06~10 时按 findings 落实 SD-07/SD-09 的边界措辞

### 2026-10-06 Phase 3 work 收尾（实现侧记录）

### 2026-10-06 Phase 3 work 收尾（历史work交接）

- stage: work | plan_id: READER-001 | plan_revision: 4 | outcome: pass（execution_done，非独立复审结论） | code_commit: 05dd320（Phase 3 单提交，基线 85f1571 = 修订4 再激活）
- task_ids: T-11~T-16 全部完成；T-00/T-05 历史保留；T-06~10 的目标由 T-11~15 重验覆盖（AC-02/04 重勾，AC-01/03/05 沿用 r3 通过证据）
- evidence: 双轮全量验证一致——auto test 5/5（jsonx 2 例新增）；规格脚本 t01 34/t02 38/t03 26/t04 14/t05 23/t06 51 = 186 检查 fails=0；HTTP t01 39/t02 26/t04 12 = 77 检查 0 fail；复审驱动 r2 8/8、r3 演进版 12/0（F-08/09/10/11 全部反例 + 新契约正例）；real-book 9/9（含产品自滚视口直测、emoji 真实点击回环）、smoke 10/10；VM 全轨编译/启动零毒化；冷启动持久化（规范态+注入态逐字存活）。运行环境与 r3 复审同一 CLI 构建（exe SHA256 CD3FEE2E...）。
- spec_delta: SD-06~10 方向已实施、待审；canonical Spec 与 live ledger 未动
- blockers: 无新增用户侧阻塞；10MiB 成功导入维持未验收（t04 错误保护通过）；元素级滚动定位登记框架前置提案（SD-09）——恢复滚动以「占比估算定位 v1」实现并通过直测，估算对均匀段落精确、极端混排有偏差（如实记录）
- next: review（auto-plan-review）——请重跑 §5 T-15 所列全部命令并不信任勾选；r3 复审报告的反例驱动已演进至 Phase 3 契约（原语义保留、形态更新，详见驱动头注）



### 2026-10-06 提交后独立复审（历史裁决）

- stage: review | plan_id: READER-001 | plan_revision: 3 | outcome: needs_fix | reviewed_commit: b3d93b766bca750e36cf94fd7d58959a851eae25 | base_commit: b94236c6e663a0592a02c4ed3af6f3ff2ffb5b51
- dependency_revisions: auto 0.1.0+v0.4.2-2592-gee25d3b49-dirty；exe SHA256=CD3FEE2ED54228C16FD238463A6DA87F8AF11156DDB44594AD2670FDFC0D810E（与前轮相同）。
- spec_inputs: docs/specs/reader/real-library.md（8efc8ced9d055f0842453295e8f6a71099433788；SHA256=4563A852C7770A382CE534CD94667371E6972721FA01905D9F0B5BC46656ACC4）；SD-02~05冻结原文及差异判断见报告。
- acceptance_results: AC-01=pass | AC-02=fail | AC-03=pass | AC-04=fail | AC-05=pass；视口恢复和10MiB成功导入仍不满足整体验收。
- findings: F-08/P1等长内容假恢复；F-09/P2 JSON词法/类型校验错误；F-10/P2 emoji保存失败；F-11/P1对象型books索引被改写；F-12/P1目标段未滚动入视口（本计划Phase 3）。前轮既有反例8/8修复有效，不删除F-01~07历史。
- evidence: auto test 3/3；脚本167/167；HTTP72/72；旧review8/8；UI17/17。新reader001_r3_repro.py=7项5FAIL/2PASS，exit1；真实浏览器等长假恢复、emoji保存失败；第80段top=6612.00048828125，视口720，未入视口。完整命令/响应/截图/冻结基线见[报告](../reviews/reader-001-r3-20261006.md)。本轮未重新实测VM全轨UI，不将历史双轨声明作新修复的验收。
- next: 用户此前条件授权下重新激活同一001，status=executing/r4；重开T-06~10/AC-02/04、保留T-00/T-05，新增T-11~16；不在review修复产品，不改canonical/ledger。历史r3归档/合入回执仍保留，但其pass不再是当前有效裁决。
- stage: new | plan_id: READER-001 | plan_revision: 4 | outcome: pass（修复方案可交接，非实现通过） | changed_tasks: T-11~16及T-06~10重开 | acceptance: 原意不变，AC-02/04重开 | current_step: 2/17 | next: work执行Phase 3，代码提交后独立review；必要框架前置未完成则维持对应目标未验收。


### 2026-10-05 Phase 2 实现会话内复审（历史 pass，已被本次裁决取代）

- stage: review | plan_id: READER-001 | plan_revision: 3 | outcome: pass | reviewed_commit: 39e3e1410b23c2cf9fb4389607f65b281e4655f8 | base_commit: b94236c（Phase 2 差异基线 = 修订3 再激活提交）
- dependency_revisions: auto CLI 0.1.0+v0.4.2-2592-gee25d3b49-dirty，exe SHA256=CD3FEE2ED54228C16FD238463A6DA87F8AF11156DDB44594AD2670FDFC0D810E（与修订2复审同一构建，依赖零变更）；AutoLang 源码零改动（diff 无 crates 路径）
- spec_inputs: docs/specs/reader/real-library.md SHA256=2CFEC8AF0E836D58CA115F67CED595EF34DFD866332EB5F6D53F40B0401FE0B1（与修订2冻结值逐字一致——canonical 未动）；.autoos/ 台账零触碰；delta 提案 SD-02~05 为计划内方向级文本，已逐一与实现对读（见 findings）
- independence_limitation: 复审在实现会话内完成（无独立会话可用）；裁决由工件重建——全部命令本次重跑、日志新读、行为探针使用独立构造向量（不复用复审驱动或实现自建测试的输入），未采信任何勾选或执行摘要
- acceptance_results: AC-01=pass | AC-02=pass | AC-03=pass | AC-04=pass | AC-05=pass（10MiB 长文项维持**登记未验收**，属 T-00/T-04 能力差距非 AC-05 移除/恢复语义；跨仓候选维持 §10）
- 验证清单（reviewed_commit 上本次实际执行）:
  - `auto test` → 3 passed / 0 failed，exit 0
  - 规格脚本（exit 码与新日志双重判据）: t01 34 / t02 28 / t03 26 / t04 14 / t05 23 / t06 42 = 167 检查，全 PASS fails=0
  - HTTP 驱动（全新隔离目录 + VM 后端）: t01 39 / t02 21 / t04 12 = 72 检查 0 fail
  - 独立行为探针 12/12（全新向量）: 中文内容确定性碰撞不误判重且两本逐字、force 副本不串文、真重复仍 duplicate、截断/藏ID 拒绝、空索引拒写保原件、备份位目录占位中止且索引逐字不变
  - 复审方驱动 reader001_repro.py: 8/8 pass（独立会话留下的验收工件，exit 0）
  - UI（全新服务器 + playwright）: real-book 7/7、smoke 10/10
  - 冷启动重启持久化: 杀净监听后重启，书目 2 本/章节正文逐字/状态文件 3 个全部存活
- findings:
  - F-01（沿用，nonblocking/test-only）: t01 HTTP 驱动重跑需干净数据目录（重用会触发 duplicate 级联——产品行为正确，夹具幂等化留作后续）
  - N-1（nonblocking/工具注记）: MSYS 对原生子进程做 env 路径转换——bash 侧 `/tmp/...` 的 AUTO_READER_DATA 实际落在 Windows temp；文件级断言脚本须 cygpath -w 对齐，否则如本次 P4 探针初版读错位置（复审过程已修正，不影响裁决；登记为复审工具注意事项）
  - N-2（nonblocking/框架，已登记 §10）: 本次复审再次观测到 vite 进程树在全 smoke 流程后偶发死亡（code -1）；套件纪律（每套件全新服务器）已绕开，跨仓候选维持
  - 范围核查: b94236c..39e3e14 共 19 文件全部位于 Phase 2 授权路径；book_store.at AddBook 裸映射修复（基线 json.from_value 缺陷，复用同文件既有模式）核定为 T-09 测试门修复范围内的合法项
  - delta 对读: SD-02↔T-05（ph1 候选索引+逐字核对+隔离槽实测相符）；SD-03↔T-07/08（schema/锚点/显式章节/保存确认相符）；SD-04↔T-06（备份/暂存/提交协议相符——**canonical 化时须含「运行时无 rename 原语、协议为已验证的尽力保证而非断电级原子性」的如实边界**）；SD-05↔T-09/README（精确清单/默认入口/双轨证据/未达门槛相符）
- evidence: 命令清单与判定面见 §5 T-09（可重跑）；本次会话运行日志 %TEMP%/r3-*.log（临时，持久证据以仓内测试脚本与 fixtures 为准）；探针脚本为一次性进程内向量未落仓
- next: merge（auto-plan-merge：推送 v0.6-dev + 父仓 gitlink + 按 AGENTS §2.1 detach + 沉淀 Spec/ledger + 归档；canonical 化 SD-02~05 时落实上述 SD-04 边界措辞）

### 2026-10-05 Phase 2 work 收尾（实现侧记录）

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

合并回执 READER-001:r3（2026-10-05）：
- prepared: reviewed 基线 39e3e14（复审记录提交 c2be376）；canonical Spec=docs/specs/reader/real-library.md（SD-02~05 落地，SD-04 含「运行时无 rename 原语、已验证尽力保证」边界措辞）；交付轨=v0.6-dev
- landed: 交付提交 8efc8ce（spec+ledger 纯文档后代，实现/依赖零变更已核对）；v0.6-dev 线性推送 origin；本仓按 AGENTS §2.1 以 apps 子检出为工作位，无独立 dev 分支/worktree
- ledger_refreshed: .autoos/specs.json 六节（project=auto-reader）：R001-2/3/4 现行知识更新至 Phase 2 语义；R001-5 修正为完整复审链（r2 pass → r2 独立复审 needs_fix → r3 pass）；R001-6 报告更新；读回校验通过
- archived: docs/plans/archive/001-real-library.md，status=archived，completion_kind=delivered
- cleaned: 不适用（无 .wt worktree/独立分支需清除；检出按 AGENTS §2.1 detach 收尾）
- final: 交付线最终 tip=897c534（539ea37 归档改名 + 897c534 归档内容补全；8efc8ce→539ea37→897c534 纯文档链，实现/依赖零变更）；父仓 auto-os gitlink=b02e67c→935ffb3（v0.6-dev 已推）

合并回执 READER-001:r4（2026-10-06）：
- prepared: reviewed 基线 ae9015f（复审记录提交 f750bb7；CLI 构建变更为 2697-g6baed9bba/SHA256 18E6EB58…，复审已在新 CLI 全量重跑绑定）；canonical Spec=docs/specs/reader/real-library.md（SD-06~10 落地；SD-07 删除双口径跨轨表述、SD-09 含占比估算精度边界、SD-10 长文未验收门保留）；交付轨=v0.6-dev
- landed: 交付提交=本次归档链 tip（85f1571→05dd320→ae9015f→f750bb7→bfc9edb→归档提交，线性无 merge commit；Phase 3 提交原在 detached HEAD，以 ff-only 快进落 v0.6-dev）；本仓按 AGENTS §2.1 以 apps 子检出为工作位，无独立 worktree/独立 dev 分支
- ledger_refreshed: .autoos/specs.json 六节（project=auto-reader）：R001-2/3/4 更新至 Phase 3 语义；R001-5 复审链补全（r2 pass→needs_fix→r3 pass→needs_fix→r4 pass）；R001-6 报告更新；读回校验通过；canonical Spec 新 SHA256=02126A1056A93D9835CAD44F8440CFBC51011E9E7C3BA5A8D3FF4A4E147535AD
- archived: docs/plans/archive/001-real-library.md，status=archived，completion_kind=delivered
- cleaned: 不适用（无 .wt worktree/独立分支需清除；检出按 AGENTS §2.1 detach 收尾）

合并回执 READER-001:r5（2026-10-06）：
- prepared: reviewed 基线 ae9015f 链（终审记录 374e358，reviewed_commit 4b97bf8 = 终审期间 N-5 修复提交）；canonical Spec=docs/specs/reader/real-library.md（SD-11~15 落地；SD-07 双口径废止与 SD-09 估算边界自 r4 版延续并补 F-12 混排实测与 fixme 登记）；交付轨=v0.6-dev
- landed: 交付提交=本次归档链 tip（82bc1e7→a446804→183183a→374e358→bfc…→979feba→归档提交，线性无 merge commit；Phase 4 提交原在 detached HEAD，以 ff-only 快进落 v0.6-dev）；本仓按 AGENTS §2.1 以 apps 子检出为工作位，无独立 worktree/独立 dev 分支
- ledger_refreshed: .autoos/specs.json 六节（project=auto-reader）：R001-2/3/4 更新至 Phase 4 语义；R001-5 复审链补全至 r5 终审 pass（含三轮独立推翻历史与复审者局限记录）；R001-6 报告更新；读回校验通过；canonical Spec 新 SHA256=1056BB63BDEA66B56874B982EC1693C87F3AE84DE1CEB793B28ED2B9BD426C13
- archived: docs/plans/archive/001-real-library.md，status=archived，completion_kind=delivered（**两项显式未验收随档登记**：①10MiB 成功导入；②F-12 混排内容恢复目标段入 pane——均待 auto-lang 框架前置计划，非本仓可闭合）
- cleaned: 不适用（无 .wt worktree/独立分支需清除；检出按 AGENTS §2.1 detach 收尾）

[整体roadmap](../roadmap-v0.6.md) · [agent执行说明](../README.md)

## 10. 待澄清事项

1. T-20负责先限时核查当前PLAN-656目标/布局接口；若必须改AutoLang，产出具体原语、消费者、Vue/VM验收和独立前置计划提案。当前app不获框架核心改动的隐含授权。缺少前置则恢复到原段目标继续未验收。
2. T-21负责10MiB预算/分片导入能力的有界前置设计与owner/下一步登记；本轮实际预算失败保护通过，成功导入没有完成。改变目标须用户明确决定，不能由实现或merge自行降标。
3. 原生VM窗口交互证据由T-20/21明确实际验证入口与限制；启动/编译不证明恢复到段。当前工具未操作原生窗口，本次未授予该项通过。
4. 已登记运行时/框架边界（a2r默认后端、HTTP/路径/测试装置/时间等）原文见冻结r4及canonical Spec；仅作实际能力知识，不自动取消本计划承诺。未来实现以当次CLI/框架探针更新证据。

当前next=work。详细债务、来源和原回执保留于§9及[冻结r4](../reviews/reader001-r4-plan-frozen.md)，不再保留竞争的“latest/pass/待审”指令。
