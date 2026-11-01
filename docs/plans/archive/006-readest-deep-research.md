---
plan_id: READER-006
status: archived
feature_name: "Readest详细调研与覆盖路线再设计"
author: [Codex]
created_at: 2026-11-01
updated_at: 2026-11-01
plan_revision: 1
current_step: 10
total_steps: 10
base_branch: main
base_commit: 0a296b39f84ce1d741511413a5eec9d3cd0225f0
depends_on: ["READER-001", "READER-002", "READER-003", "READER-004", "READER-005"]
supersedes_spec_components: []
new_spec_components: []
touched_goals: []
---

# READER-006：Readest 详细调研与覆盖路线再设计

## 0. 变更摘要

在“覆盖 Readest 开源项目绝大多数能力”的新目标下，详细调查 Readest 官方文档、真实源码与依赖、实际 UI 和运行行为，与 AutoReader 已交付能力逐项对照。基于证据修订总设计和路线，确定后续计划建议、依赖和验收边界。本计划交付研究与设计，不实施阅读器功能。

**work 阶段执行状态（2026-11-01）**：T-00～T-07 已完成（基线/矩阵/代码地图/UI 实测/对照核查/决策与报告/二次修订/内部核对），产出 docs/research/readest/ 五份报告并二次修订总设计与路线（coverage v2）；T-08 独立复审、T-09 归档未执行。详见第 9 节回执。

## 1. 目标

1. 固定可追溯的 Readest 发布/源码/文档/UI 基线，按需要建立真实本地 clone。
2. 完整盘点已发布能力、平台/服务条件、实际交互与工程机制，区分计划中和未核实项。
3. 建立稳定功能 ID 与 AutoReader 覆盖/差距矩阵，解释何为“绝大多数”，防止名称覆盖冒充可用。
4. 给出引擎、Vue/原生 VM 接缝、定位/标注迁移、服务与许可/分发的比较决策。
5. 根据详细调研再次修订总设计、路线和导航，再确定首批后续计划的建议范围与依赖。

非目标：直接移植 Readest/React/Tauri、改 AutoReader 业务代码/数据格式、修改框架代码、支付/订阅、建立新在线账号、实现同步服务或更新 AutoOS gitlink。实际 UI 调研包括运行经核实的发布版或本地构建；不把产品功能实现混入调研。后续正式计划不在本计划中批量取号或自动执行。

## 2. 架构方案

研究执行、内部核对和最终复审顺序使用 D:/autostack/auto-reader 独立 clone 的 main，同一检出、一 app 一写入者；无应用 worktree，不在 D:/autostack/auto-os/apps/auto-reader 编辑。

Readest 源码位建议为 D:/autostack/readest。T-00 先检查是否存在及 Git 身份、状态：不存在时从 https://github.com/readest/readest.git 建立真实独立 clone；存在时不清理、reset、切换他人 WIP。若已有目录不可安全复用，使用新的独立目录并记录实际路径。固定已发布基线及其提交；必要时另读主分支差异，不混用证据。子模块如为分析/构建所需，依固定提交实际检出并记录；禁止 junction/symlink、伪造依赖目录或把源码复制进 app。

实际 UI 优先使用可核验的桌面官方发布版或固定源码构建；Web 可以作为补充，不代替桌面结论。发布版与源码版本不同须映射差异，不把两个版本拼成一个已验证产品。安装/构建命令从对应版本文档与 package manifest 中确定后记录，不预填未经核实的启动命令。

研究成果统一放 docs/research/readest/（新增）；截图、录屏、构建产物、依赖与测试语料放报告所记载的仓外证据目录，避免混入产品资源。Markdown 报告记录可复查的步骤、截图索引、版本/hash、关键结果；报告要能独立理解，不能只留不可访问的本机绝对路径。

## 3. 技术栈

AutoReader 当前为纯 .at 应用、AutoUI Vue/原生 VM、HTTP VM 后端、Playwright 和原生 UI 验收驱动。Readest 的语言、构建工具、文档引擎、平台桥、云服务与测试工具在 T-00/T-02 从固定源码核实；技术栈名称不是预先选定的 AutoReader 实施路线。

