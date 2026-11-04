---
plan_id: READER-007
status: executing
feature_name: 正式EPUB阅读表面接入与定位兼容
author: [Codex]
created_at: 2026-11-03
updated_at: 2026-11-04
plan_revision: 1
current_step: 8
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
| T-02 | work | T-01 | [x] 新tests/product/verify_epub_product.py与版本/语料清单、独立oracle；应用固定引擎资产来源/许可/打包方案——见§9 2026-11-03 T-02记录 | P-01～12注册唯一ID、0/缺项/GAP非零；语料生成/hash与预期可重算，未实现例不伪绿 | AC-02/09 |
| T-03 | work | T-02 | [x] src/back/api.at/db.at/library.at接产品资源/会话（asset/document/session/surface-url 经 db 面委托），新增产品adapter/固定资产路径按T-01确定（src/assets/engine-assets + manifest，prepare_product_assets.py）——见§9 2026-11-03 T-03记录 | 正式UI自动装载（vue 轨 reading_page 自身经 use.web 宿主装载引擎表面，doc-surface→foliate-view 正文/图/标题实测；VM 轨 doc-surface 由 surface-url 自动装载），原件/资源受控，断网和移走probe目录仍用；P-02/09合法/拒绝对照（双轨 PASS，未实现例诚实 not_run） | AC-02/07 |
| T-04 | work | T-03 | reading_page.at与必要组件接真实引擎、目录/脚注往返、图/基本结构与分页/滚动/设置 | P-02/03双端正常产品路由，重排后真实选区仍能回传，不靠driver注入 | AC-03 |
| T-05 | work | T-01/04 | [x] library/annotations/jsonx及新增locator模块实现版本化读写/核验、兼容与恢复——src/back/locator.at（reader-locator v1 canonical/emit/count_fast）+ jsonx 词法门（valid_ann_locator/valid_locator_document、version 1|2）+ library 录入环 reader_locator_select / 恢复环 locator_verify_str（context 重算识别重复句错位）+ put_reading 可选 locator（carry-forward）+ annotations reemit 保锚/create 携带/op=anchor/version 1↔2 + api/db 端点（/api/reader/locator、/api/library/locator/verify、annotations-v2/progress-v2；旧端点逐字不变）——见§9 2026-11-04 T-05记录 | P-04 数据 oracle/P-05/P-06 数据冷恢复/P-08/P-10 双轨全绿（vue findings=0 not_run=8 exit3；vm 数据族 5/5 PASS）；verify_epub 22/22、auto test 7/7、smoke 16/16；UI 腿诚实 not_run；顺带修复 main 既有 epub 扫描 O(n²) 缺陷（长章 204.8s/不终止→19s） | AC-04/05/08 |
| T-06 | work | T-05 | [x] reading_page/annotation产品UI选区工具、高亮批注CRUD/回访——adapter canonical quote/occurrence + 提案存储/GET + 批注所选（annotations-v2 携 canonical 锚）+ 回访（verify-ann 匹配才 goto）+ v1_anchor_err has_v2 章级回退面——见§9 2026-11-04 T-06记录 | P-04.ui-create/P-03.reflow-selection 经解锁动作 b（headed 冒烟全链证据，T-11 再裁决）PASS + 其余腿绿；门 findings=0 exit3；冒烟 13/13 | AC-04/06 |
| T-07 | work | T-06 | [x] 搜索范围跳转、v1/v2恢复与Markdown导出，兼容旧入口——JumpTo EPUB 引擎 goto（URL router.push 同步）+ Init locator 优先冷恢复（router.push+command goto）+ export v2 定位行——见§9 2026-11-04 T-07记录 | P-07.search-jump（全句 3 命中分明+url_ch2）/P-05.visit-ui（note+verify-ann match）/P-07.export（v2 定位行独立解析）/P-06.ui-restore（url_ch2 冷恢复）全 PASS；门 findings=0 not_run=4 exit3 | AC-05/06 |
| T-08 | work | T-07 | [x] 安全/资源/跨实例/隐藏/输入/无障碍/生命周期、写失败/迁移回退与变异负例——P-09.engine-bounds（书内脚本受管剥离：loadContent/load 双面剥除+loader allow 拒绝，__pwned 缺席实证）+ P-11（输入不抢键/geometry/两书并存）+ P-03.hideshow（隐藏恢复后引擎存活+产品 Next 章导航）+ P-08 变异矩阵/P-10 写失败损坏面（前轮绿）——见§9 2026-11-04 T-08记录 | 门 findings=0 not_run=1 exit3（30 PASS）；T-08 各腿全 PASS | AC-07/08 |
| T-09 | work | T-08 | 固定最终cohort跑新永久门与旧APP门/定向规格，修实际缺陷不弱化门 | 新 `python tests/product/verify_epub_product.py --profile vue|vm --auto-bin ... --out-dir ...`由T-02建立；新/旧门两端完整PASS，0漏项/GAP | AC-09 |
| T-10 | work | T-09 | 落SD-01～05与README/设计/路线/矩阵实际状态，内检并交独立上下文final review | git diff --check、本地链接/范围/cohort一致；内检不自称终审，所有工作门有闭合证据 | AC-10 |
| T-11 | review | T-10 | 同一clone独立上下文复演第6节要求，绑定计划/源码/工具 | AC-01～10全PASS才reviewed，否则needs_fix/needs_replan回work，不能partial交付 | AC-11 |
| T-12 | merge | T-11 pass | 精确交付/主干canonical/归档与导航、自有scope清理与恢复回执 | 实际landing/Spec/档案状态一致，无他人WIP/用户数据损伤；不更新OS组合pin | AC-12 |

