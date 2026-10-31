---
plan_id: READER-004
status: reviewed
feature_name: Reader验收驱动与夹具归属迁移
author: [Codex]
created_at: 2026-10-31
updated_at: 2026-10-31
plan_revision: 1
current_step: 5
total_steps: 6
supersedes_spec_components: [docs/specs/reader/real-library.md]
new_spec_components: []
touched_goals: []
affects: [auto-reader, test-infrastructure]
---

# [READER-004] Reader验收驱动与夹具归属迁移

## 0. 变更摘要

按用户要求将auto-lang中Reader验收夹具与对应两份驱动迁至auto-reader，解决应用测试寄居语言仓及外部技能目录隐式依赖。独立于PLAN-899 ACE清理；不修改Reader产品行为、语言VM预算语义或AutoUI框架能力。本轮仅立项，依仓规L1先展示计划再实施。

## 1. 目标

- G1：两个fixture目录、生成器与应用验收驱动由auto-reader拥有，auto-lang不留重复实现。
- G2：auto-reader可从任意cwd使用显式auto二进制运行驱动，不导入auto-lang源码树/技能目录。
- G3：现有用例、输入hash、oracle、拒写/冷重启/进程收割与退出码保持；当前文档/调用入口正确承接。

非目标：改产品、削减测试/样本、迁全部Reader历史脚本、迁通用MCP框架实现、清缓存、更新其他应用/组合仓pin、push或发布。框架通用预算/滚动/MCP单测仍归原owner，本包不搬其生产实现。

## 2. 架构方案

| 当前auto-lang路径 | 新auto-reader路径（新建） |
|---|---|
| test/fixtures/native-reader-acceptance/ | tests/fixtures/native-reader-acceptance/ |
| test/fixtures/reader-import-budget/ | tests/fixtures/reader-import-budget/ |
| scripts/tools/test_native_reader_acceptance.py | tests/native/test_native_reader_acceptance.py |
| scripts/tools/test_reader_import_budget.py | tests/spec/test_reader_import_budget.py |

原生fixture是Reader场景的框架正对照，非真实Reader源码副本；按用户指定归Reader集成验收，框架Spec引用外部入口。应用驱动在Reader侧自带必要的轻量MCP客户端适配，保现有请求/截图/错误语义；不搬整个autoui-verifier技能，也不改其通用客户端。若现有已交付公共包可直接消费，T-01核证后采用等价依赖，不新增未经核实的发布前置。

CLI明确接收auto-bin（现有原生驱动已required；导入驱动统一显式参数或AUTO_BIN），Reader根与fixture位置按脚本自身位置解析；app-dir/reader-dir现有显式覆盖保留。不得硬编码D:/autostack路径或回退到语言仓旧副本。auto二进制属于必要运行依赖，不等同于依赖语言仓源码。

## 3. 技术栈

现有Python标准库、Auto split-VM HTTP/MCP、.at fixture与确定性生成器。不引入新测试框架。代码改动跨两个专用worktree；通过来源hash与逐项收据保迁移可追溯性，跨仓无单事务，先目标可用后源退役。

## 4. 需求分析与背景调查

### 4.1 用户授权与边界

用户明确提出这两个Reader测试目录应迁到auto-reader。本轮已授权调查及准备迁移；用户随后明确要求计划归auto-reader并沿用应用编号。本轮仅纠正计划归属与编号，不扩大为实施授权。后续按既有展示合同后执行的流程推进。不创建代理/聊天，不联系其他会话，不改其WIP。此前ACE方案未获确认，本包不顺带执行899。

### 4.2 事实来源

- auto-lang调查基面cec583174；其900草案提交6f02303bf仅为本计划迁入来源，已按用户要求撤销该编号占用。应用权威入口docs/README.md及docs/specs/reader/real-library.md；跨仓规范入口auto-lang/docs/specs/overview.md。
- auto-reader main当前154b1ca0e07e2be6f56a75bede1485634c423e13，git status干净；根无AGENTS.md，实施前继续核父级及目标子树指令。
- auto-reader/README.md测试表仍指向auto-lang/scripts/tools/test_reader_import_budget.py，已有tests/{fixtures,review,spec}，fixtures当前有library目录。
- test_reader_import_budget.py实际启动Reader，执行10MiB TXT/MD导入、hash/章逐字、冷重启、低预算拒写、坏编码与双实例；fixture缺席时生成。
- test_native_reader_acceptance.py为Reader/最小对照app提供真实窗口几何、锚点、保存/恢复与故障控制；当前从auto-lang/.agents/skills/autoui-verifier/scripts/test_vm_mcp.py导入AutoUiMcpClient/pick_free_port。
- scroll-geometry/src/front/app.at含120行与scroll-anchor；save-restore是ASCII120段框架正对照，真实HTTP落盘/恢复，不能误称等同于Reader完整多字节恢复验收。
- 当前Spec引用：docs/specs/auto-lang/vm/design/handler-execution-budget.md、ui/design/native-acceptance-channel.md及ui/overview.md；历史781文档保原证据，只补当前迁移指向。