UI 观察使用执行环境可用的浏览器/桌面控制工具，使用前读取对应技能；不能用 HTTP 写入或源码推断替代规定的用户操作。仅研究文档不运行 AutoReader 功能回归，不在 auto-lang 跑 cargo/docs_gen。

## 4. 需求分析与背景调查

### 已有授权与范围

用户于 2026-11-01 指定：先按覆盖 Readest 的目标更新总设计/路线；建立详细调研计划；需要时可在该计划内克隆 Readest，分析文档、代码和实际 UI；依据调研二次修订设计/路线，之后确定后续计划。本轮交付是前置文档与计划起草，详细调研留 work 阶段；同范围执行无需重复申请克隆许可。

允许研究时读取 AutoReader、AutoOS 的相关规范，以及实际框架 owner 的能力资料；源码变更范围仅为本 app 的研究/设计/路线/导航和计划文档，不写其他仓。未指定时间/费用/token 预算或模型分工，不虚构其授权。额外账号、收费、实体设备或产品代码修改超出本计划执行范围，具体缺证如实记录。

### 已观察事实

- 001～005 已归档，当前没有相同活动计划；.next-id 为 006，已在独占锁下复核活动区和 archive/archived 最大编号并分配 006。
- EPUB 章内容转为文本/图片行，图片与书内链接已交付；非完整 HTML/CSS 阅读表面，自定义 Locator v1 不是 CFI。
- 注释有稳定 ID、原文子串核验、回访与导出；高亮为段级标记，无完整子串样式与划词选区。
- 005 双端聚合门已交付，原生写传输及 scroll-pane 自动化路径缺口在册。其当前框架状态需核验，不直接归因或在本计划修复。
- 旧设计包含早期种子库/旧路线，已在 new 阶段修正；现实现 Spec 保持不变。历史研究只作线索，不替代本计划的新证据。

### 源与版本

AutoReader 源码/规范基线为 0a296b39f84ce1d741511413a5eec9d3cd0225f0；本次新目标文档在 T-00 补记交接时实际提交/内容 hash。下列 hash 为 new 阶段实读源，work 不得默认它们永远不变。

| 源路径 | SHA256 |
|---|---|
| docs/specs/reader/real-library.md | 027df6a839919fbe174e911227f8fbeb3ee5658e0dd9aaa935668494791f4f23 |
| docs/specs/reader/epub-reflow.md | 8e74c12222a3cf1be6ac9ba2107ae69406efefd3d45c1da71c13d7550eb120a7 |
| docs/specs/reader/reading-annotations.md | c2ace0e4b9de7486d6bae4921662484e22bbe03cc16abbac5c3d182aefbb766b |
| docs/specs/reader/standalone-reading.md | 4e40eec8ab1f8b3716f3983b0929a7a182ec902a4cc3cb22a4d153f7fcd3f0ee |
| src/back/epub.at | a9434338887933fc0469849e77a38deba295bf57196e514f4ee71f16d7a19075 |
| src/front/pages/reading_page.at | 1a6d4af8daf8b653a1994ed03c343d8dc8dce741b81b748a61ecb7c54cdcf325 |

研究入口：https://github.com/readest/readest 、https://readest.com/docs 。旧样本可参考 auto-os/docs/research/apps/reader.md 与本仓 docs/research/20261004-benchmarks.md，但其发布日期和样本不当作当前事实；上游所有精确路径、提交和依赖由 T-00～02 重新核实。

## 5. 详细设计

### 5.1 研究产物（均已产出，2026-11-01 work 阶段）

| 文件 | 内容与闭合要求 |
|---|---|
| docs/research/readest/baseline.md | 仓库/提交/tag/子模块、文档访问日期与固定源、实际 UI 版本/平台/来源、构建和隔离目录、命令/退出码；记载无法建立的对应关系 |
| docs/research/readest/capability-matrix.md | 稳定 ID RDT-Cxx-NNN；发布状态、平台/服务条件、文档/代码/UI 证据、AutoReader 现状、差距、覆盖程度、依赖、候选工作流 |
| docs/research/readest/code-map.md | 文档引擎、解析/资源、选区/定位/注释、书库与迁移、平台桥、服务与同步、测试；真实入口→调用→持久化/渲染的路径与符号 |
| docs/research/readest/ui-study.md | UI 用例 ID、语料与来源、前置条件、实际步骤/结果、截图索引、冷启动/离线/异常观察、版本差异与未验证项 |
| docs/research/readest/decisions.md | 引擎/平台/迁移/服务方案比较，推荐与替代，证据/成本/风险，未决问题的最小探针，以及候选计划的范围/依赖/验收 |
| docs/research/readest/report.md | 综合结论、证据导航、计数规则/目标建议、核心任务覆盖、重大差距、对设计/路线的具体修订与后续计划顺序 |

