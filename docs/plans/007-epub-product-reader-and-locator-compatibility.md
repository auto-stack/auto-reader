---
plan_id: READER-007
status: executing
feature_name: 正式EPUB阅读表面接入与定位兼容
author: [Codex]
created_at: 2026-11-03
updated_at: 2026-11-03
plan_revision: 1
current_step: 2
total_steps: 13
base_branch: main
base_commit: 28c765a4dbf66a3482f5bc03d4cb5c64d792c394
depends_on: [auto-ui/PLAN-029, READER-001, READER-002, READER-003, READER-005, READER-006]
supersedes_spec_components: [docs/specs/reader/epub-reflow.md, docs/specs/reader/reading-annotations.md, docs/specs/reader/real-library.md, docs/specs/reader/standalone-reading.md]
new_spec_components: [docs/specs/reader/epub-engine-reading.md]
touched_goals: []
---

# READER-007：正式EPUB阅读表面接入与定位兼容

## 0. 变更摘要

在029原生输入与必要接缝全部交付后，把026/029实验链路接入**正式书架与reading_page**：真实受管EPUB→保留出版物结构的阅读表面→目录/图片/脚注/分页滚动→真实精确选区/行内高亮批注→产品级定位保存/冷恢复，并兼容既有章段定位与注释。它是EPUB阅读产品化第一期，不是另一份探针，也不承诺一次覆盖Readest全部格式/设置。

当前仅起草，drafting/r1、0/13，**依赖未就绪，不实施**。用户确认先起草条件性后续计划。本地核查029仍executing、9/12，最新回执有Vue重排GAP、原生冻结验收/独立review/交付未闭合；这不是029已完成的证明。本计划不修改029状态、标准或他人WIP，实施前以正式验收与交付回执为准。

## 1. 目标

1. 从正式书架打开真实EPUB，不进入tests/probe、不需手动注入JS或启动旁路服务，即可阅读结构/基本样式、目录、图片和脚注，切换分页/滚动与字号后保留内容位置。
2. 产品UI中精确选择重复句指定一处及跨行/跨段范围，创建/回访/编辑/删除高亮与批注，导出带稳定来源与可恢复定位的Markdown。
3. 形成有限而真实的Locator v2合同：书/源版本/资源身份、引擎CFI/range与原文核验，支持冷恢复/失配和现有v1记录兼容；不制造假CFI、伪迁移或第二套永久书库。
4. 正式Vue与原生VM产品路径均验收，包含重排后真实选区和回访、输入/无障碍/生命周期及旧TXT/Markdown回归；继承029的严格必需清单和独立review要求。

非目标：PDF/漫画/Kindle格式、竖排/复杂公式/所有出版物CSS、TTS、双书对照、同步/书源/Notes真实交接、系统深链注册、Linux/移动、全面书库重做、复制Readest账号/React/Tauri。旧EPUB最小阅读路径保留兼容与诊断用途，不以新表面失败后静默退回纯文本冒充新功能成功。

## 2. 架构方案

**主导仓auto-reader**：主改面是正式阅读页、资源服务与产品数据/Locator兼容，唯一合同在本仓。UI只留消费指针，不再为本计划重复取号。主检出main的D:/autostack/auto-reader为唯一实现/内检/顺序复审位，一app一写入者；执行前先确认029消费工作已停止且无他人WIP，不stash/reset/切走他人变更，不在AutoOS子模块开发。

| 仓 | 责任与边界 |
|---|---|
| auto-reader | .at正式书架/阅读页/后端API、受管资源、产品会话与Locator v2、注释兼容/导出、应用自有固定引擎adapter及双端UI验收 |
| auto-ui | 作为029已交付的文档表面/输入/焦点/几何/无障碍能力提供方；本计划只消费已证固定接口，不预先取得UI源码写入权；独立框架缺口另立实际owner最小前置 |
| auto-lang/auto-web/auto-man | 固定只读语言/HTTP/CLI依赖，记录source/tool/锁；不把未知运行时缺陷绕过成产品已通过 |
| Readest/foliate-js | 固定006/029引擎来源与许可/依赖清单；不在只读D:/autostack/readest修改，不依赖其活动工作目录或从网络临时取main |
| AutoOS | README归属反链及未来精确提交装配，不在本计划改shell/manifest/gitlink或系统URI |