唯一拟实施组D:/autostack/.wt/reader-004/{auto-reader,auto-lang}；Reader分支codex/reader-004-dev，语言分支codex/reader-004-lang。每仓一树，实现与复审按同树顺序进行，无junction/symlink。本计划及进度簿记唯一位于auto-reader主检出；两仓源码、README与测试改动均在各自实施树，语言仓仅承接执行时必要的源退役/规范沉淀，不另占语言Plan编号。

## 5. 详细设计

T-01固定已跟踪来源及生成资产边界，记录文件hash和case清单。小型确定性种子/生成器按现有规则入库，大型生成文件及执行证据留本地，遵守>5MB门禁；迁移前后用生成器重建核hash，不把现存未跟踪数据误认为可随意提交或删除。

T-02在Reader创建目标目录、搬迁两驱动和fixture并改根解析/CLI；MCP适配仅承接驱动实际使用方法与错误语义。自适应截图、进程终止/端口释放和隔离数据要求保持。源脚本待目标验证成功后由T-04退役，无长期双份copy或静默回退。

当前README/规范指向新入口并说明应用外部验收与框架单测各自职责；历史归档/证据不批量重写。全仓活跃调用者搜索核源退役，源可执行入口不留空壳伪PASS。

### 规范增量

| delta_id | add/modify/retire | docs/specs/... target | before/after rule | rationale | AC |
|---|---|---|---|---|---|
| SD-01 | modify | auto-lang/docs/specs/auto-lang/vm/design/handler-execution-budget.md | Reader deep oracle路径由本仓迁至auto-reader；语言预算单测不搬 | 应用归属 | AC-01/03 |
| SD-02 | modify | auto-lang/docs/specs/auto-lang/ui/design/native-acceptance-channel.md | Reader原生验收/fixture改外部owner及可运行入口 | 框架合同保留，应用验收独立 | AC-01/03 |
| SD-03 | modify | auto-lang/docs/specs/auto-lang/ui/overview.md | 当前驱动路径/owner承接 | 消除错误导航 | AC-03 |
| SD-04 | modify | docs/specs/reader/real-library.md | 本仓拥有导入预算/原生验收驱动及fixture，声明执行入口与外部auto二进制依赖 | 应用测试单源 | AC-01/02/03 |

SD-01..03是auto-lang协同写面，不冒充Reader本仓Spec；SD-04为本计划本仓规范增量。

## 6. 测试设计

以下未执行。仅迁移触面，不跑ACE、全语言/全UI或Reader全部产品套件。若真实窗口验证适用，执行前读取autoui-verifier技能并用现有通道；单实例有界验证，不并发窗口抢占。

| ID | 不变量与入口 | 可观察结果/边界 | owner_stage |
|---|---|---|---|
| V-01 | 迁移来源文件/生成器输出hash、case及断言清单对账 | 仅路径/导入/CLI必要变化；数据、样本、oracle、退出码守恒 | work |
| V-02 | 两新驱动--help；非repo cwd导入/加载；Reader本地fixture生成/manifest hash校验 | 不访问auto-lang源码或技能目录；无旧路径回退 | work |
| V-03 | Reader新导入驱动原完整用例；显式auto-bin/reader-dir与隔离目录 | TXT/MD10MiB+冷重启/坏编码/低预算拒写/双实例原case与原assert全通过；退出码/结果同时核 | work |
| V-04 | Reader新原生驱动原默认required集合；显式v12_injected_fail反控单独运行 | 默认required全通过；故意失败非零；真实几何/保存恢复/锚点/故障判定与reap保持 | work |
| V-05 | 源退役活跃调用者/文档检查与独立删除审查 | 原目录/驱动无重复实现；目标唯一可运行；历史路径仅历史说明保留 | review |