### 5.2 能力清单与深读原则

从官方发布说明、功能文档、设置/菜单和实际源码入口盘点总设计 C01～C07；C08 为 AutoOS 扩展，单列且不混入 Readest 分母。新增发现不能因不在初始表内而遗漏。为每个功能记录已发布/主分支新增/计划中/未核实；代码存在不等于稳定可用。

源码深读至少包括：EPUB 与 PDF/其他格式分派；Readest 定制引擎与上游差异；资源与 CSS/字体；分页/滚动；选区/CFI 或其他 locator；搜索、注释恢复/导出；书库身份/元数据/迁移；桌面/浏览器平台服务；TTS/翻译/OPDS；同步存储、冲突/离线；测试与故障分支。用路径+符号+固定 commit 的永久链接建立调用证据，不能只罗列依赖名/类型枚举。

完整覆盖/部分覆盖/缺失/待验证/排除逐项说明。若提出排除，要记裁定来源；没有裁定的难项仍留在范围内。提出计数分母、权重和目标建议，分别报告核心任务与总量；不在本阶段任意宣称达成 90% 等比例。

### 5.3 实际 UI 最小任务集

以下均为拟执行任务，未有实测结果。每项含具体输入、实际结果和可观察证据；自制或可再分发语料至少覆盖中文/混排、图片/脚注、重复句、长章，另备文本型 PDF 和漫画样本。记录运行时能支持的格式，不用同一 EPUB 代表全部格式。

| UI ID | 必需观察路径 | 能区分错误结论的观察 |
|---|---|---|
| U01 | 空书库→文件导入→打开→元数据/组织→移除/恢复（若存在） | 真实内容、书籍身份与状态；没有的入口标记不存在，不能虚构流程 |
| U02 | EPUB 目录/图片/脚注往返→字体/主题→分页/滚动 | 版式保留、目标原文、往返位置；变化布局后回到同一内容 |
| U03 | 选择重复句中的指定一处→高亮/批注→搜索→重开→回访→导出 | 精确选区而非整段；重启后 ID/定位/文本一致，导出有来源 |
| U04 | PDF 打开→缩放/翻页→选字/搜索/标注（按宣称范围） | 固定版式与坐标/文本定位；不支持的内容明确，不用转纯文本冒充 |
| U05 | 其余已发布格式、双书对照、书库检索与阅读设置 | 各候选功能至少一次实际发现/操作；格式支持深度分别记录 |
| U06 | TTS/查词/翻译/OPDS/同步与导出服务 | 入口、配置、成功路径（条件可用时）、无配置/离线/错误行为及远程依赖 |
| U07 | 键盘/输入焦点/中文 IME、窄屏/大字号、深色和无障碍入口 | 输入不误触导航、文字可读、焦点可达；读屏未经实际验证不写可用 |

U01～U04 与 U07 的本地可达操作必须实测；U05 要覆盖选定基线实际宣称的其他主要能力，不得只浏览菜单。U06 服务成功面若受账号/付费/设备限制，至少验证本地入口和失败面，并逐项记录成功路径缺证、影响、下一动作，不用文档/源码代替。最终报告据此提出范围/依赖决策；未完成的核心本地任务阻塞 AC-04。

这些研究观察不构成新 AutoReader 功能已通过验收；也不能用少量样本宣称全格式兼容。测性能时记录机器/构建/样本/冷热条件，未经测量只给待测项。

### 5.4 架构与迁移决策

至少比较成熟阅读引擎嵌入 AutoUI、原生文档能力扩展、必要的外部应用过渡三条路线。评估功能、Vue/VM 输入/选区/焦点/原生合成、无障碍、离线与资源、性能、许可/分发、维护和替代成本。若原生接口未经整条路径探针，只能得出候选/待验证，后续先安排最小可行性计划，不能直接宣布可用。