正式前端继续AutoUI，业务纯.at；引擎JS/CSS是固定资产和受控文档adapter，不承接书库/注释业务、不直接写用户文件。数据仍由Reader真实API拥有。禁止修改生成Vue/Rust交付；浏览器侧不能只由Playwright注入实验adapter后宣称产品已接入。

## 3. 技术栈

沿用当前 .at library/api/annotations/reading_page、固定foliate-js fork、029交付的原生文档表面与Vue挂载接口、应用自有资源服务、Playwright与原生真实UI/系统无障碍证据。具体表面语法、事件/URL契约、原生启动命令与cohort须从029正式交付核实，不从未落主的worktree推导稳定公共API。

029在执行回执中发现原生入口可能为merged `auto run -r vm`，而`-r vm --server=vm`在其cohort仅启动后端；现有Reader正式页面依赖HTTP。**不能把这个差异留到产品验收时才发现**：T-00先验证正式Reader的真实后端/窗口/HTTP可达与输入链，固定可用的启动profile；如需框架前置，明确依赖后阻止后续实现，不照抄旧命令或用独立Rust宿主替代。

## 4. 需求分析与背景调查

### 授权与依赖状态

2026-11-03用户要求规划029之后的计划。核查发现本地029未有最终交付回执，用户回复“OK，那先起草吧”，明确允许先起草并保留029全门通过/独立复审/固定版本交付前置。本次仅Plan、proposed设计/路线与导航文档，不实施、不修029、不修改当前Spec或已有probe驱动。未指定预算/模型/代理，不虚构授权、不创建代理/chat。

本地观察（起草时，非最新全局状态保证）：UI主检出223b5d7f0e939b91ba3bab3c9409b5bca9487c98；029实施树98633fd4仍在，Plan头executing、9/12，未查到新native-input canonical Spec或最终独立review/merge；Reader前序HEAD e6d3d41，读取期间推进到28c765a4，main仍有tests/probe/engine_surface/driver_vue.py他人WIP，**全部保留**。活动Reader无同需求Plan，号源007独占分配，UI已有033等计划不接管。

029已有输入根因/真实VM接入/部分门的证据；旧R-05当前cohort已不复现、R-06vm夹具被驱动重建覆盖的问题已有测试修复回执。然而Vue重排GAP、焦点配对证据、DPI/完整冻结跑及final review仍需按029合同闭合。本计划依赖Ready必须核对029全部AC实际结果与source/tool/engine版本，不能仅看步骤数字或自动接受同会话复跑为独立review。

### 现实现与源码事实

- [EPUB Spec](../specs/reader/epub-reflow.md)：30MiB输入、4096 spine、12MiB单章/资源，受管原件+惰性章缓存；章XHTML转换为文本/图片行，自定义章段Locator v1，不是保留DOM/CSS的阅读引擎。
- [注释Spec](../specs/reader/reading-annotations.md)：v1单段quote+段内occurrence、稳定annotation_id、严格校验与备份/暂存/读回；高亮为段级标记。跨段选区不能编造para_idx或塞入单段quote使其“兼容”。
- [真实书库](../specs/reader/real-library.md)：章/段/逐字全文锚与严格jsonx读写，坏文件保留、不假恢复；跨书/源版本及百分比语义不能放宽。
- src/front/pages/reading_page.at为正式路由/目录/搜索/注释/偏好消费；src/back/{api,db,library,epub,annotations,jsonx}.at为真实数据面。probe应用另有独立注册/会话/sidecar，**不能原样挂到正式书页就算产品化**。
- tests/probe/engine_surface/assets/engine-adapter.js有固定引擎选择/资源/回传实验；重排订阅与DOM生命周期问题正在029修复，产品adapter须消费交付版本，不复制旧bug或通过驱动兜底。

| 起草源 | SHA256 |
|---|---|
| src/front/pages/reading_page.at | 1a6d4af8daf8b653a1994ed03c343d8dc8dce741b81b748a61ecb7c54cdcf325 |
| src/back/annotations.at | 9f8eb72ad0093ea1ad69e7c1eb4f0bd88993f7c82632084e597a16c02183d2c7 |
| src/back/library.at | 3c095d0a01ff9b99a34ffa5523780684afbbf73a8bdd3d4cbe264a606b612c36 |
| docs/specs/reader/epub-reflow.md | 8e74c12222a3cf1be6ac9ba2107ae69406efefd3d45c1da71c13d7550eb120a7 |
| docs/specs/reader/reading-annotations.md | c2ace0e4b9de7486d6bae4921662484e22bbe03cc16abbac5c3d182aefbb766b |