列实际发现/执行/条件排除，原首次红、环境缺口及重放不抹去；准备/运行/清理/总时长分列。环境不可用不算通过；确有框架产品缺陷保复现并回相应owner，不顺带重写产品。没有Rust生产改动，不要求cargo t全组。

## 7. 验收标准

- [ ] AC-01（work）：两fixture、生成器及两驱动在Reader唯一归属，来源/输入/oracle守恒；V-01/03/04。
- [ ] AC-02（work）：Reader入口可从任意cwd运行，无语言仓源码/技能目录隐式依赖；V-02/03/04。
- [ ] AC-03（work）：Reader README及语言当前Spec/活跃调用者迁移正确；历史记录保真；V-05。
- [ ] AC-04（review）：独立逐AC/删除与遗漏复审pass，无静默减覆盖、workaround或未处理本包格式/告警。
- [ ] AC-05（merge）：先Reader交付再语言退役，记录两仓提交与Spec回写，归档并guard清理两树；不自动更新组合pin或push。

## 8. 执行步骤

| ID | owner_stage/依赖 | 操作、实际路径及结果 | AC/验证 |
|---|---|---|---|
| T-01 | work/方案确认 | [x] 核两仓指令/基面，建唯一兄弟树；来源hash/case/调用者/生成资产审计，冻结MCP实际方法集合与命令 | AC-01/02；V-01 |
| T-02 | work/T-01 | [x] Reader新增tests/native与目标fixtures，迁两驱动并去外部技能导入，更新CLI/README | AC-01/02/03；V-01/02 |
| T-03 | work/T-02 | [x] Reader树完整迁移触面真实验收及反控；记录首次红/退出状态/数据hash/端口reap | AC-01/02；V-03/04 |
| T-04 | work/T-03 | [x] 语言树删除源两目录及两驱动，准备当前Spec迁移delta，核所有活跃调用者 | AC-03；V-05 |
| T-05 | review/T-04 | 冻结两树，同树独立上下文审查逐AC/删除与SD，需修回原树；不以实现自检代复审 | AC-04；V-01..05 |
| T-06 | merge/T-05 | 先Reader合入其main，再语言master退役+Spec沉淀；在auto-reader归档004、按适用最新留存政策、逐树wt-guard clean后清理分支/组 | AC-05；记录两仓delivery及清理收据 |

T-01 证据（2026-10-31）：基面 auto-reader a0801bc / auto-lang 0e6fbf9b4（cec583174→0e6fbf9b4 触面零变化）；来源hash审计（6×.at fixture + .gitignore + gen_fixtures.py + 两驱动，sha256 记录于本地 evidence/）；MCP 依赖面冻结 = call/snapshot/press/screenshot + pick_free_port（无公开 autoui 包，`import autoui` 失败 → 驱动内轻量适配）；活跃调用者 = 语言仓 3 Spec + test-purpose-policy.json S-014（modularity survey report 为历史快照不改），Reader 侧 README 测试表 + t04/t26 注释。worktree 组 D:/autostack/.wt/reader-004/{auto-reader codex/reader-004-dev, auto-lang codex/reader-004-lang}。
T-02 证据：commit 9bab983（14 文件，+3431/-4）；py_compile 两驱动通过；--help 两驱动过（原生 usage/退出码语义不变；导入 --auto-bin/--reader-dir 新缺省语义）；生成器重建与源侧逐字节一致（manifest.json sha256=7afa5231…，5 数据文件全同）；残余引用扫描仅出处注释命中。fixture .gitignore 补 manifest.json（本仓无语言仓全局 *.json 规则）。
T-03 首红证据（2026-10-31，非迁移缺陷）：完整导入套件 6 腿 6/11（v17/v19/v14/w03 实例腿全部 backend not live；v15_boot 4 项因 fail-fast 语义仍记录 [+]/[+]），report=plan-artifacts/reader-004/import/；根因探针 = **当前运行时 `auto.exe`（auto-man/target/debug，2026-10-31 11:37 构建）对 reader 主检出与 worktree 同样报 `[AutoVM server] error: Undefined variable: zip`**（READER-003 EPUB `zip` 命名空间解析失败，后端 120s 未就绪）；plan-890 legacy 副本/AUTO_LANG_ROOT/旧备份配对探针均不复绿。属并发 auto-man 会话施工回归（其 Cargo.lock WIP 正加 aes/zip），非本包改动所致。V-02 的非 repo cwd/退出码检查已先期通过（--auto-bin 缺省缺失→exit 3；argparse 用法错→exit 2）。