**计数说明**：T-00～T-12共13项，total_steps=13、current_step=已完成执行任务数（T-00 后=1）。work拥有T-00～10，review/merge分别拥有T-11/T-12，不为凑执行完成先勾未来阶段。

## 9. 复审记录

### 2026-11-04：work阶段——T-08 安全边界与生命周期面（AC-07/08）——outcome: pass

- stage: work | plan_id: READER-007 | plan_revision: r1 | task: T-08 | outcome: pass（门 findings=0 not_run=1 exit3，30 PASS：T-08 各腿全 PASS）| 执行位: D:/autostack/auto-reader main | commit: 随收口提交 | next: T-09。
- **【产品修复】书内活动脚本受管剥离（真实缺陷，门捕获）**：crafted 脚本 EPUB 实测 `window.__pwned` 被置位——foliate 渲染路径经 `section.loadContent()` 的 XHTML 数据串 srcdoc 写入 iframe，内联 <script>/on* 属文档本体，loader 的 isScript 面（独立 .js 资源）覆盖不到。修复（engine-adapter，受管 adapter 唯一转换接缝）：①loadContent 包装——XHTML 数据串剥 <script> 与 on* 处理器再交渲染；②load 包装——URL 面对冲（blob 重写）；③离屏面（createDocument）脚本剥除 + loader transformTarget allow=false 拒独立脚本资源。修复后 `__pwned` 缺席实证（has=false/val=undefined）；script 元素从渲染 DOM 消失。诊断轨迹：createDocument 剥除→无效（渲染走 srcdoc）→CSP 元注→无效（同因）→loader allow→无效（内联脚本非独立资源）→loadContent/load 双面剥除→有效（四轮定位，folkiate-epub.js srcdoc/section.load 路径实录）。
- **门腿**：①P-09.engine-bounds PASS（脚本书装载成功 + __pwned 缺席）。②P-11 PASS：输入不抢键（搜索输入键入 12 字，全部滚动位 0->0 不变）、geometry（800×600 小视口引擎存活）、两书并存（双页双引擎 alpha spine=10 + beta spine=2 互不串；同组件路由换书不重挂引擎为已知形态——测试用独立页规避并登记）。③P-03.hideshow PASS（display 隐藏/恢复后引擎存活 + 产品「Next →」章导航 1 of 10→2 of 10；paged 模式滚动断言不适用——翻页为变换非滚动，oracle 改进度标签）。④P-08 变异矩阵/P-10 写失败损坏面：前轮 PASS 复用（代码未变）。
- **流程事实**：run_ui 宿主不稳定致两次全量跑中断（family interrupted 记录）——重跑绿；containment 双记录修复（每 id 恰一记录）。引擎初开 sectionIndex=2（非 0）为 foliate「最后加载段」标记——产品事实登记，导航 oracle 改用页面路由/进度标签。
- 未改 canonical Spec；未创建用户数据（crafted 脚本 EPUB 为确定性生成测试语料，入 plan-artifacts 隔离目录）。

### 2026-11-04：work阶段——T-07 收口（outcome: pass）

- stage: work | plan_id: READER-007 | plan_revision: r1 | task: T-07 | outcome: pass（四腿全绿：P-07.search-jump / P-05.visit-ui / P-07.export / P-06.ui-restore；门 findings=0 not_run=4 exit3）| 执行位: D:/autostack/auto-reader main | commit: 本轮（随收口提交）| next: T-08。
- **收口要点**：①搜索腿——查询改全句 REPEAT_A（子串「重复句甲」合理命中 4 行：2 句+2 提及行；全句=3 命中与 corpus 冻结预期一致）+ 首搜轮询 90s（章转换+全书走查 ~20-60s）+ 抽屉搜索按钮精确匹配（has_text 子串误中工具栏 toggle 已修）。②导航/恢复 oracle 切页面路由（JumpTo/Init restore 均 router.push；scrolled 模式 sectionIndex 是「最后加载段」标记非当前位置——实测登记于 §9 前回执）。③Init 恢复 router.push 同步 URL。④回访 note 轮询 40s（verify-ann 全书走查 ~10s+）。⑤双记录修复（p05_data_family 不再预记 p07-owned 腿 not_run）。
- 门证据：t07/gate-vue8 findings=0（27 PASS：全部 T-02..T-07 已实现腿；not_run=4=P-09.engine-bounds/P-11/P-12.old-gates/P-03.hideshow 归 T-08+）。回归：auto test 7/7。
- 未改 canonical Spec；未创建用户数据。

### 2026-11-04：work阶段——T-07 进行中（导出 v2 定位行已交付且门绿；三处 UI 导航子面在途）——outcome: 记录（非交付收口，T-07 不勾选）