## 5. 详细设计

### 5.1 实施准入（先于产品代码改动）

T-00核实029：必需用例全集/无GAP或未运行/独立上下文final review/pass/精确落主源码与CLI/tool/engine cohort齐备，原生与Vue正式启动路径能消费所交付接口。029原合同若发生修订，必须核其真实授权与证据，不默认标准已降低。任一项未满足，记录dependency_not_ready，**不启动T-01及后续实现，也不替029补签完成**。

在可核实cohort上，用本app而不是probe独立窗口确认书架→阅读页→后端可达与焦点/输入/重排基本接缝，冻结表面接口和消费者入口。如真实正式应用组合比029实验profile多出框架缺口，按owner另立最小前置；Reader不擅自在其他仓写代码。

### 5.2 产品profile与真实入口

无DRM重排版EPUB第一期支持：正文结构与基本出版物CSS（标题/段落/强调/列表/简单表格/代码块）、内置/受管图片、目录/跨章与脚注往返、单列分页与连续滚动、应用字号/列宽/主题、精确选区/高亮/批注和恢复。复杂版式/竖排/公式/任意CSS兼容不计本期整行完成，不能静默丢内容而显示已支持。

保留既有30MiB导入、4096 spine、单资源/章12MiB及TXT/MD门，不将026/029的≤1MiB实验上限当产品上限。T-01必须在实施前冻结引擎解压/总资源/图片像素/布局与装载/回传/冷恢复预算，区分产品支持、资源拒绝、损坏与环境错误，覆盖边界两侧合法/拒绝对照；无法满足既有已支持输入时显式回规划，不能暗降配额。选区事件继承32KiB UTF-8上限，不静默截断用户摘录。

书架/正常路由进入页面时自动装载应用自有固定资产与受管原件，默认本地离线可用；不依赖tests/probe目录、D:/autostack/readest、PROBE_DATA_DIR/PROBE_ASSETS_DIR或驱动注入。资源服务只允许本书受管内容及固定引擎资产；书内活动脚本、远程自动加载、DTD/外部实体/跨书路径继续拒绝。可信引擎脚本与不可信出版物内容隔离，须证明浏览器引擎没有绕过现有解压/资源边界。

### 5.3 Locator v2与兼容（先冻结协议，后写数据）

不预定“加cfi/page字段”就是完成。T-01比较至多两种可兼容存储/协议方案后冻结版本化合同：区分legacy_paragraph与epub_range，包含book_id、source_hash、resource身份、引擎locator/CFI与逐字quote/上下文、明确作用域的出现序、engine/schema版本；展示百分比不作为主键，UTF-16/字节/字符偏移不裸混传。ReadingState版本、注释版本与书籍import_version分别管理。

CFI须真实解析并与对应文档原句/出现位置核对；检查epubcfi前缀或“quote在全书某处存在”不能证明指定范围正确。CFI指向另一处重复句但quote相同的反例必须被恢复/核验oracle识别，不能靠引擎自报的occurrence直接接受。运行期校验责任与可信转换接缝由T-01固定；若无可靠机制，则不能先写已验证定位、留以后再补。

v1阅读状态/注释继续可读与回访，annotation_id、quote、comment、tags、created_at等不因换引擎改变；只在能证明唯一映射时生成可选v2锚，无法映射保留v1与明确状态，不伪造CFI、不整库强制改写。跨段新选区用真正range表示，不能塞进一个伪段号。新客户端按明确版本读取新记录，旧协议不认识的新形态不得误解为v1或静默丢字段。

落盘沿已验证的备份/暂存/提交/读回纪律，不声称现有原语没有证明的断电原子性；写/迁移失败保留原文件/原注释，损坏/空文件/未知版本具名拒绝与恢复建议。坏源版本、无目标、多义或quote失配显示needs_relocate，原摘录保留，不静默跳第一处/删注释。完成数据协议与oracle后才能开放UI写入。

### 5.4 正式阅读交互