迁移覆盖 book_id/源版本、Locator v1 与段注释、annotation_id、缓存重建、备份与失败回退；EPUB 和 PDF 的位置语义分别处理。许可与依赖按实际版本做工程层面的来源/边界梳理，不将未核实的许可证概括成最终合规结论。

同步、TTS、翻译、网络书源与 Notes/Jade 各自标注数据流向、凭据/离线语义、实际 owner 与前置；不在本计划采购、建服务或写框架代码。设计和路线必须引用这些决策。

### 规范增量

本计划无现实现 Spec 增量：研究报告和 proposed 总设计描述候选能力，不改变运行时行为、API、数据协议或已交付承诺。因此 supersedes_spec_components/new_spec_components 均为空；不写 docs/specs、specs.json 或手工索引。后续实施计划再提出各自真实的 Spec delta；若调研发现当前 Spec 与事实不符，记 discrepancy 与 owner，不在本研究中静默改写。

| delta_id | add/modify/retire | docs/specs/... target | before/after rule | rationale | acceptance IDs |
|---|---|---|---|---|---|
| 无 | — | 无 | 当前运行时规则不变 | 仅研究与目标文档二次设计 | AC-07、AC-10 |

### 执行入口

work 首先核验 main 的实际 HEAD/WIP 与本计划 r1，记录到 baseline.md；T-00 就绪，其余按第 8 节依赖推进。001～005 为已关闭基础，不重跑/重开它们作为研究前置。上游版本、可运行 UI、服务条件与原生接缝仍是待调查事项，不能从本计划措辞推导已经验证。无额外产品实施授权或预算前提。

## 6. 测试设计

本计划为研究文档，不新增镜像实现的单元测试，不要求 AutoReader 全量回归。使用三类证据交叉验证：固定文档/源码永久链接、真实 UI 观察、AutoReader 现实现 Spec/代码。研究报告所有关键结论需定位到来源；无法交叉验证之处明确置信度与缺证。

反例至少包括：重复句选中不同出现位置；改字号/模式后回访；关闭重开后恢复；无配置/断网服务错误；受损或不支持样本的真实边界。报告不能把“按钮存在”当作“内容正确”，也不能把代码分支当作已运行结果。

检查入口：`git diff --check` 应 exit 0；逐条解析本次变更 Markdown 的本地相对链接（排除外部 URL/页内锚）应全部存在；006 ID 在活动与 archive/archived 目录唯一；任务/AC 对应、版本矩阵与两轮文档更新一致。外部源核对使用报告固定的 commit URL；UI 复演按 ui-study.md 的 U01～U07 步骤，而不是预先杜撰构建命令。

执行者先内部核对；最终复审者使用独立上下文、同一 app 检出顺序复核，角色未指定模型，不自动创建代理/chat。复审须抽查 EPUB 选择/恢复和 PDF 本地任务，以及至少一个服务限制/错误结论，并检查 UI 证据和代码实际对应。内部检查不替代最终 review；merge 在其后。

## 7. 验收标准

| ID | owner_stage | 可观察标准与验证方法 |
|---|---|---|
| AC-01 | work | baseline.md 固定上游发布、源码/子模块、文档日期与 UI 身份；实际 Git 命令/构建或发布来源可复查；若版本不同明确映射，不把主分支混充发布版 |
| AC-02 | work | C01～C07 完整盘点且吸收新增发现；每项稳定 ID、发布状态、平台/服务条件与来源；AutoOS 扩展分列，计数分母/目标建议明确，无擅自删难项 |
| AC-03 | work | code-map.md 覆盖第 5.2 节路径，关键机制具 commit/路径/符号和调用链；定制依赖与上游差异、失败/迁移/同步分支有依据，非依赖列表 |
| AC-04 | work | U01～U07 按第 5.3 节实测并留版本/输入/实际结果/截图索引；核心本地任务全部完成；服务成功面缺证具名，未运行项不标通过 |
| AC-05 | work | 每条基准功能映射 AutoReader 现有 Spec/代码或缺失，明确完整/部分/缺失/待验证/裁定排除；位置与注释迁移、Vue/VM 差异和具名缺口未遗漏 |
| AC-06 | work | decisions.md 比较三条路线，给证据、成本/风险、许可/服务/平台前置及推荐；未证原生接缝转为最小探针建议，未强行冻结引擎 |
| AC-07 | work | 调研后再次修订总设计、路线、设计入口、docs/README 和根 README；记录版本/结论/覆盖规则、假设变化与依赖，链接报告，不能只保留起草时文本 |
| AC-08 | work | report/decisions 确定首批后续计划建议：目标/非目标、owner 仓、依赖、优先级理由、验收任务、迁移与平台门；无提前编号/自动实施 |
| AC-09 | review | 独立复审绑定 r1 与实际交付 SHA，抽查 UI/源码/矩阵与二次文档，确认 AC-01～08；记录 pass/needs_fix/needs_replan/blocked，不由 work 自称终审 |
| AC-10 | merge | 仅在 review pass 后沉淀/归档，计划和导航链接正确；未改业务源码、现实现 Spec/旧 ledger 或 OS gitlink，研究证据与范围可恢复 |

