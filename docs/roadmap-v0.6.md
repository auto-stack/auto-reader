# AutoReader 路线图：从独立阅读到覆盖 Readest

更新：2026-11-02（**coverage v4：026 归档后先收口原生输入与必要接缝**）。沿用此路径保持链接兼容；长期覆盖目标不等于所有能力必须在 v0.6 一次交付。

## 1. 新目标与决策顺序

以 Readest 开源项目为主要参照，逐步覆盖其绝大多数已核实的能力，涵盖阅读/排版、选区/标注、书库、多格式、辅助阅读、书源、同步与互操作。

当前顺序：**006详细调研已交付 → 026探针已归档 → 先收口原生输入链与必要接缝 → 再确定Locator v2/完整EPUB产品化**。026流程记10/10，不代表双端所有能力已通过。Vue指定样本全链30/30，原生嵌入/引擎装载/IPC已证，真实输入与应用保存/恢复链仍未闭合。后续已建立 [auto-ui/PLAN-029](https://github.com/auto-stack/auto-ui/blob/master/docs/plans/029-reader-native-input-and-surface-closure.md)（drafting/r1、0/12），本次仅起草，未开始实现；Reader不另取号。

## 2. 已交付基础

| 阶段 | 计划/成果 | 当前状态与证据边界 |
|---|---|---|
| 基础 | [001 真实书库与恢复](plans/archive/001-real-library.md) | archived/r9、32/32；10MiB 与内容锚点已交付，不等于完整 EPUB |
| EPUB 数据面 | [003 最小 EPUB](plans/archive/003-epub-reflow.md) | merge 24c9838/landing 21/21；旧 frontmatter 差异保留；图像/链接后由 005 接续 |
| 本地增强 | [002 r4 本地 A](plans/archive/002-reading-annotations.md) | 搜索、注释与 Markdown 导出已交付；7/9 为历史计数；Notes 移交 OS TODO |
| 测试归属 | [004 驱动与夹具迁入](plans/archive/004-reader-test-ownership-migration.md) | archived/delivered；框架正对照/HTTP 保存不代替全部产品 UI |
| 独立可用 | [005 EPUB 实际阅读与双端收口](plans/archive/005-standalone-epub-and-ui-acceptance.md) | archived/r1、9/9；图片、链接/脚注、搜索/注释/导出/恢复；聚合门 Vue 28/VM 27 全绿，原生写传输/按压缺口在册 |

现有 EPUB 仍为文本段落与图片行，高亮为段级；005 最小 profile 不等于 Readest 覆盖完成。旧归档不为新目标改写；现实现单源仍为 [Specs](specs/reader/standalone-reading.md)。

## 3. 006 调研计划（已交付）

| 计划 | 状态 | 交付 |
|---|---|---|
| [006 Readest 详细调研与路线再设计](plans/archive/006-readest-deep-research.md) | archived/r1、10/10 | 固定 tag v0.12.16=3cc39ad7 与官方 portable 同版；257 行发布对照（259−2）；源码地图和 U01~U07 研究；引擎/迁移与 P1~P6 建议；v2 文档修订。发布盘点完整性与各功能实测深度分别说明，不宣称所有路径均已通过 |

调研源检出为 `D:/autostack/readest`（detached v0.12.16，子模块按 tag 检出）。**原始运行/截图目录 plan-artifacts/plan-006/ 已按归档回执清理**，现存研究摘要、源码与计划复审记录；旧路径不能当成仍可访问的证据。重跑时按 [baseline](research/readest/baseline.md) 重建隔离环境。

研究实证包括 EPUB 精确选区、批注、搜索、恢复与导出；同时对话框导入有受管副本缺失/打开静默失败，阅读用 argv/open-with 路径继续。PDF 打开/翻页/缩放已有观察，PDF 选区/标注仍证据不足，双书对照及服务成功面等也有未测项。用 [UI 研究](research/readest/ui-study.md) 的具体任务状态作为后续验收输入，不沿用“所有核心路径全绿”的泛化结论。

区分已发布、主分支新增、计划中、未核实；每项有稳定 ID、来源/版本、代码/UI 证据、AutoReader 状态、差距与建议（矩阵承载）。云服务、账号、付费和设备限制显式登记（约 25 项服务闸），不以无法体验判定已支持或无需支持。

## 4. 026结论与后续顺序

[auto-ui/PLAN-026](https://github.com/auto-stack/auto-ui/blob/master/docs/plans/archived/026-reader-engine-embedding-and-locator-probe.md)已归档；[研究报告](https://github.com/auto-stack/auto-ui/blob/master/docs/research/reader-engine-probe.md)与[实验边界Spec](https://github.com/auto-stack/auto-ui/blob/master/docs/specs/runtime/document-surface-boundary.md)记录实际能力。三个状态分开：流程归档、指定样本能力通过、双端产品可用，不能互相替代。

| 证据面 | 已知结果 | 仍不能据此宣称 |
|---|---|---|
| Vue实验消费者 | 引擎真实拖选→CFI/quote/出现序→.at核验→sidecar→冷恢复，30/30 | 全部026接缝/任意出版物/正式Reader产品已通过 |
| 原生独立iced实验宿主 | WebView2子表面、引擎装载与IPC已证 | 已接通AutoUI原生VM的真实选区→.at→保存/冷恢复 |
| 原生输入与系统接缝 | 注入拖选/键盘未被内容消费；人工真实拖选待验 | 故障已完全归因自动化环境，或焦点/IME/系统无障碍已可用 |
| 隔离与失败控制 | V-08双实例和V-10探针驱动负控未单列；部分同构对照在旧门中 | 两实例互扰、关闭断链和专属负控已完整验收 |
| 旧Reader门 | 本次cohort下Vue27/28、VM25/27；R-05路由404，R-06vm毁损图负控未失败 | 历史“全绿”可直接作为本次工具cohort的绿色基线 |

报告中“有条件go”保留为026研究结论，但不是原合同“双端全门go”。原复审回执记同会话复跑，后续收口需独立上下文复核；本轮没有重新复审或改写其历史结论。026原始plan-artifacts已清理，需要按固定source/tool/engine与重建脚本重新生成证据。

### 推荐阶段

| 顺序 | 工作 | owner/依赖与收口要求 |
|---|---|---|
| 已交付 | 026阅读引擎探针（原P2） | UI主导，Reader实验消费；研究流程已归档，局限保留 |
| **正式计划已起草** | [auto-ui/PLAN-029 原生输入链与必要接缝收口](https://github.com/auto-stack/auto-ui/blob/master/docs/plans/029-reader-native-input-and-surface-closure.md) | drafting/r1、0/12；UI主导、Reader消费；真实native VM链、严格必需用例集合、旧门与独立上下文review，全部通过后才能交付 |
| 可独立准备 | P1锚契约核对、P3书库小范围改进 | 仍是候选；v1/注释身份不变，Locator v2正式schema待真实双端契约；同一app单写者顺序推进 |
| 收口后产品化 | Locator v2与完整EPUB阅读闭环 | 真实原生链、输入/几何/无障碍与生命周期门闭合，再按支持profile交付分页/滚动、行内高亮、搜索回跳、旧数据兼容和冷恢复 |
| 后续分域 | PDF/漫画、TTS、导出与互操作（原P4～P6） | 依实际引擎与定位契约分别立项；PDF评估不要求某一路线必成功，TTS不能因引擎可嵌就算已有；系统URI归OS协同 |

其他格式、双书对照、词典/翻译、OPDS、本地备份和跨设备同步继续保留。257是固定发布对照行数，102行待验证与4行待裁定排除不能算成已缺失/已获准排除。各计划先绑定RDT ID和用户任务；功能与平台分列，Linux仍WAIT_DISTRO_M1，不因本次局限降低Readest覆盖目标。

## 5. 下一阶段范围与产品化退出门

下一阶段正式合同为 [auto-ui/PLAN-029](https://github.com/auto-stack/auto-ui/blob/master/docs/plans/029-reader-native-input-and-surface-closure.md)，正文在UI仓、本仓只留指针，drafting/r1、0/12。它将以下退出门落实为12项任务/12项AC，补齐真实原生VM消费者而不是继续只跑独立iced宿主；不重开026、不另取Reader号。本次未实施：

1. **输入定责**：在可控真实桌面会话确认原生焦点/鼠标/键盘输入及选区；采用真实拖选或CDP真实输入对照，记录各输入通道差异。Vue通过不能排除原生宿主/焦点/路由问题，禁止预设“仅自动化环境问题”。JS直接设置Range不能替代真实选择。
2. **原生端到端链**：固定cohort，在实际AutoUI原生VM消费者中选择重复句第2处，事件经.at核验、隔离sidecar持久化、关闭后新进程恢复同一原文。独立iced/wry spike装载或IPC成功不能替代这条链；HTTP/磁盘只做独立读回，不预写冒充UI保存。
3. **必要接缝**：焦点往返、中文IME组合不误导航；resize/缩放/重排/滚动与裁剪遮挡；系统无障碍内容/操作可达。按实际证据逐项通过，DOM ARIA或只有截图不够。若仍有GAP，应记录具体边界与处理范围，不称双端全门完成。
4. **隔离和清理**：补做双实例不同文档、迟到/错会话事件拒绝、关闭断链、端口/子进程释放和重开；补专属坏tool/占口对照，合法路径继续成功。用V-08/V-10的区分性断言检验，独立数据目录约定本身不是隔离实证。
5. **守旧门分账**：复现R-05路由404及R-06vm负控判别缺口，核实是已有缺陷、工具cohort变化还是新回归。实际owner负责最小修复/前置，不能只因Reader src没改就证明无关；不得靠HTTP绕过、吞失败或改预期使门变绿。若影响产品化验收须先闭合，具体仓别按复现定责。
6. **独立复核与状态同步**：执行证据绑定两仓source/tool/engine、逐例预期/实际和退出码，独立上下文复验原生全链与失败对照；Vue30/30重跑确认未回归，再据实际结论更新设计/路线。原生未闭合前不进入完整EPUB产品化，也不把流程计数当能力覆盖率。

UI继续拥有宿主/桥/输入/生命周期，Reader拥有受管资产、原文核验、数据与消费者验收；语言/HTTP owner的独立缺口另行明确前置。下一阶段不是移植整个Readest，也不同时做PDF/TTS/云同步或批量v1→CFI迁移。本轮没有运行这些验收，全部必需门通过方可execution_done，并由独立上下文final review后再归档；GAP/未运行/缺case/环境失败必须非零，不能沿用026有条件交付方式。Reader R-05/R-06vm按实际owner定责，必要他仓前置未交付则相关AC不能通过。

## 6. 工程与系统依赖

使用 D:/autostack/auto-reader 独立 clone main，一 app 一写入者，顺序复审用同一检出；不在 OS 子模块内开发。006 为研究计划：不改当前 Spec、旧 ledger、业务源码或 OS gitlink；Readest 源码检出（D:/autostack/readest）仅作研究只读基线，不在其中开发。后续实施计划按各自 Spec 增量流程沉淀。

框架能力先实查 owner/版本，不沿用“没有 image widget”或旧 zip 首红等失效归因。原生写传输与 scroll-pane 工具路径缺口保留并核验当前状态；修复另走实际 owner 的计划。非框架修改不在 auto-lang 跑 cargo/docs_gen。

Notes 交接仍属 OS 协同，不重开 002-B；组合装配由统一 OS 计划接收精确提交。独立研究与应用交付不以系统装配或 Linux 为前置。

[README](../README.md) · [规划入口](README.md) · [总设计](design/01-product-design.md)