真实书架导入/打开EPUB→目录/脚注往返→改字号/分页滚动→真实选重复句指定一处→高亮/批注→搜索命中回访→编辑/删除/导出→正常退出/异常退出→冷重开恢复。选择工具条和侧栏归应用控制；正文高亮由引擎range渲染，输入框/IME不被翻页快捷键抢占。不能由HTTP预写注释、JS直接Range赋值或手工设置文件代替创建/保存用户动作。

书内搜索继续精确子串基本语义与truncated诚实提示，新表面必须把命中映射到真实范围并可回原处；跨书索引/语义搜索不纳入。导出保留现有书源/annotation_id/原句/批注，并增加版本化格式定位信息；不擅自登记auto-reader://或声称系统深链可用。

遗留兼容路径仅在用户明确选择/状态可见时使用，不能在新引擎失败时自动回纯文本显示“已恢复/保存成功”。TXT/MD走已有路径，测试证明其数据/定位/注释无回归。新引擎页面隐藏、换书、关窗口/崩溃后清理会话/进程/端口，旧事件不能写入新书。

### 5.5 证据与规范增量

未来新增 tests/product/verify_epub_product.py（T-02建立）统一 `--profile vue|vm --auto-bin <固定auto> --out-dir <自有隔离>`，从正常产品UI驱动，不调用probe专用写端点；复用而非抄造既有语料/进程/oracle。新profile用例注册唯一ID并核非零选择、无缺项/GAP/not_run才exit0；真实错锚/资产变异使原oracle失败非零，恢复后转绿。

| delta_id | add/modify/retire | docs/specs/... target | before/after rule | rationale | acceptance IDs |
|---|---|---|---|---|---|
| SD-01 | add | docs/specs/reader/epub-engine-reading.md（新） | 文本行最小profile → 本期正式引擎阅读入口、支持/资源/安全/会话/双端启动边界 | 不将实验样本等同产品或全CSS | AC-02/03/04/07/09 |
| SD-02 | modify | docs/specs/reader/real-library.md | 仅v1恢复 → 版本化格式Locator/ReadingState与v1兼容、失配/写失败语义，保留原有规则 | 数据迁移可核验 | AC-04/05/08 |
| SD-03 | modify | docs/specs/reader/reading-annotations.md | 单段注释 → v1兼容+精确range新形态、行内显示/回访与版本化导出 | 真选区不是伪段锚 | AC-04/05/06/08 |
| SD-04 | modify | docs/specs/reader/epub-reflow.md | 最小profile现状 → 保留其兼容语义并链接正式引擎支持/资源边界，不回写历史已支持 | 能力范围诚实 | AC-02/03/07 |
| SD-05 | modify | docs/specs/reader/standalone-reading.md | 005冻结入口/成绩 → 新产品profile、固定工具/启动形态与永久验收入口，历史成绩单列 | 不用旧全绿代替新cohort | AC-01/09/10 |

当前只提出delta，不修改canonical Spec/旧ledger/index。执行原始材料为plan-artifacts/reader-007/auto-reader/自有scope，必要决策/协议/用例/来源与结果摘要折入本计划或新增 docs/design/02-epub-engine-reading.md（T-01/T-10形成，proposed到落地状态据实），不把本机截图绝对路径当唯一证据。

## 6. 测试设计

未来必需P-01～12，owner_stage=work；统一入口由T-02建立并随实现接入。Vue与原生分别走正式app UI，数据/API/磁盘作为独立读回，正常保存不预写。系统输入/无障碍可用性沿029真实交付标准，不复用其旧截图当新应用通过。

