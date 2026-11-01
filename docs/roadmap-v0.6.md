# AutoReader 路线图：从独立阅读到覆盖 Readest

更新：2026-11-01（**coverage v3：006 交付后的设计收敛与后续顺序讨论**）。沿用此路径保持链接兼容；长期覆盖目标不等于所有能力必须在 v0.6 一次交付。

## 1. 新目标与决策顺序

以 Readest 开源项目为主要参照，逐步覆盖其绝大多数已核实的能力，涵盖阅读/排版、选区/标注、书库、多格式、辅助阅读、书源、同步与互操作。

用户指定顺序：**先更新总设计与路线 → 详细调研 Readest 文档、代码和实际 UI → 根据调研修订设计与路线 → 确定后续计划**。006 已交付研究；v3明确阅读表面探针优先，定位迁移依赖真实契约，探针后交付EPUB产品闭环。用户现已同意按此顺序先起草探针，正式合同为 [auto-ui/PLAN-026](https://github.com/auto-stack/auto-ui/blob/master/docs/plans/026-reader-engine-embedding-and-locator-probe.md)，drafting/r1、0/10，**暂不实施**。其他P1/P3～P6仍是候选代号。

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

## 4. 后续计划讨论：推荐的决策顺序

[006 决策 §5](research/readest/decisions.md) 的 P1~P6 保留为研究来源。P2已起草为auto-ui/PLAN-026，其余未取号；**所有功能暂不实施**。应用数据与服务保留纯 .at 主干，阅读表面优先验证成熟引擎接入，不把“B 主干”理解成重写排版系统。

| 建议阶段 | 对应候选 | owner 与依赖 | 收敛后的范围与交付门 |
|---|---|---|---|
| **已起草、暂不实施** | P2 → [auto-ui/PLAN-026](https://github.com/auto-stack/auto-ui/blob/master/docs/plans/026-reader-engine-embedding-and-locator-probe.md) | auto-ui主导宿主与双端桥；auto-reader最小纯.at消费者 | 固定引擎与受管EPUB；Vue/原生VM分别走显示→真实选区→事件/定位回传→探针sidecar→冷恢复。焦点/IME、几何/重排、系统无障碍、身份拒绝和清理分别验收；go与研究完成分开 |
| 可独立准备，实施后置冻结 | P1：锚契约/迁移 → Locator v2 | 现有 schema/旧库核对可先做；实际新定位模型依赖 P2 输出 | 保留 book_id/annotation_id、quote/occurrence 与 v1 读能力；真实文档树/转换器未证前不批量补 CFI、不用空字段充交付、不默认升级书籍 import_version |
| 独立的小范围日用改进 | P3：分期补齐书库 | auto-reader；系统文件选择能力先核实，无引擎依赖 | 先讨论文件选择/批量导入与逐本失败反馈、排序筛选；书封/元数据、分组标签、跨书搜索分别按完整用户任务拆分，不塞入一个大计划 |
| **探针结论后的核心产品交付** | EPUB 阅读表面与选区/标注闭环（承接 P1/P2） | 所选引擎接缝、真实定位模型和迁移方案已具备 | 出版物样式、图/脚注、分页/滚动、选择重复句指定一处、行内高亮、搜索回跳、旧注释兼容与重启恢复；按冻结样本和支持 profile 双端验收 |
| 后续分域 | P6：PDF/漫画评估与实施拆分 | 依赖 P2 **结论**，不要求一定通过 | 明确固定版式、缩放/文本层/页锚、漫画模式；不能拿 EPUB 或 Readest 未验证的 PDF 标注当现成成功依据；A 不可用时继续评估替代引擎 |
| 后续分域 | P5：TTS 本地面 | 宿主 speech 能力核对可提前；句级导航/高亮依赖实际文本与定位模型 | 本地语音播放/暂停/跳句，朗读高亮与用户选区不互相破坏；不默认引擎嵌入成功就拥有 TTS |
| 随定位契约推进 | P4：导出与互操作 | 稳定来源/定位契约；系统 URI 注册另属 OS | 先交付可解析的 Markdown/JSON 来源与真实 app 内回跳；自定义 scheme 不未经系统契约就承诺已注册/可用 |

P2 先核对当前宿主能力，避免重做已有接口。上游 foliate-js 可作对照，但主验证应覆盖 006 固定的 Readest fork 或明确列差异；简单打开上游样本只证明宿主/样本路径，不证明 254-commit fork 的能力已获得。性能记录固定机器、样本和冷热状态，探针不承诺发布级性能。

P2 失败时不自动缩小“覆盖 Readest”的目标，先给接缝修复/替代引擎的证据和代价，再讨论路线变化。P1、P3 的“可独立”表示依赖独立；同一 app 仍只有一个写入者，执行按序协调。

### 长期覆盖范围保留

其他格式（MOBI/AZW3/FB2/HTML 等）、双书对照、词典/翻译、统计/辅助阅读、OPDS、自建书库、本地备份恢复与多设备同步继续保留在矩阵中。优先形成完整本地 EPUB 体验，再按依赖与价值分域扩展；云端成功面、账号与付费条件单列，不预设必须复刻 Readest 的商业套餐。

257 是固定发布对照行数，不是当前实现覆盖率。AutoReader 102 行待验证和 4 行待裁定排除保留原状态，不能算成已缺失/已获准排除；每份正式计划先绑定 RDT ID 和核心任务。P2 与受影响能力核对后提出阶段目标，避免实现完再倒定标准。平台矩阵另列，Linux 仍 WAIT_DISTRO_M1，移动/电子墨水不直接成为当前必达。

## 5. 研究收口与后续入口

调研已收口，研究基线与归档合同不改；本次 v3 明确五处细化：P2 优先、P1 schema 冻结依赖真实定位契约、增加探针后的 EPUB 产品闭环、P3 分期、P6 依赖探针结论而非必须成功。服务能力审计可先行，端到端交付仍按真实依赖推进。

正式探针合同现为auto-ui/PLAN-026，本仓仅保留指针与消费责任，不分配READER-007复制正文。主改面已核为UI宿主/生成/桥接，Reader在独立clone main提供tests/probe/engine_surface/（未来新增）、隔离受管资产、.at handler与独立读回oracle。两端均要真实输入与冷恢复，不以API预写或外开浏览器替代；单端通过不能推导另一端通过。研究可交付有证no_go_current_profile，但不能将失败门计PASS或自动降目标。

静态核查发现UI已有View::Text.selectable、View::Rich和RemoteFrame，故不把“无任何选择/富文本”当起点；但文本选择在widget本地，RemoteFrame是DisplayList与输入承载，Embed是块面板，均未证明DOM/CFI→.at链路。

**026 探针结果（2026-11-02，见 auto-ui `docs/research/reader-engine-probe.md` 与边界 Spec `docs/specs/runtime/document-surface-boundary.md`）**：vue 表面全链 go（真实导入身份→remote-frame 接缝挂 foliate-js@3d79419→真实拖选 CFI→.at 原文核验（逐字+出现位次吻合独立 oracle）→sidecar→冷重启恢复，30/30）；原生 iced 宿主内 WebView2 嵌入与引擎装载已证，注入输入回传具名 GAP（自动化环境侧，人工拖选待验）。本仓消费工程沉淀于 `tests/probe/engine_surface/`（verify_engine_surface.py 永久入口）。定位迁移（Locator v2）契约建议见报告 §5；阅读表面产品闭环据此另立计划。原生WebView接法、偏移单位与协议预算由026的T-00在实现前冻结；当前未创建实施树、未改代码、未构建或启动探针。

已证实/被推翻/仍未验证的假设见[报告](research/readest/report.md)，矩阵保留功能追踪，当前实施态仍由 Spec 描述。

## 6. 工程与系统依赖

使用 D:/autostack/auto-reader 独立 clone main，一 app 一写入者，顺序复审用同一检出；不在 OS 子模块内开发。006 为研究计划：不改当前 Spec、旧 ledger、业务源码或 OS gitlink；Readest 源码检出（D:/autostack/readest）仅作研究只读基线，不在其中开发。后续实施计划按各自 Spec 增量流程沉淀。

框架能力先实查 owner/版本，不沿用“没有 image widget”或旧 zip 首红等失效归因。原生写传输与 scroll-pane 工具路径缺口保留并核验当前状态；修复另走实际 owner 的计划。非框架修改不在 auto-lang 跑 cargo/docs_gen。

Notes 交接仍属 OS 协同，不重开 002-B；组合装配由统一 OS 计划接收精确提交。独立研究与应用交付不以系统装配或 Linux 为前置。

[README](../README.md) · [规划入口](README.md) · [总设计](design/01-product-design.md)