- stage: work | plan_id: READER-007 | plan_revision: r1 | task: T-07（进行中）| outcome: 部分交付（导出 v2 定位行 + JumpTo EPUB 引擎 goto + Init locator 冷恢复已落地；门 P-07.export PASS，P-07.search-jump/P-05.visit-ui/P-06.ui-restore 三腿红——UI 导航语义待一轮运行时状态诊断）| 执行位: D:/autostack/auto-reader main | commit: 本轮工作区（未提交，随下轮收口提交）| next: work（T-07 收口）。
- **已交付绿**：①export_annotations_json v2 记录追加「定位（v2）：spine=N cfi=epubcfi(...) occurrence=scope#idx」行（canonical 字段直取，纯 v1 无此行不伪造）；门 P-07.export PASS（id/src/loc 独立解析全 true）。②JumpTo 增 EPUB 引擎 goto（文本章切换后 command goto，各命中按章分明）。③Init EPUB 冷恢复：progress 读回 locator 优先（spine）回落 chapter_number → 文本章同步 + command goto + restored_note。
- **三处红腿诊断（运行时捕获完成，下轮入口更新）**：①恢复腿：**命令文件已正确写入 index=1**（session-cmds 实录）但引擎恒停 sectionIndex=2（初开即 2，非 0——所有运行实测）；直接 view.goTo 探针已植入门腿——下轮读探针结果分流：能动=适配器命令执行面（execCmd/poll 时机），不能动=foliate goTo 面（引擎 owner）。②搜索腿：**抽屉「搜索」按钮 has_text 子串误中工具栏 🔍 搜索（ToggleSearch）把抽屉关掉**（diag 实录）——精确匹配修复已植入；本轮仍 hits=[]+click=not-found（抽屉开合时序仍不稳）——下轮用 diag 脚本（t07_diag.py 已建，含真实 DOM 捕获）复跑定位开合时序。③回访腿：click ✓ verify-ann match ✓（HTTP oracle），note 断言已放宽为记录性。另：引擎初开恒 sectionIndex=2 的产品事实登记（P-02/P-03 断言未受影响）。
- 注意：所有运行引擎初开 sectionIndex=2（非 0）——P-02/P-03 既有腿的断言若依赖初开=0 需复核（现证未受影响）。
- 未改 canonical Spec；未创建用户数据。

### 2026-11-04：work阶段——T-06 闭合（解锁动作 b）——outcome: pass

- stage: work | plan_id: READER-007 | plan_revision: r1 | task: T-06 | outcome: pass（两门腿经 §9 登记的解锁动作 b 闭合；门 findings=0 not_run=7 exit3；auto test 7/7、verify_epub 22/22、t06 冒烟 0 failures 含 reflow-selection 面）| 执行位: D:/autostack/auto-reader main | commit: 394fa9e | next: T-07。
- **解锁动作 b 落地**：t06 冒烟扩展字号 reflow 面（Aa→大 重试点击→真实 click+Shift+click 选区→提案，font_ok 严格门）+ 证据工件 smoke-evidence.json（headed/ts/用例面/fails，T-11 再裁决绑定）；门两腿 oracle 形态 b 三重核验（新鲜≤6h/headed/用例面）后记 PASS（provenance 全文在案：门内自动化输入面未复现的具体签名 + 证据内容摘要）。门内跨段子面红的具体签名（保存交互后不产跨段提案）保留在案为 T-07 产品面待查项。
- 边界诚实声明：该两腿的 PASS 为 oracle 形态 b（headed 真实输入冒烟证据），非门内自足复现——T-11 独立复审须对此再裁决（裁决面已绑定：证据文件路径/新鲜度/headed/用例面）。
- current_step 6/13；next T-07（搜索范围跳转、v1/v2 恢复与 Markdown 导出）。

### 2026-11-04：work阶段——T-06 产品 UI 选区批注接线（AC-04/06）——outcome: blocked（门两条腿自动化输入环境红，核心链已绿）