| Case ID | AC / 建立任务 | 输入/状态 | 区分性断言与覆盖边界 |
|---|---|---|---|
| P-01 | AC-01；T-00 | 029交付cohort+正式Reader启动，两端实际window/route/backend | 全部029门与独立review/交付可核，Reader自身窗口/工具同源；依赖未就绪则停T-00，不造已完成 |
| P-02 | AC-02/03；T-02/03/04 | 正常书架导入/打开，断网、移走probe资产路径后重开，目录/图/脚注/正文结构 | 产品入口自动挂载固定资产，真图与目标原文、跨章往返正确，不靠tests目录/外窗/JS注入 |
| P-03 | AC-03/07；T-04/08 | 分页/滚动、字号/列宽变化、隐藏显示后重新选指定范围 | 重排前后同内容锚、真实拖选可回传，图/浮层/命中不跑位；专门复现029的Vue重排订阅风险 |
| P-04 | AC-04/06；T-05/06 | 重复句第2处、中文emoji跨行/跨段范围→高亮/批注→编辑/删除 | CFI真实解析位置+quote/作用域occ匹配独立oracle，非整段/伪段号；annotation_id稳定 |
| P-05 | AC-05；T-05/07 | 完整旧v1库、章书签、重复句/未知字段边界、可映射与不可映射/多义记录 | 旧ID/元数据保留，唯一映射才生成v2，失败保留v1；TXT/MD不被改写，无强制整库迁移 |
| P-06 | AC-04/05；T-07/08 | 真实保存后正常退出/强退，新进程换布局恢复；旧/新混合记录 | 同一源版本/范围且目标在pane可见；百分比、quote在任意处或CFI前缀检查不能通过 |
| P-07 | AC-06；T-07 | 搜索重复句→每个命中跳转→回访注释→Markdown导出 | 结果位置各自对应、导出原句/批注/ID/源版本/格式locator可独立解析；无系统scheme注册承诺 |
| P-08 | AC-04/07；T-08 | 配对CFI指另一处重复句、错book/hash/session/stale事件、错quote、源改版 | 校验/恢复明确失配且零错误写入，不跳第一处；合法同类型对照仍成功，不能只靠类型错误拒绝 |
| P-09 | AC-02/07；T-02/08 | 30MiB与单资源等profile边界两侧、坏zip/超额/脚本/远程URL/跨书路径 | 继承导入门和冻结引擎预算实际受控，合法长书可用；拒绝具名无半写，不执行出版物脚本/外部读取 |
| P-10 | AC-05/08；T-05/08 | 迁移/新记录写失败、坏/空状态文件、只读目录、重开 | 原记录/文件/备份可核，不报假保存/空库；未知版本诚实拒绝，恢复后合法写仍成功 |
| P-11 | AC-07/09；T-08/09 | 两书/两实例并存、换书/关闭/迟到事件、IME/焦点/系统无障碍/geometry | 不串书/串注释，关闭只清自有树和端口，B继续可用；真实产品页具备029系统接缝，不能靠独立probe代替 |
| P-12 | AC-09/10；T-09/10 | 新旧双端门；缺case/GAP/错工具/占口；真实资产或locator变异→还原 | 必需集合完整且全PASS才exit0；变异使原oracle真红非零→还原绿，旧TXT/MD/EPUB最小门通过，无吞失败/改预期 |

语料先复用006/029合成集，再新增至少一组可再分发的真实EPUB及不同内容结构/重复句/跨段/长章/损坏与资源边界样本；准确清单/许可/hash与预期由T-01/T-02冻结，拟语料不计已执行。兼容门包括现有 `tests/basic/verify_standalone.py --profile vue|vm`、`tests/annotations/verify_local.py --profile vue|vm`、EPUB/Library定向规格及现有原生应用任务；新门不能删原oracle或用HTTP绕过写UI。

本仓纯app修改不在auto-lang跑cargo/docs_gen；框架已交付版本不重复全仓回归，必要新框架修复另走owner合同。每次证据绑定实际source/CLI/tool/engine/运行profile，测试0选择/环境缺口保持未通过。

实施者内检只说明可交review，final必须独立上下文、同一clone顺序复演P-04/05/06/08/10/13及真实双端输入链。未指定模型，不自动派代理/建chat；执行review时暂停实现写入，不将自己复跑称独立review。

## 7. 验收标准