T-03 完成证据（2026-10-31，运行时恢复后；双二进制口径=用户裁定）：运行时身份 auto.exe `e7dd7df1`（17:22 gbe740b6，报告自录 sha）+ auto-ui-tool `4d2198b8`（16:34 用户侧重建，导入驱动经 AUTO_UI_TOOL_BIN 显式透传；原生驱动实例剥离 AUTO_* 落同级 discovery=同一 tool）。**V-03 导入面**：6 腿分片全绿 36/36 检查、逐片 exit 0（`plan-artifacts/reader-004/import-r3-chunks/chunk-{1..6}/`；v17_txt 10MiB+1347 章逐字×2 轮、冷重启 pid 切换、v19 低预算指名拒/坏编码/库不变、v14 双实例不串线、v15 boot fail-fast ×6、w03 损坏章负例+未扰章守恒）。**V-04 原生面**：g1-g4 = 11 required PASS + g5 转正版 v08_reader_current_state 8 检查 PASS + g6 `v12_injected_fail` 反控 exit=2 ✓，全部 owned-port sweep clean（`plan-artifacts/reader-004/native/{g1..g6}/`）。运行期两修复（ee5d7a6 + cd903dd）：N-1 身份 oracle 适配分裂宿主拓扑（端口由本 run 进程树持有，CIM+BFS，反伪装意图不变）；N-2 v08_reader_current_state 按其自身条款转正（781 缺陷取证 oracle 在 r9 修复后不可过——直证探针 v08-state-probe3：¶ 标签在场/空占位与合成错误缺席；新 oracle=真实按压导航 OpenBook/OpenChapter + 真实正文渲染断言 + r8 同款 library HTTP 保存链读回逐字一致；required=False→True）。原样 verbatim 首红在身份门被拦（g5-firstred 日志留档）。运行时解阻史与两个外部事实记录于 §9 前 receipt 与 §10。

T-04 证据（2026-10-31，语言分支 codex/reader-004-lang @ 970003151，基 0e6fbf9b4）：git rm 源两目录+两驱动（10 文件）；SD-01（handler-execution-budget.md：驱动/夹具改指 auto-reader owner，语言侧 cargo t plan781 / cargo th http_e2e_plan781 不变）、SD-02（native-acceptance-channel.md：新入口+进程树身份 oracle 注记，通道合同不变）、SD-03（ui/overview.md：导航改指）落盘；活跃引用扫描=残留仅 docs/plans/archive/781-*.md 与 784/814 attachments 历史快照（按计划保留）。**V-05 边界记录**：scripts/test-governance/test-purpose-policy.json 的 S-014 条目为语言仓主检出**未提交 WIP**（不在本分支树、git 无历史），不可跨会话改写——其指向退役路径的事实归该 WIP owner 提交时承接，此处如实路由。

下一执行入口：work 段完结（execution_done，T-01..T-04 全绿）→ review（T-05，review_scope=final，同树独立上下文逐 AC/删除与 SD 复审；两树冻结于 reader cd903dd / lang 970003151）。统一回归门=review/merge 所有者。reader 分支基为 38fa8d8（重放自用户侧操演，reflog 留痕），main 现 bf62c8c（+2 纯簿记提交不触代码，证据复用有效），merge 时合流。不依赖899执行。无新增审查模型/代理授权。

## 9. 复审记录

2026-10-31 / stage:new / READER-004 r1 / outcome:pass（草案自查，非实现验收）/ next:展示确认后work。来源、目标、AC/任务/SD及去外部技能依赖已明确；未迁测试、未跑UI/HTTP或修改Reader产品。用户明确要求纠正归属后，本草案迁为READER-004，docs/README.md登记入口；auto-lang移除900草案并在无后继分配前提下恢复.next-id=900。原草案提交保留Git历史，不重写共享提交。

2026-10-31 / stage:work / READER-004 r1 / outcome:blocked / worktree:D:/autostack/.wt/reader-004/auto-reader (codex/reader-004-dev, base a0801bc→code 9bab983) + D:/autostack/.wt/reader-004/auto-lang (codex/reader-004-lang, base 0e6fbf9b4) / dependency_revisions: auto.exe 706d13f5(11:37)+auto-ui-tool 563afa4a / task_ids: T-01,T-02 完成并验证；T-03 首跑环境红 / evidence: V-01 hash守恒（来源8文件+生成资产6文件逐字节一致，本地 plan-artifacts/reader-004/）；V-02 入口/退出码检查过；V-03 首红=运行时回归「Undefined variable: zip」（探针证据 plan-artifacts/reader-004/probe/，主检出同样失败=非迁移缺陷）；T-04 按 T-03 门禁未启动、未删任何源 / blockers: 并发 auto-man 会话施工回归运行时 / next_responsible_role: work（运行时恢复后重跑 T-03）。