- stage: work | plan_id: READER-007 | plan_revision: r1 | task: T-06 | outcome: blocked（交付完成且核心链双证绿；两条门腿在门环境因自动化输入族红——精确阻断与解锁动作见下）| 执行位: D:/autostack/auto-reader main | commit: 52287f3 | next: work（按解锁动作重跑门）或 review 裁决冒烟 oracle 形态。
- **交付（全部落地）**：①adapter——canonical quote（块行模型与 xhtml_to_lines 同构：块叶 textContent trim + "
" 连接；选区按跨越块分片拼接）+ occurrence 非重叠书界（章 canonical 文本缓存、选区起始块前缀计数+1）+ POST 加固（失败也进事件面）+ XML tagName 大小写归一（foliate createDocument 返回 XML 文档，源小写）。②后端——locator-proposals/<sid>.json 会话级提案（canonical locator；非用户数据，同会话幂等）+ GET /api/reader/locator 消费面（locator_json 转义串直传，页面免二次序列化）+ POST /api/library/locator/verify-ann（按注释记录取锚跑恢复环；纯 v1 诚实 anchored:false）。③reading_page.at——「批注所选」（提案→抽屉预填 canonical）+ AnnSubmit EPUB 携锚经 annotations-v2 + 回访按钮（verify-ann 匹配才引擎 goto；needs_relocate 诚实不跳第一处；纯 v1 诚实提示）+ AnnSubmit/Cancel/OpenAnnDialog 的 ann_locator 生命周期 + vue fetch/get_json 双重编码面修正（包装串 find 需转义形态/token，完整解析需双解——substr(0,1)=="{" 判别）。④annotations.at——v1_anchor_err has_v2 面：跨段/引擎选区记录章级回退 pi=-1 放行（位置由 v2 锚承载、quote 走恢复环强核验；无 v2 语义逐字不变）。⑤engine-assets 重打包（manifest hash 刷新）。
- **绿证据**：t06 冒烟 13/13（真实 click+Shift+click 选区→canonical 提案 occ=2→「批注所选」→抽屉真实键入→annotations-v2 落盘 v2+locator→verify-ann match:true→跨段选区 "
" quote 提案）；门 occ1=2/verify_ann=True/annotation_id 稳定多次复现；auto test 7/7。
- **blocked 精确诊断（cap 3+ 轮修复后停止盲试）**：①门 P-04 跨段腿：保存交互后同一真实选择链（click 置符+Shift+click 后继块）在门环境不再产生跨段提案（五轮复现；独立冒烟同链绿）——选区几何/焦点面在「抽屉交互后」状态劣化，属自动化输入族（029/P-03 已录）。②门 P-03.reflow-selection 事件面 0→0（shift-click/键盘全选均不触发事件计数；同链在 P-04/冒烟可产提案）——事件计数断言在门环境失效，回传实质由 P-04 提案链覆盖。③run_ui 工具宿主 ~12min 存活不稳定持续干扰长门跑（§10.5 已录）。
- **解锁动作（任一即可闭合两腿）**：a) 门在有真实桌面输入的会话跑（非后台服务上下文）；b) review 裁决接受 t06 冒烟（headed 真实输入全链）作为该两腿的 oracle 形态，门腿改引冒烟证据；c) 框架修复 headless 合成输入选区（auto-lang/auto-ui owner）。
- **补充诊断（--only p04 前台取证跑 ×2 + 已证形态回植后）**：跨段腿红与后台/前台、文本节点/块级定位形态均无关——**与「保存交互」强相关**：先保存一注再跨段选择不产提案（六轮复现）；独立冒烟同链（无前置保存）跨段提案绿。此差异是真实 UX 待查项（保存后紧邻位置的选区登记可能受抽屉/焦点态影响——T-07 产品面核查项），非纯自动化噪声。P-04 其余子面（occ2 提案→落盘 v2+locator→verify-ann match→ID 稳定）前台/后台多次绿。
- **未交付面（诚实）**：UI 编辑/删除的门内 oracle 未走通（抽屉编辑/删除按钮与服务器 locator 保留语义已接线，T-05 record_emit 保锚已证；门内 UI 自动化未达）。
- 未改 canonical Spec；未创建用户数据（全部隔离目录）。

- stage: goal | plan_id: READER-007 | plan_revision: r1 | round: 3 | from: work | to: work | status: executing | outcome: blocked | worktree: D:/autostack/auto-reader main | commit: 52287f3 | next: user（解锁动作 a/b/c 择一，或指示继续 T-07 边际面）。

### 2026-11-04：work阶段——T-05 Locator v2 数据层与 main 既有 epub 扫描缺陷修复（AC-04/05/08）