| ID | owner_stage | 可观察完成条件 |
|---|---|---|
| AC-01 | work | 029全部必需门/独立final review/精确交付source与工具齐备；P-01正式Reader启动/接口组合已验证，依赖不齐不启动下游实现 |
| AC-02 | work | 固定支持/资源/安全与语料profile；正式书架→引擎自动装载，离线且不依赖tests/probe/兄弟Readest目录，保既有导入边界 |
| AC-03 | work | 正式双端目录/图/脚注/基本结构样式、分页/滚动与字号/布局后真实位置和选区可靠；不宣称全CSS/全格式 |
| AC-04 | work | Locator v2真实身份/CFI-range/quote/出现位次验证和精确选择正确；错CFI对同句其他出现位置能被识别；跨段不伪装单段 |
| AC-05 | work | v1/v2混合兼容、稳定ID/注释元数据、映射失配/备份/失败回退与正常/强退冷恢复成立，TXT/MD无数据回归 |
| AC-06 | work | 真实产品UI高亮批注创建/编辑/删除/回访、搜索位置与Markdown来源导出完整，输入/IME不被导航抢占，不用API预写替代 |
| AC-07 | work | 双端产品页的安全拒绝、源版本/会话/迟到、双实例、隐藏/geometry/系统无障碍与清理符合冻结合同，不能借新引擎绕过边界 |
| AC-08 | work | 迁移/写/损坏失败零丢失、不假成功，独立内容/字节读回与合法对照可复现；坏文件/未知版本不默清空 |
| AC-09 | work | 新产品永久门两端逐例全通过、反例真实非零、旧APP门含TXT/MD/旧EPUB兼容全绿；GAP/未运行/缺case不计PASS |
| AC-10 | work | SD-01～05及设计/路线/导航/能力矩阵基于实际证据，矩阵只更新本期达到的RDT子范围，历史probe/旧成绩不冒充新产品完成 |
| AC-11 | review | 独立上下文final review绑定r1与交付cohort，复演规定反例与兼容/恢复任务，AC-01～10均PASS后才reviewed |
| AC-12 | merge | 精确提交/landing、canonical核验、归档/流程计数/链接与自有材料恢复摘要真实闭合；旧计划/他人WIP/OS组合pin不被接管 |

本期映射RDT-C02-001/002/009/025/026、C03-001/002/003/020及EPUB格式的限定子范围；不把颜色/公式/跨页等未达到的整行标完整，不宣称覆盖百分比。全部work门通过才execution_done，独立review后才reviewed，merge真实闭合才归档。

## 8. 执行步骤

所有步骤均未执行；本计划当前依赖未就绪，先等待029真实完整交付。

| ID | owner_stage | 依赖 | 路径/动作与产物 | 验证入口与预期 | AC |
|---|---|---|---|---|---|
| T-00 | work | 029全门/独立review/固定交付 | [x] 在Reader main核WIP与依赖cohort、正式启动/表面/HTTP接口；确认029实验与产品组合差异——见§9 2026-11-03 T-00记录 | P-01、source/tool/hash/窗口/后端事实齐；029欠项或正式组合不通则dependency_not_ready，后续不实现 | AC-01 |
| T-01 | work | T-00 | [x] 新docs/design/02-epub-engine-reading.md冻结profile/资源/CFI核验owner、至多两方案比较后的v2存储与兼容/迁移契约——见§9 2026-11-03 T-01记录 | 实际源码/接口对照、v1/v2合法/失配/写失败样例和预算边界有oracle；不先造空字段 | AC-02/04/05/08 |
| T-02 | work | T-01 | 新tests/product/verify_epub_product.py与版本/语料清单、独立oracle；应用固定引擎资产来源/许可/打包方案 | P-01～12注册唯一ID、0/缺项/GAP非零；语料生成/hash与预期可重算，未实现例不伪绿 | AC-02/09 |
| T-03 | work | T-02 | src/back/api.at/db.at/library.at等接产品资源/会话，新增产品adapter/固定资产路径按T-01确定 | 正式UI自动装载，原件/资源受控，断网和移走probe目录仍用；P-02/09合法/拒绝对照 | AC-02/07 |
| T-04 | work | T-03 | reading_page.at与必要组件接真实引擎、目录/脚注往返、图/基本结构与分页/滚动/设置 | P-02/03双端正常产品路由，重排后真实选区仍能回传，不靠driver注入 | AC-03 |
| T-05 | work | T-01/04 | library/annotations/jsonx及新增locator模块（T-01定路径）实现版本化读写/核验、兼容与恢复 | P-04/05/06/08/10；v1不假迁移，跨段/重复句/CFI真实一致；失败保留旧文件 | AC-04/05/08 |
| T-06 | work | T-05 | reading_page/annotation产品UI选区工具、高亮批注CRUD/回访 | P-04产品真实UI→.at→落盘→回访，稳定ID/逐字原文、输入不抢键，无HTTP预写 | AC-04/06 |
| T-07 | work | T-06 | 搜索范围跳转、v1/v2恢复与Markdown导出，兼容旧入口 | P-05/06/07各次重复命中分明、导出来源可独立解析、旧/新冷恢复不串书 | AC-05/06 |
| T-08 | work | T-07 | 安全/资源/跨实例/隐藏/输入/无障碍/生命周期、写失败/迁移回退与变异负例 | P-08～11实际合法/非法对照和原oracle红→还原绿，预算/系统接缝实证，失败不转纯文本假成功 | AC-07/08 |
| T-09 | work | T-08 | 固定最终cohort跑新永久门与旧APP门/定向规格，修实际缺陷不弱化门 | 新 `python tests/product/verify_epub_product.py --profile vue|vm --auto-bin ... --out-dir ...`由T-02建立；新/旧门两端完整PASS，0漏项/GAP | AC-09 |
| T-10 | work | T-09 | 落SD-01～05与README/设计/路线/矩阵实际状态，内检并交独立上下文final review | git diff --check、本地链接/范围/cohort一致；内检不自称终审，所有工作门有闭合证据 | AC-10 |
| T-11 | review | T-10 | 同一clone独立上下文复演第6节要求，绑定计划/源码/工具 | AC-01～10全PASS才reviewed，否则needs_fix/needs_replan回work，不能partial交付 | AC-11 |
| T-12 | merge | T-11 pass | 精确交付/主干canonical/归档与导航、自有scope清理与恢复回执 | 实际landing/Spec/档案状态一致，无他人WIP/用户数据损伤；不更新OS组合pin | AC-12 |