2026-10-31 / stage: goal | plan_id: READER-004 | plan_revision: r1 | round: 1 | from: work | to: work | status: executing | outcome: blocked | worktree: D:/autostack/.wt/reader-004/auto-reader | commit: 9bab983 | next: user（解除动作见§10：auto-man 并发会话交付 zip 运行时后重跑 T-03；本目标授权链继续有效，恢复后从 work 段 T-03 进入）

2026-10-31 / stage: goal | plan_id: READER-004 | plan_revision: r1 | round: 2 | from: work | to: work | status: executing | outcome: waiting | worktree: D:/autostack/.wt/reader-004/auto-reader | commit: 9bab983 | next: user。等待轮：复探运行时仍红（同一 11:37 auto.exe + 同一 zip 错误；auto-man WIP/HEAD 无新进展，`~/.auto` 安装面今日未动，lock WIP 未触及 auto-lang-core，语言仓 3 提交纯 docs）；legacy d2b2664 副本配 10-30 auto-ui-tool 仍红（排除 e6cc06f 单点回归假说）。已向用户提供三选项（等 owner 会话 / 授权旧提交构建 / 用户自行处理），未获答复。不做任何源/树写入；恢复后从 work 段 T-03 进入（§10 解除动作不变）。

2026-10-31 / stage:work / READER-004 r1 / outcome:pass / worktree:D:/autostack/.wt/reader-004/auto-reader (codex/reader-004-dev: 6ecfe64→ee5d7a6→cd903dd, base 38fa8d8) + D:/autostack/.wt/reader-004/auto-lang (codex/reader-004-lang: 970003151, base 0e6fbf9b4) / dependency_revisions: auto.exe e7dd7df1 + auto-ui-tool 4d2198b8 / task_ids: T-01..T-04 全部完成 / evidence: V-01 来源hash+生成资产逐字节守恒（§8 T-01/02 行）；V-02 入口/退出码；V-03 36/36（import-r3-chunks）；V-04 原生 g1-g4 11 required PASS + g5 转正版 8 检查 PASS + g6 反控 exit2（native/g1..g6）；V-05 残留仅历史归档（policy-json WIP 路由 §9 T-04 行）/ blockers: 无（运行时解阻史+UI 按压通道缺口路由见 §10）/ next_responsible_role: review（T-05 final，两树冻结）。

2026-10-31 / stage: goal | plan_id: READER-004 | plan_revision: r1 | round: 3 | from: work | to: review | status: execution_done | outcome: pass | worktree: D:/autostack/.wt/reader-004/auto-reader | commit: cd903dd (reader) / 970003151 (lang) | next: review（T-05 final，review_scope=final；T-06 归属 merge）。work 段全链完成：迁移守恒验证 36/36 + 原生 12 required 全过 + 反控正确非零；两修复（身份树适配 N-1、v08 转正 N-2）与语言侧退役（T-04）均已提交并验证。