## 8. 执行步骤

所有步骤未执行；下表是唯一当前任务清单。任务产物路径以第 5 节为准，不把未来闭环预先打勾。

| ID | owner_stage | 依赖 | 变更路径/动作 | 验证与预期 | AC |
|---|---|---|---|---|---|
| T-00 | work | 无 | 新增 baseline.md；检查开发位与隔离目录；需要时真实 clone Readest，固定发布提交/子模块和 UI 构建身份 | `git -C D:/autostack/auto-reader status --short --branch`；上游实际路径执行 `git rev-parse HEAD`、`git status --short`、`git submodule status --recursive`；记录实际命令和结果，无误切 WIP/链接目录 | AC-01 |
| T-01 | work | T-00 | 新增 capability-matrix.md：官方文档/发布/菜单全量清单，固定来源并标记发布与平台条件 | 逐项对照固定文档与发布；C01～C07 有条目、发现不遗漏、计数可复核；无把计划中当已发布 | AC-02 |
| T-02 | work | T-00、T-01 初始清单 | 新增 code-map.md：深读第 5.2 节机制、依赖/fork 与测试；核实构建/运行办法 | 在固定检出用 `rg --files` 和 `rg -n` 定位真实入口/符号；命令和固定 permalink 写报告，关键链路及失败面可追溯 | AC-03 |
| T-03 | work | T-01、T-02 的运行准备 | 新增 ui-study.md；执行 U01～U07，使用隔离语料和应用配置，留仓外原始证据与报告索引 | 按 UI 任务实际操作/重启/读回；核心本地任务完成，版本对应且诚实登记服务成功面缺证；不以脚本 API 写入替代用户动作 | AC-04 |
| T-04 | work | T-01～03 | 完善矩阵，对照本 app Specs 与源码；定位双端/迁移/服务缺口；核实已登记框架缺口的现状 | 抽查矩阵每行的双边来源；区分无实现与未验证、完整与部分；旧定位/注释与平台边界均有条目 | AC-05 |
| T-05 | work | T-04 | 新增 decisions.md、report.md 初稿：引擎路线、迁移、许可/服务/平台、覆盖规则与目标建议 | 三路线比较有证据；未验证机制有有界下一步，覆盖计数可重算且不掩盖核心缺口 | AC-02、AC-06 |
| T-06 | work | T-05 | 二次更新 docs/design/01-product-design.md、docs/roadmap-v0.6.md、docs/design/00-intro.md、docs/README.md、README.md | 与调研前版本 diff 可见实质结论/依赖变化，引用研究报告；本地链接全存在、`git diff --check` exit 0 | AC-07 |
| T-07 | work | T-06 | 完成 report/decisions 的首批计划建议与依赖顺序，内部核对并附工作交接 | 每个建议有范围/owner/依赖/验收与优先级依据，能据此另立计划；不预分配计划号、不开始实现 | AC-08 |
| T-08 | review | T-07 | 独立上下文复审同一检出与固定交付版本，写本计划第 9 节记录/报告 | 复演/抽查第 6 节要求、检查 AC-01～08，绑定版本；仅实际通过后记 reviewed | AC-09 |
| T-09 | merge | T-08 pass | 依 merge 流程交付/归档 006、修正活动链接并保存回执；不更新 OS pin | 导航/本地链接可用、计划状态 archived、研究文档与回执可追溯；业务/Spec/OS 范围未变 | AC-10 |