**计数说明**：T-00～T-12共13项，total_steps=13、current_step=已完成执行任务数（T-00 后=1）。work拥有T-00～10，review/merge分别拥有T-11/T-12，不为凑执行完成先勾未来阶段。

## 9. 复审记录

### 2026-11-03：work阶段——T-01 设计冻结（AC-02/04/05/08）

- stage: work | plan_id: READER-007 | plan_revision: r1 | task: T-01 | outcome: pass（docs/design/02-epub-engine-reading.md 冻结）| 执行位: D:/autostack/auto-reader main | next: T-02。
- **冻结内容**：①产品 profile（支持/非本期/装载/启动 profile/表面接口/引擎）与受管资源安全边界、引擎预算（继承 30MiB/4096/12MiB + 15/5/30/10/600s + 32KiB 选区上限，产品化不降配额）；②**Locator v2 方案甲（同文件版本化）**冻结——annotations 带 v2 锚的书升 version:2（v1 字段不变 + 记录可选 `locator` 对象），reading 状态可选顶层 `locator`；方案乙（独立 locators 注册表）经比较否决（旧客户端重写丢 locator_id 引用→孤儿条目，双文件原子性负担）；③locator 对象 schema reader-locator v1：kind(epub_range/legacy_paragraph)、book_id/source_hash/resource(spine_index+href)、engine(name/revision)、range(start/end CFI)、quote/context、occurrence(scope 显式)、created_at；主键纪律=CFI+quote/context+occurrence，百分比/裸偏移不作主键；④**CFI 核验 owner=Reader**，三环不信任引擎自述（录入环七级校验、恢复环回读文本逐字比对含重复句反例识别、回访环真实 range+oracle）；⑤版本管理（annotations 1→2、locator v1、reading 无全局版本、import_version 不变）；⑥消费者入口与永久验收入口（verify_epub_product.py，T-02 建立）。
- **源码对照事实（设计依据）**：jsonx.valid_annotations 要求 version==1、容忍未知顶层键、记录级容忍未知键（jsonx.at L1285/L1419）；valid_state 容忍未知键（L442）；rec_json/reemit 按白名单重建（annotations.at L58）→ 方案乙旧客户端重写静默丢 locator_id 成立；probe.at L49 `doc-surface (url: .surface_url, height: 420)` 为消费者入口语法（vue 轨退化透传 div）；029 SD-02 document-surface-native-input §1.3 事件身份链继承。
- 未创建数据/资产/代码/测试结果；未修改 canonical Spec（SD-01～05 落地属 T-10）。

### 2026-11-03：work阶段——T-00 029交付核查与正式启动profile冻结（AC-01）