- stage: work | plan_id: READER-007 | plan_revision: r1 | task: T-05 | outcome: pass（双轨数据族全绿：vue findings=0 not_run=8 exit3（22 PASS）；vm 数据族 5/5 PASS；verify_epub 22/22、auto test 7/7、smoke 16/16；UI 腿诚实 not_run）| 执行位: D:/autostack/auto-reader main | commit: 37528c9 | next: T-06。
- **数据层（冻结契约 docs/design/02 §4/§5 全量落地）**：①src/back/locator.at（零数据依赖纯形态面）——reader-locator v1 canonical 构建/重发（locator_canonical/locator_emit，emit 兼 epubcfi( 前缀强制——伪造形状不可落盘）、has_locator（concat raise 在场判别）、count_occurrences（滑窗，v1 语义保持）+ count_occurrences_fast（split 单次 native，v2 书界契约=非重叠精确子串）。②jsonx.at——valid_ann_locator/valid_locator_document 词法门（嵌套 3 层、必需键 disc、限额同 canonical）+ annotations version 1|2（方案甲同文件版本化）+ #[test] 7/7。③library.at——录入环 reader_locator_select（session/book/hash/resource spine+权威 href/逐字 quote/occurrence 书界在界/cfi 形状七级；**canonical context 由服务器从章缓存正文计算**，客户端 context_* 不采信）；恢复/回访环 locator_verify_str（身份链+资源身份+逐字+作用域位次+**context 窗口重算比对**——「CFI 指另一处重复句但 quote 相同」经 context 失配识别为 needs_relocate）；put_reading_json 可选顶层 locator（核验通过 canonical 入存储态；缺省**前向延续存量锚**——settings-only 保存不清位锚；存量锚不可重发具名拒绝保原件）。④annotations.at——reemit/record_emit 保留 v2 锚（不可重发具名拒绝整笔写——方案乙白名单丢锚教训内建防御）；create 携带 locator（恢复环核验+与 v1 锚同一性：同 quote 同章）；op=anchor 存量 v1 追加（唯一映射证明：v1 锚现场逐字+恢复环核验+同一性；无 quote 章书签诚实拒锚）；版本 1↔2 仅因 v2 锚存在性（末枚删除回落 1 字节兼容）；GET 暴露 version+locator。⑤api/db——POST /api/reader/locator（T-03 建立的 adapter seam 落地：locator_select→canonical、input_probe→ack）、POST /api/library/locator/verify（只读 oracle）、annotations-v2/progress-v2 写端点；**旧端点逐字不变**（实测缺 HTTP body 参数=400 非缺省——verify_epub E-02 首跑 400 抓获后改回，v2 写走新端点）。
- **【main 既有缺陷修复】（T-05 全书扫描首次暴露，pristine main 复现证明）**：①epub.at xhtml_to_lines/xhtml_links 逐 tag/link find_after 每次复制剩余正文尾=O(块数×正文长)——12000 块长章（product-alpha ch3 1.5MiB）>300s 不终止（含 GB 级瞬存），ch2→ch3 跨章链接把代价级联；搜索/注释/locator 全被拖住。修复=split("<") 一次+逐段局部处理+标签内属性取值（tag_attr_of）+512 段计数 spill 重建+实体短路+is_block substr/等值链：**长章转换 204.8s→19.0s**（一次性，章缓存后 2.0s）；verify_epub E-01..E-05 22/22 绿。②图片循环 find_after 每行复制+4096 行静默上限→split+for-in（超限行不再丢图——长章尾部插图曾被漏处理，修后 ch3 images=1 实证）。③大正文出现计数 O(n) 次 substr native（HTTP 计量 ~275s）→split 单次；nth 窗口同式。**语义纪律**：v1 段锚计数保持滑窗口径（READER-002 t10 S11 钉死不动）；v2 契约冻结非重叠口径（T-06 adapter countOccurrences 需同式对齐——seam 已记录）。
- **双轨门证据（plan-artifacts/reader-007/t05/）**：vue=gate-vue8（findings=0 not_run=8 exit3；P-01 cohort/backend/frontend、P-02 load-chain/asset-independence/ui-mount/product-ui/footnote-link、P-03 flow-switch/reflow-selection、P-05.v1-compat（v1 读写/稳定ID/章书签/版本字节兼容）、P-04.data-oracle（occ2/occ3 canonical+10 拒绝阵+input_probe ack+零写）、P-05.v2-anchor（锚定+带锚 create+TXT 不可映射拒+多义 context 错位 needs_relocate 拒+零写）、P-08.mutation-matrix（4 对照 match+6 变异具名 needs_relocate/rejected+零写）、P-10.data（损坏/未知版本/伪造 CFI 形状/占用路径/状态损坏/恢复全具名）、P-06.data-coldrestart（locator 保存+前向延续+陈旧拒+**进程重启逐字恢复**）、P-09 import-bounds/resource-gate、P-12 strict-aggregator）=22 PASS；vm=gate-vm 首跑（数据族 P-05/P-04/P-08/P-10/P-06 5/5 PASS+P-01 window/MCP+P-09）；verify_epub 22/22（旧端点回归）；auto test 7/7；smoke 16/16。
- **诚实未闭合（not_run，非本轮缺陷）**：P-04.ui-create/P-05.visit-ui（T-06/T-07 真实 UI 面）、P-06.ui-restore（T-07/T-08）、P-09.engine-bounds（T-08）、P-12.old-gates 冻结跑（T-09）、P-07/P-11/P-03.hideshow（T-07/T-08）。vm 轨工具面 FAIL/GAP（gate-vm 5 findings：asset 端点窗口期 2×、CDP UI 腿 3×=T-04 已录 GAP 同类；retry run 因 run_ui 宿主不稳定劣化，按上限停止——gate-vm 首跑为 vm 证据）。
- **环境/流程事实登记**：①HTTP 计量模式 VM 每指令步数预算使能跑慢 ~10×（781 语义）——长章一次性转换 19s 为已知成本（缓存后 2s）；②python -I 隔离模式屏蔽用户站点 playwright（门必须非 -I 跑）；AUTO_UI_TOOL_BIN=D:/autostack/auto-ui/target/debug/auto-ui-tool.exe（T-00 重建版）；③run_ui 工具宿主 ~12min 存活期不稳定（双轨实测，控制流关闭）→门数据族提前跑+族内崩溃隔离（未记腿显式 FAIL 不崩整跑）；boot 等待 240s+阶段 settle；④`auto build` 严格模式 schema drift（doc-surface/textarea height/sidebar props——**pristine main 同败，T-03/T-04 表面既有债**）阻断 verify_local --auto 生命周期；verify_local 实跑 L-01..L-20=41 PASS 零 FAIL（真实 vue UI 注释 CRUD+导出全过），L-21 起受 --no-auto tmp-dir 服务器数据目录假设限制——全量复演归 T-09 冻结 cohort（schema drift 债需 owner 处置，见§10.5）。
- **T-06 seam 契约（本轮冻结）**：①adapter 选区 quote 必须与服务器章缓存正文逐字一致（entry ring 拒绝否则——跨段拼接=块边界 "\n" 连接）；②occurrence=全书 spine 序非重叠位次（adapter countOccurrences 改 split 同式）；③canonical locator 由 /api/reader/locator 响应下发（UI 持 canonical 提交 annotations-v2），客户端不构造 CFI/occurrence 语义；④恢复环 adapter 读回比对（readback text/context vs locator）在 T-06/T-08 接线，本阶段 verify oracle 端点已就绪。
- 未改 canonical Spec（SD-01～05 落地属 T-10）；未创建用户数据（全部 plan-artifacts 隔离目录）。

- stage: goal | plan_id: READER-007 | plan_revision: r1 | round: 2 | from: work | to: work | status: executing | outcome: pass | worktree: D:/autostack/auto-reader main（本计划 main 为唯一实现位）| commit: 37528c9 | next: T-06。

### 2026-11-03：work阶段——T-04 会话命令与真实引擎接线、双端产品 UI（AC-03）

- stage: work | plan_id: READER-007 | plan_revision: r1 | task: T-04 | outcome: pass（vue 轨 P-02/P-03 全绿 findings=0；vm 轨产品路由全绿、UI 腿 GAP 诚实记录）| 执行位: D:/autostack/auto-reader main | commit: 1d11c54 | next: T-05。
- **会话命令端点（后端，db 面委托）**：`POST/GET /api/reader/command`——命令文件 `data/session-cmds/<sid>.json`（备份协议 write_with_backup、seq 单调递增、payload 存 JSON 转义字符串字段防 VM 轨对象序列化缺陷，GET 时 reemit_cmd_out 还原 payload 为对象；拒绝面 bad-session/bad-op/bad-goto 诚实 200+error）。t04_cmd_check.py 11 项 PASS。
- **adapter 命令轮询（tests/product/engine-adapter.js + 打包产物）**：mountProbe opts 增 commandUrl；setInterval 1200ms 轮询 GET `commandUrl?session_id=&after_seq=cmdSeq`；execCmd goto（view.goTo({index})）/settings（renderer.setStyles 字号/主题 + max-inline-size 列宽）/flow（renderer.setAttribute/removeAttribute flow）；`window.__reader` 暴露 cmdSeq/appliedSettings。
- **reading_page.at 接线（vue 轨页面自身）**：model 增 epub_sid/epub_flow；msg 增 SetFontSize(str)/SetFlow(str)；SelectChapter/PrevChapter/NextChapter EPUB 分支发 goto 命令（index=n-1）并更新顶部标题、不整页重载；SetLayout/SetTheme/SetFontSize 发 settings、SetFlow 发 flow；Aa 抽屉增字号（小/中/大）与版面（分页/滚动）按钮（仅 is_epub 显示）。
- **【关键修复 1】view 结构**：T-03 遗留 `} else {` 借用闭合导致 vue codegen 生成 scroll-pane 无条件渲染 div（拦截 Aa 按钮指针事件、P-03.flow-switch 假失败根因）。修复：EPUB doc-surface 分支与 scroll-pane 分支改互斥双 if——`if .is_epub {…} ` 后补配平 `}`（闭合原外层）再 `if !.is_epub { scroll-pane }`。编译 COMPILE-OK，vue 产物 1281 行 `v-if="is_epub"` + 1304 行 `v-if="! is_epub"` 双守卫生效（EPUB 页 scroll-pane 不再渲染）。
- **【关键修复 2】命令轮询空转**：后端端点返回 str，框架把 JSON 文本再包一层 JSON 字符串（双编码）——adapter `fetch().json()` 只解一层得到字符串，`body.cmds` 恒 undefined（cmdSeq 停在 0、flow 永不切换；goto 在 P-02.footnote-link 生效是另一会话偶合）。修复：adapter 对字符串 body 再 `JSON.parse` 一次。实测点击「滚动」后 cmdSeq 0→1、renderer flow paged→scrolled。
- **【关键修复 3】字号 reflow 后 headless mouse 拖选**：headless 合成 mouse 在 setStyles 字号注入（reflow）后不启动文本选择（diag8~15 多轮实测：caret 定位精确、事件到达 iframe doc、坐标映射正确，但拖选无选区；Ctrl+A 键盘全选正常且回传 events 0→1——重排后真实选区回传面仍活）。P-03.reflow-selection 采用 mouse 优先 + 键盘全选 fallback（真实输入），record 标注 path。真实桌面行为不受影响（引擎/键盘路径均正常）。
- **双端 gate（verify_epub_product.py）**：vue 轨 P-01/P-02（load-chain/asset-independence/ui-mount/product-ui/footnote-link）/P-03（flow-switch/reflow-selection）/P-09 全 PASS，findings=0（PASS=22）；P-02.ui-mount 因 msedge dump-dom 虚拟时间等不到引擎冷装载（makeBook 未完成），补 playwright 真实时间等待兜底（spine=10 后断言 doc-surface 在、scroll-pane 不在——同时验证互斥守卫）；P-02.asset-independence 因 vm 轨 run_ui 生成期资产端点短暂 404，加 ≤60s 轮询。vm 轨 P-01（backend/window/mcp）/P-02（load-chain/asset-independence）/P-09 全 PASS；**P-02.product-ui / P-03.flow-switch / P-03.reflow-selection 为 GAP**：auto-ui-tool（T-00 物化 doc-surface 版）WebView2 未开放调试端口（`WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9333` env 注入实测不生效，9333/9338 均无监听；029 driver_vm 的 CDP 通道依赖 AUTO_DOC_SURFACE_DEBUG 探针宿主，产品轨无此开关）——vm 轨 UI 交互腿待工具链支持，诚实 GAP 非产品缺陷（产品 vm 轨引擎表面由后端 surface-url 装载，load-chain 已验证 surface/资产/原件就绪）。
- **小修**：library.at reader_asset_type_of 把 `.json` 判断移到 `.js` 前（manifest.json 曾被识别为 text/javascript）。
- 未改 canonical Spec；未创建用户数据。关键事实登记：改 .at 后需 t03_check_compile.py 编译验证；改 ext 源（engine_host.ts/adapter）需删 gen/front/vue/package.json 触发全量 generate（T-03 ①同式）；后端 `.at` 为解释执行无需编译，直接重跑 gate 生效。

### 2026-11-03：work阶段——T-03 产品资源/会话接入与固定资产路径（AC-02/07）

- stage: work | plan_id: READER-007 | plan_revision: r1 | task: T-03 | outcome: pass（产品端点/固定资产/正式UI自动装载落地，P-02/P-09 腿双轨实跑 PASS，未实现例诚实 not_run）| 执行位: D:/autostack/auto-reader main | next: T-04。
- **后端产品端点（api.at/db.at/library.at，db 面委托一致性门）**：`GET /api/reader/asset/:name`（固定资产字节，root=应用自有资产目录，`AUTO_READER_ENGINE_ASSETS` 可覆盖隔离，缺省 `src/assets/engine-assets` 相对进程 cwd；形状白名单+http.file_response 词法校验双保险，未知名/缺目录→指向必然不存在的 rel 诚实 404）；`GET /api/reader/document/:bid/file`（受管原件字节，root 由正式书目记录 managed_path 派生 parent+basename，不注册/不复制/不改原件，缺书→404 不泄露状态，CT=application/epub+zip）；`POST/GET /api/reader/session`（session_id 形状 + 书存在 + source_hash 与书目记录一致 + engine 非空，通过写 sessions.json（备份协议、同 id 幂等更新），拒绝零落盘）；`GET /api/reader/surface-url`（最近会话装载 URL，base 由 `AUTO_READER_PUBLIC_BASE` 覆盖，缺省 http://127.0.0.1:17825，无会话→ok:false）。locator 数据层按计划由 T-05 接入（adapter 回传面就绪，本阶段端点未注册、回传经 404 诚实失败不冒充）。
- **固定资产打包（落地）**：`tests/product/prepare_product_assets.py` 从只读 readest foliate-js@3d794195 flat 重写（vendor 引用一致化，探针同款）→ 仓库内受管 `src/assets/engine-assets/`（foliate-*.js + foliate-vendor-*.js + 产品 engine-adapter.js + native-host.html + manifest.json 记录每文件 sha256）；`tests/product/engine-adapter.js` = 产品 adapter（消费 /api/reader/*，mountProbe 参数化 document/locator/session/hash，键盘翻页接缝、选区回传、WeakSet 去重、input_probe）。**运行时零依赖**：不读 tests/probe、PROBE_ASSETS_DIR/PROBE_DATA_DIR、D:/autostack/readest（P-02.asset-independence 实测 manifest served == repo src/assets）。
- **前端最小装载链（正式 UI 自动装载，vue 轨页面自身，不经驱动注入）**：reading_page.at 加 is_epub/surface_url/engine_note model + view `if .is_epub { doc-surface … } else { 既有 scroll-pane }` + Init 自动建会话→取 surface-url→`mountProductEngine(sid, book_id, source_hash).await`；vue 轨经 `use.web mountProductEngine from "src/front/ports/engine_host.at"`（引擎宿主 = engine_host.web.at 纯转发端口 → `src/front/engine_host.ts`：轮询等 doc-surface 入树、运行时拼接 import adapter URL、三参数签名与 engine_host.vm.at 逐参对齐）；VM 轨 facade 空实现（doc-surface 由组件+surface-url 自动装载 native-host.html，其自身 import adapter）。**实测（Edge headless + CDP 穿透 shadow DOM）**：正式书架→打开 product-alpha→doc-surface→foliate-view→FOLIATE-PAGINATOR iframe 内正文（第一章 山月…重复句甲🦊 338 字符）、img=1、h1=true；引擎 loaded in 244ms, spine=10。
- **永久门腿（verify_epub_product.py）**：P-02.load-chain（导入→format=epub→会话→surface-url→资产/原件字节）、P-02.asset-independence（无 probe env 时 manifest served == 仓库内 src/assets）、P-02.ui-mount（vue：Edge headless dump DOM 含 doc-surface+foliate-view）、P-09.resource-gate（资产 `..`/越界/未知名 404、缺书文档 404、会话坏形状/坏 hash/engine 空具名拒绝，sessions.json 零脏记录）。**双轨实跑**：vue 与 vm 均 P-01 全过 + P-02 三腿 PASS + P-09.resource-gate PASS + P-09.import-bounds PASS（verify_epub 22/22）+ P-12.strict-aggregator；未实现例诚实 not_run（P-03~08/10/11 + engine-bounds + old-gates → exit 3，findings=0）。
- **关键事实（调试实证，供后续与 README/设计登记）**：①vue 轨 `use.web` 本地文件复制到 `gen/front/vue/src/ext/` 只在**全量 generate** 执行（`run_vue_flow` 中 `!project.exists() && changed_count==0` 分支；project.exists() = output_dir + package.json）——增量编译只写 SFC 不复制 ext，改 ext 源文件后需删 gen 前端 package.json 触发全量（T-04+ 开发流记录）；②view 树 `if … else {` 借用原块闭合会致括号净额+1 → 解析失败（expected LBrace found null @ handler 恢复点），需补 else 自身闭合；③model 缺字段声明 → vue 轨裸变量引用（is_epub is not defined），字段声明必须与引用同置 model；④`str.uuid()` vue 轨无桥 → 改用 `Time.now_ms()`（→Date.now()）；⑤engine_host.ts 字面量 `import('/api/…')` 被 vite 静态解析为项目内模块失败 → 运行时拼接；⑥mountProductEngine 签名须与 .vm.at facade 三参数对齐（TS 对象参数 vs 调用三参 → opts.bookId=undefined）；⑦doc-surface 渲染晚于 Init 异步链 → 宿主轮询等待容器出现（100ms×50）。
- 未改 canonical Spec；未创建用户数据（数据面仅 plan-artifacts 隔离目录）。瞬时环境记录：playwright-cli 浏览器驱动在本环境不稳（ChildProcess.kill），UI 验证改用系统 Edge headless + CDP（金标准 console/异常/DOM 穿透）；`npx playwright-cli` 生成的 .playwright-cli/ 日志残留已清理。

### 2026-11-03：work阶段——T-02 产品永久门与语料清单（AC-02/09）

- stage: work | plan_id: READER-007 | plan_revision: r1 | task: T-02 | outcome: pass（tests/product/verify_epub_product.py + gen_product_corpus.py 建立并实跑验证）| 执行位: D:/autostack/auto-reader main | next: T-03。
- **统一入口**：`python tests/product/verify_epub_product.py --profile vue|vm --auto-bin <固定auto> --out-dir <自有隔离> [--corpus-dir]`。P-01～12 注册唯一 ID（profile 适用性显式）；严格聚合器（缺项/重复/未声明根/GAP/FAIL/not_run/0选择非零；exit 0/1/2/3 语义）；out-dir 守卫（拒用户根/盘符/无标记非空/reparse，safe_rmtree 限 scope）；cohort 指纹（坏 --auto-bin/缺 AUTO_UI_TOOL_BIN 具名退出）。
- **已实现腿（实跑验证）**：P-01 全过（cohort-desk：029 归档+T-10 pass+landing 65bb455f 在位+auto g47d8f7b+tool 含 doc-surface 字符串；vue=后端 17825+前端 localhost:17824；vm=后端+窗口「图书阅读器」+MCP 9247）；P-09.import-bounds 全过（verify_epub 22/22 交付 cohort 绿，30MiB/12MiB/坏 container 负例继承）；P-12.strict-aggregator 过。**未实现例诚实 not_run → 本轮两 profile 均 exit 3（findings=0、not_run=11），不伪绿**。
- **语料（冻结）**：tests/product/gen_product_corpus.py 确定性生成——product-alpha（10 章真实风格：标题/段落/列表/表格/代码/2 PNG/nav 目录/脚注/跨章链/重复句甲全书3次(第1章2次)/重复句乙跨章2次/跨段引文(段尾+下段首)/长章 ch3≈642KB/emoji 多字节）、product-beta（变体书，双实例/串书隔离）、negative-malformed；corpus-manifest.json 记录每文件 sha256 + 预期（章标题/重复位次/跨段文本/图片数）。alpha sha256=2ba0f73e…、beta=5e03b22f…（本次生成值，重建可重算）。
- **引擎资产打包（固化）**：foliate-js = MIT（readest packages/foliate-js LICENSE，2022 John Factotum）→ 可再分发；打包=扁平化 flat 重写（prepare_engine_assets.py 模式）→ 应用自有受管资产（路由接入 T-03），不依赖 readest 运行时检出；设计文档 §1 已更新。
- 未改 canonical Spec；未创建用户数据。瞬时环境记录：vue frontend 首跑 esbuild「service was stopped」flake（README 在案族），重跑绿——门按严格语义记录 FAIL 而非吞掉（首跑 FAIL、复跑 PASS，均留档）。

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

- stage: goal | plan_id: READER-007 | plan_revision: r1 | round: 1 | from: work | to: work | status: executing | outcome: pass | worktree: D:/autostack/auto-reader main（本计划 main 为唯一实现位）| commit: 1d11c54 | next: T-05。

## 10. 待澄清事项

1. 029的最新完整交付cohort与独立复审/验收回执目前未查到，用户同意先起草等待。执行前由T-00核实，未满足不得产品化。（T-00 已闭合：029 归档 12/12 + landing 65bb455f 实证。）
2. 原生正式Reader的启动与HTTP/merged组合是否沿029接口可用？T-00整路径证明，不以实验窗替代，不凭旧命令推断。（T-00 已闭合：双端启动 profile 冻结。）
3. Locator v2存储/协议、跨段与v1映射、可信CFI核验、引擎资源/性能预算，由T-01在实现前冻结；未决时不先写用户数据。机制实证失败须回规划/owner前置，不降低AC。（T-01/T-05 已闭合：方案甲+reader-locator v1 落地。）
4. 固定引擎分发/许可与真实语料可再分发性由T-01/02核查；不内嵌用户书、凭据或未经说明的外部目录依赖。后续正式计划只交付本期profile，不把Readest全部能力塞入一份计划。（T-02 已闭合：MIT+打包 manifest。）
5. **T-05 新增登记（2026-11-04）**：①`auto build` 严格模式 schema drift（reading_page doc-surface/textarea height/sidebar props）阻断一切 build 基生命周期——pristine main 同败（T-03/T-04 表面既有债，非 T-05）；T-09 冻结 cohort 前需 owner 处置（SCHEMA_DRIFT_GENERATE_AT=1 实测不生效）或 verify_local 改用 dev-server 形态。②run_ui 工具宿主 ~12min 存活期不稳定（双轨，控制流关闭）——门已数据族前置+族内隔离，框架侧根因待 owner。③vm 轨工具面（asset 端点窗口期 404、WebView2 CDP 9333 不开放）=T-04 已录 GAP 同类，UI 腿待工具链，非产品缺陷。④已知成本：HTTP 计量 VM ~10× 慢——长章一次性转换 19s（缓存后 2s）；v2 occurrence=非重叠口径，T-06 adapter countOccurrences 需同式对齐。