## 9. 复审记录

### 2026-11-01：new 阶段交接

- stage: new；READER-006 r1；outcome: pass；next: work。
- 交付：先期总设计/路线修订与研究合同；T-00～T-09、AC-01～AC-10 均为新建，尚未执行/验收。
- 起草自检：6 份 Markdown 的 46 个本地链接存在；0～10 节、10 项任务和 10 项验收编号完整，006 在活动/归档区唯一，下一号为 007；git diff --check 通过。这些仅证明草案结构，不代替研究或独立复审。
- 当前不是执行完成或独立复审通过；详细调研、二次设计/路线修订和后续计划建议均留在 work。
- 授权范围见第 4 节；无需重复询问是否可为研究克隆 Readest。未决技术问题由 T-00～05 负责收集证据。

## 10. 待澄清事项

无阻塞起草的用户信息。以下是研究待决问题，不要求用户先替研究者选答案：

1. 固定哪个发布/tag/源码与实际 UI 构建，主分支差异如何分列？T-00 记录并裁定研究基线。
2. Readest 实际功能深度、依赖/fork 差异、同步/迁移机制和服务限制？T-01～04 给证据。
3. 引擎路线、Vue/VM 接缝、旧数据迁移、覆盖计数/阈值与后续优先级？T-05～07 提出可审查决策；影响目标范围的变更明确留待用户裁定。
4. 如实际 UI 因安装、账号、费用或设备不可用，T-03 记录具体任务/失败证据与替代路径；核心本地任务未完成则不能声明 AC-04 通过。不得静默用源码分析替代实际体验。

### 2026-11-01：work 阶段交接（T-00～T-07 完成）