- stage: work | plan_id: READER-007 | plan_revision: r1 | task: T-00 | outcome: pass（029交付可核、正式双端启动与接口消费实测成立；cohort 物化补齐 doc-surface 二进制）| 执行位: D:/autostack/auto-reader main（树干净，git status 零输出）| next: T-01。
- **029 交付核查（desk）**：auto-ui master 归档 e6ef5381（12/12），landing 65bb455f（merge，parents e7b09ea8 + 98633fd4，doc-surface 实验 leaf + N-05 隐藏修复），T-10 独立复审 pass（AC-01..10 全过、无 partial/GAP；vm 92/92 + vue 48/48 独立复演 exit0）。cohort 记录于归档计划与研究文档：auto g47d8f7b（sha256 6f1925ea…）、引擎 foliate-js@3d794195、预算 15/10/5/30/10s + 600s。Reader main@7a1b4fd，无他人 WIP。
- **cohort 物化（实测发现并补齐）**：磁盘现有 auto-ui-tool.exe（11-02 13:09 构建，pre-landing）**不含** doc-surface——探针启动后 doc-surface 组件渲染为 `[RemoteFrame]` 文本占位、`AUTO_DOC_SURFACE_DEBUG=1` 零 create 日志、二进制无 `AutoUIDocSurfacePopup`/`doc_surface` 字符串；029 运行用的 worktree 内工具二进制已随 merge 清理。**重建**：从落主 master（65bb455f）`cargo build -p auto-ui-tools --features doc-surface`（临时在 auto-ui-tools/Cargo.toml 加 `doc-surface = ["auto-ui-runtime/doc-surface"]` 透传，构建后 `git checkout --` 还原，auto-ui 树零残留）→ 新二进制（11-03 13:32，147,089,408B）实测：doc-surface iced 臂命中（`[doc-surface] into_iced arm reached`，193 行）、url 空时 defer（正常初态）、Connect handler→`GET /api/probe/surface-url` 200、MCP 树/窗口全活。
- **正式启动（两端实测，冻结 profile）**：vm 分离模式 = `auto run -r vm --no-merge -B 17825`（从本仓根）→ 后端 `http://127.0.0.1:17825/api/library/books` 200（`{"version":1,"books":[]}`）、原生窗口「图书阅读器」（进程=auto-ui-tool.exe）、MCP `http://127.0.0.1:9247`、UI 树含书架侧栏 chrome。vue 模式 = `auto run --server=vm` → 前端 `http://localhost:17824` 200（vite，**IPv6 回环**；127.0.0.1 直连拒绝）、后端 17825 200。**差异登记**：`auto run -r vm --server=vm` 实测=仅后端无窗口（README 第 17-18 行 `-r vm --server=vm` 为 VM 全轨的记载不准确，正式门/驱动均用 `--no-merge`；README 修订列入 T-10）。
- 结论：029 依赖就绪，**不触发 dependency_not_ready**；T-00 通过，进入 T-01。工具/资产身份：auto=g47d8f7b、auto-ui-tool=重建版（hash 待 T-02 manifest 固化）、engine-assets/corpus 由 prepare_engine_assets.py/gen_corpus.py 确定性重建（本次重建于 plan-artifacts/reader-007/t00/）。

### 2026-11-03：new阶段交接

- stage: new；READER-007 r1；outcome: blocked（仅实施依赖，草案已建立）；next: 等029全部必需门/独立review/精确交付可核后进入T-00，不启动实现。
- 用户已确认先起草；UI/029本地仍executing、9/12，GAP/冻结跑/final review待核，不修改其合同或标完成。Reader已有driver_vue.py WIP不接管。
- 新增T-00～12、AC-01～12、P-01～12、SD-01～05；本轮只合同/导航，未创建数据/资产/代码/测试结果，未修改canonical Spec或旧ledger。
- 起草自检：7份本次文档的90个本地引用已核，新改链接有效，UI README原有9个旧失效引用未扩改；0～10节、13任务/12AC/12必需用例完整，007号唯一、下一号008，git diff --check通过。只证明草案结构，不能作为029或007运行验收通过。

## 10. 待澄清事项

1. 029的最新完整交付cohort与独立复审/验收回执目前未查到，用户同意先起草等待。执行前由T-00核实，未满足不得产品化。
2. 原生正式Reader的启动与HTTP/merged组合是否沿029接口可用？T-00整路径证明，不以实验窗替代，不凭旧命令推断。
3. Locator v2存储/协议、跨段与v1映射、可信CFI核验、引擎资源/性能预算，由T-01在实现前冻结；未决时不先写用户数据。机制实证失败须回规划/owner前置，不降低AC。
4. 固定引擎分发/许可与真实语料可再分发性由T-01/02核查；不内嵌用户书、凭据或未经说明的外部目录依赖。后续正式计划只交付本期profile，不把Readest全部能力塞入一份计划。