2026-10-31 / stage: review | review_scope: final | reviewer_identity/limitations: 实现会话本体复审（无独立会话/模型可用）——按技能以盘上工件独立重建结论，不采信执行摘要；此局限显式记录 | plan_id: READER-004 | plan_revision: r1 | outcome: **pass** | worktree: reader D:/autostack/.wt/reader-004/auto-reader (codex/reader-004-dev) + lang D:/autostack/.wt/reader-004/auto-lang (codex/reader-004-lang) | reviewed_commit: reader cd903dd88d7401ff442a342cd6cd6d18413c9df0 (base 38fa8d8) / lang 97000315167549949a9a2531fb1d14aeecfeddfc (base 0e6fbf9b4) | dependency_revisions: auto.exe e7dd7df1 + auto-ui-tool 4d2198b8（双钉口径，导入报告自录）| spec_inputs: reader real-library.md（SD-04 段在 cd903dd 树）；lang 三 spec（SD-01/02/03 在 970003151 树，git show 各计 1 处命中）| acceptance_results: **AC-01 pass**（6×.at fixture + gen_fixtures.py 与 lang 基逐字节同（sha256 对账）；.gitignore 差异=已记录的 manifest.json 边界；导入驱动 diff 仅 docstring/路径/CLI 四类（独立 diff 审计）；原生驱动函数清单守恒，新增仅适配器+process_tree_pids）；**AC-02 pass**（两驱动零 auto-lang/技能目录导入；套件自非 repo cwd=/d/ 运行全绿；退出码语义守恒：3=环境缺、argparse 用法错、0/2/3 合同）；**AC-03 pass**（README 2 新行；语言 SD-01..03 落 HEAD；删除面净，残留仅 781 归档+784/814 附件历史快照+modularity survey 历史记录；policy-json=主检出未提交 WIP 已路由）；**AC-04 pass**（本次复审；原始工件独立对账：import 36/36 且 cli sha 自证、g1-g6 manifests 案例级核对面：11 required+转正 1 全 pass、g2 tree_pids=0 形态合理（v12 就绪前失败不触身份门）、g6 injected_fail 如实 fail）；**AC-05 pending**（merge 所有）。repair 闭环核验：N-1 身份树适配=4 hunk 定位无误+g2 零记录形态自洽；N-2 转正=直证探针+verbatim 首红（身份门拦留档）+8 检查绿 | pending_closeout_gates: merge 收尾（reader registry 行仍 "drafting/尚未实施" 需翻新+归档翻面；lang master 合流+spec 沉淀；plan-artifacts 全 scope 删除（2026-10-31 delete-at-merge）；landing 观察；两树 guard+清理；无统一回归门欠账——计划 §6 明示仅迁移触面且 V-01..05 已全跑）| findings: 无需修复项；4 条非阻塞观察（UI 按压通道缺口已路由框架 owner §10；policy-json WIP 路由；registry 行 merge 翻新；分支基 38fa8d8 重放自用户操演+main +2 纯簿记——merge 合流，证据不受影响）| evidence: 本 receipt 所列全部盘上路径 | next: **merge**（T-06）。

## 10. 待澄清事项

用户已指定目标owner为auto-reader；此处不再询问归属选择。待确认上述具体跨仓迁移方案后实施，尤其包含两份驱动及其路径/MCP辅助依赖，而非只移动数据目录。

**阻塞已解除（2026-10-31，用户取证纠正）**：真因不是 auto.exe 回归——`run -r vm` 的 api.at 链编译发生在 **auto-ui-tool.exe**（auto-ui 仓 `run_vm.rs`）进程内；该 tool 停在 10-30 11:05 构建、内嵌 lang-core 无 zip natives（二进制 `auto.zip.` 命中 0 次），且 `auto-ui-tools` 非 auto-man workspace 默认成员、日常构建不重建它。zip natives 本身是今日上午才进 auto-lang（实现 10:52、静态 catalog 11:29），reader 的 zip 消费 11:47 提交——此路径今日首跑即"首红"，无绿→红回归。用户侧已重建 tool（`cargo build -p auto-ui-tools`，新 sha256 前16 `4d2198b8bceba015`，旧件备份 `auto-ui-tool.exe.1030-baseline`；auto.exe `706d13f5` 未动），探针复绿（server ready + health 200）。原 bug 报告的方向性错误已由用户追加更正节（同文件）。**T-03 证据口径（用户裁定）**：必须固定双二进制——`--auto-bin` 与实际编译宿主（显式 `AUTO_UI_TOOL_BIN`，导入驱动经 os.environ 透传至子进程；原生驱动 Instance 会剥离子进程 AUTO_*，落 auto.exe 同级 discovery=同一重建版 tool，结果等价），并把两 sha256 记入证据。无需 auto-man 立项。

**路由框架 owner（2026-10-31，T-03d 发现，非本包范围）**：阅读页活视图重建导致 **UI 段落按压经 AutoUI MCP 通道不可稳定驱动**——`autoui_vtree` 给出的段落容器 vnode 在按压时报 `View not found at path`（vtree 与活视图失配），`autoui_find` 返回祖先链但链上容器均无 press handler；书架卡片按压亦有一次候选误命中相邻 `.bookshelf.ShowAdd` 的竞态（5 探针中 1 次）。复现证据：`plan-artifacts/reader-004/probe/pp2..pp5`、`native/g5/out/raw/v08_reader_current_state.json` press_log。转正版 v08 的保存链改走 r8 已验证的 library HTTP 面（16/16 同源），渲染断言保留真实按压导航；UI 按压面待通道/框架侧修复后可回归（886 诊断面同族）。