- stage: work | plan_id: READER-006 | plan_revision: r1 | outcome: pass | worktree: D:/autostack/auto-reader（main，计划 §2 指定开发位，无 app worktree） | branch: main | base_commit: d39c255 | code_commit: 7d0f760 | dependency_revisions: readest=3cc39ad7(v0.12.16, detached)+submodules per tag（baseline §2） | task_ids: T-00,T-01,T-02,T-03,T-04,T-05,T-06,T-07 | evidence: docs/research/readest/*(5 报告)+baseline/ui-study 摘要+plan-artifacts/plan-006/(原始记录) | blockers: 无阻塞 | next_responsible_role: review（T-08 独立复审）
- 交付：①baseline.md（clone/tag/子模块/portable SHA256/隔离机制/命令实录）；②capability-matrix.md（259 行=255 发布分母+主分支候选，33 行 ✓实测，AutoReader 列受控词表 1 完整/36 部分/116 缺失/102 待验证/4 排除-需裁定）；③code-map.md（498 行，12 链路/12 格式/fork 差异/24 服务，path:line 于 tag）；④ui-study.md（U01~U07 真机：核心日用链路全绿——精确选区/CFI 锚/重复句搜索恰 3 结果/重开恢复/导出深链；2 个 Windows 0.12.16 缺陷实证；IME/窄窗移动布局/本地 TTS；服务成功面缺证具名）；⑤decisions.md（三路线裁定=B 主干+A 有界探针+C 长尾过渡；迁移=字段扩展+逐字锚保留；P1~P6 建议）；⑥report.md（假设核对/计数规则/不预宣比例）；⑦二次修订 design/01（coverage v2）+roadmap+00-intro+docs/README+README。
- 提交链：d39c255(计划)→14d1689/346c7de(T-00)→ccd08a0(T-03)→8213092(T-01/02/04/05)→a68b4fe(链接修复)→7d0f760(T-06)；internal check：git diff --check=0、本地链接 134/134 存在、006 活动区唯一（archive 0）、矩阵行数=清单行数（agent 复核）。
- 工作授权：/goal 继承（含 clone Readest）；证据在 plan-artifacts/plan-006/（runlog+notes+screens），merge 时按政策合并进计划文件并删除。
- 未完成属下阶段：T-08 review（AC-09：独立上下文复核 AC-01..08，抽查 EPUB 选择/恢复与 PDF 本地任务+一个服务限制结论）、T-09 merge（AC-10）。移除确认复现 2 次未删已登记为复审抽检项（ui-study §1）。

- stage: goal | plan_id: READER-006 | plan_revision: r1 | round: 1 | from: work | to: review | status: archived (work pass, 8/10) | outcome: pass | worktree: D:/autostack/auto-reader (main, 计划 §2 开发位) | commit: eaee1cc | next: review

### 2026-11-01：T-08 独立复审（review_scope: final，r1 @ 432ce21）

- stage: review | review_scope: final | reviewer_identity: 双独立新上下文复核（R1=文档/AC 审计 44 次工具调用；R2=真机 UI 复现 89 次调用），编排会话汇总裁定；模型/会话 ID 未暴露（限制如实登记） | plan_id: READER-006 | plan_revision: r1 | outcome: **needs_fix**（0 blocker / 2 major / 6 minor + 4 条措辞修正） | worktree_path: D:/autostack/auto-reader | branch: main | reviewed_commit: 432ce21 | base_commit: d39c255 | dependency_revisions: readest 3cc39ad7 (v0.12.16, clean) | spec_inputs: 无 Spec 增量（计划 §规范增量=无；diff 范围核实未触 docs/specs、ledger、OS gitlink）
- **AC 证据图**：AC-01..AC-08 全部 pass（R1 审计：基线 git 事实可复算、矩阵 259 行与清单逐一对应、code-map 12 引证 10 精确 2 漂移、26 截图全在、映射抽查 25+ 行无虚构、三路线/探针/建议完备、五文档实质修订、P1~P6 无早取号）；R2 真机复现 4/4 REPRODUCE（EPUB 选择→黄色高亮→落盘 cfi→重开恢复；PDF 打开/翻页/缩放，弹层未现与"未验证"记录一致；翻译禁用门；软删书架一致性）。
- **Findings**（详见 plan-artifacts/plan-006/notes/review-r1-docs.md + review-r2-ui.md）：
  - RV-D02 (major, AC-01)：portable exe SHA256/下载 URL 无归档原始记录（文件+大小旁证在）。
  - RV-D03 (major, AC-02)：发布分母 255 不可由矩阵推导（仅 2 行非 released，可推导值 257；分域和 259 与 255 括注不自洽）。
  - minor：RV-D01 gstack 哈希笔误（a3259400）；RV-D04 §11.2「30 条」应 31；RV-D05 两处行号漂移（section-chunks.js:13、Annotator.tsx:1607-1617）；RV-D06 runlog 缺 U04-U07 逐条记录；RV-D07 重复截图组未标注；RV-D08 三导航文档 7/10 应 8/10。
  - R2 措辞修正：高亮渲染为分页器 shadow-DOM SVG overlay（非 iframe span）；重复高亮幂等去重；「应用到所有匹配」本次未现（存疑样本登记）。
- evidence: notes/review-r1-docs.md、notes/review-r2-ui.md、screens/review-*.png(15)、check_links 134/134、git diff --check=0 | pending_closeout_gates: 无（研究文档计划，§6 检查已由审计覆盖） | next: work（有界修复 RV-D01..D08 + R2 措辞，随后 AC-01/02/04 受影响面 targeted re-review，pass 后 T-09）

### 2026-11-01：T-08 修复轮（work，needs_fix → 闭合）+ 受影响面 targeted re-review（final pass）

- stage: work（修复） | plan_id: READER-006 | plan_revision: r1 | outcome: pass | task_ids: RV-D01..D08+R2措辞（12 项全闭） | code_commit: 见本回执后首个提交 | evidence: exe-provenance.md（哈希两次独立计算同值 683a620d…）+ 各文件定点修正
- 修复映射：RV-D01 baseline gstack=`a3259400a366…`（R1 实测值）；RV-D02 evidence/exe-provenance.md 归档哈希+URL+两次计算，baseline §4 指向之；RV-D03 分母改 **257=259−2**（逐行点名 C04-010 主分支/C05-035 code-only；255 宽估废止），matrix §11.2+report §1/§2/§3+design §1/§8+roadmap+两 README+00-intro 全部对齐；RV-D04 31 条；RV-D05 两引证按 R1 实测值改（section-chunks.js:13、Annotator.tsx:1607-1617）并注校正；RV-D06 runlog 补 U04~U07 逐条记录 + ui-study §0 覆盖说明；RV-D07 重复截图组+PDF 单帧证据如实注记；RV-D08 三导航文档 8/10；R2 措辞：高亮渲染=分页器 shadow-DOM SVG overlay（新行）+幂等去重（新行）+「应用到所有匹配」存疑样本注记。
- stage: review（targeted re-review，AC-01/02/03/04 受影响面） | review_scope: final（闭合复核） | outcome: **pass** → **reviewed** | 复核方式：修复项逐一比对 R1 实测值；两处改后引证由本会话在 tag 检出直接重读（section-chunks.js:13=CHUNK_ATTRIBUTE ✓、Annotator.tsx:1607=BookNote 字面量起点 ✓）；残留「255」仅存 d39c255 哈希与 matrix 废止说明（非主张）；check_links 134/134 ALL OK；git diff --check=0 | findings: 无新增 | next: merge（T-09）
- 计划状态：executing → **reviewed**（r1 @ 098cde5）。

- stage: goal | plan_id: READER-006 | plan_revision: r1 | round: 2 | from: review | to: merge | status: archived (T-08 needs_fix repaired, targeted re-review pass @ 098cde5) | outcome: pass | worktree: D:/autostack/auto-reader (main) | commit: 098cde5 | next: merge

### 2026-11-01：T-09 merge 沉淀与归档（READER-006:r1）

- stage: merge | plan_id: READER-006 | plan_revision: r1 | outcome: pass | delivery_commit: main 线性链 d39c255..2e0600c（计划 §2 开发位=独立 clone main，无 worktree、无分支着陆；研究提交即交付链） | canonical: **无 Spec 增量落地**（计划 §规范增量=无，supersedes/new 均空；approved no-impact：研究报告描述候选能力不改运行时行为——T-08 已核实 diff 范围未触 docs/specs、.autoos ledger、OS gitlink） | archive_path: docs/plans/archive/006-readest-deep-research.md
- 检查点：**prepared** = reviewed 基线 2e0600c（修复轮 098cde5 之后）、无 Spec diff、交付=既有 main 链；**landed** = 交付链本就在默认分支（`git log --oneline d39c255..2e0600c` 线性、无 merge commit），main tip 即交付头；**canonical_verified** = no-impact 结论（上栏）+ 研究产物五文件路径 docs/research/readest/{baseline,capability-matrix,code-map,ui-study,decisions,report}.md 在 landed 提交内（134/134 本地链接核验）；**archived** = `git mv` 至 docs/plans/archive/ + status: archived + 导航四处改链（docs/README、roadmap、00-intro、根 README）+ current_step 10/10；**cleaned** = 无 worktree 可拆（`git worktree list` 仅主检出；计划 §2 明示无 app worktree）；plan-artifacts/plan-006/ 证据折叠（本节+§9 全回执+docs/research/readest/ 耐久摘要）后整删，registry 刷新，无具名 holds。
- 证据折叠去向（merge 后恢复研究结论所需的最小集）：研究耐久摘要 = docs/research/readest/ 五文件（含全部截图索引与运行方法）；原始运行记录 = 本计划 §9 各回执（work 交接/review/修复/本节）；上游复检 = baseline §2 命令（可重放）+ `D:/autostack/readest`（detached v0.12.16 检出，**保留在 plan-artifacts 作用域之外**，报告 §6 复演入口引用）；portable exe 重新获取 = evidence/exe-provenance.md 内容已折入 baseline §4（SHA256+URL+大小），exe 本体随作用域删除（92MB，可按 provenance 重下载）。
- Landing checks（Landing ≠ 部署）：本计划纯文档（0 行 src/ 改动，T-08 diff 核实），无构建产物/运行进程需要刷新；主检出 clean。批量回归到期检查：auto-lang 规则不适用本仓（无 .last-batch-regression.json 机制），N/A。
- completion_kind: delivered | 后续入口：P1~P6 建议待用户认可后另立计划取号（decisions §5）；遗留待人工复核项（Readest 上游侧，非本计划义务）：移除确认未生效复现×2、PDF 标注弹层、顶栏书签按钮——均已在上游 ui-study 如实登记，不阻塞本计划交付。
