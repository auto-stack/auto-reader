# AutoReader 路线图：从独立阅读到覆盖 Readest

更新：2026-11-01（**006 调研后二次修订**）。沿用此路径保持链接兼容；长期覆盖目标不等于所有能力必须在 v0.6 一次交付。

## 1. 新目标与决策顺序

以 Readest 开源项目为主要参照，逐步覆盖其绝大多数已核实的能力，涵盖阅读/排版、选区/标注、书库、多格式、辅助阅读、书源、同步与互操作。

用户指定顺序：**先更新总设计与路线 → 详细调研 Readest 文档、代码和实际 UI → 根据调研二次修订设计与路线 → 确定后续实施计划**。前两步已完成：调研交付了 257 项发布能力对照（[能力矩阵](research/readest/capability-matrix.md)）、真机 U01~U07 实测（[UI 研究](research/readest/ui-study.md)）、引擎三路线裁定与首批计划建议 P1~P6（[决策](research/readest/decisions.md)、[报告](research/readest/report.md)）；总设计已二次修订为 coverage v2。当前处于"确定后续实施计划"阶段：P1~P6 经用户认可后另行取号。

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
| [006 Readest 详细调研与路线再设计](plans/006-readest-deep-research.md) | work 完成/待复审（r1，8/10 任务） | 基线固定（tag v0.12.16=3cc39ad7 + 官方 portable 同版）；257 项发布能力×稳定 ID 对照（=全量 259 行 − 2 行非发布）；代码地图（12 条链路/12 格式/fork 差异 path:line）；真机 U01~U07（核心日用链路全绿，2 个 Windows 缺陷实证）；三路线裁定与 P1~P6 建议；总设计/路线/导航二次修订 |

调研源检出 `D:/autostack/readest`（detached v0.12.16，子模块按 tag 检出）；UI 证据与运行记录在 `D:/autostack/plan-artifacts/plan-006/`（复审可复演）。真机发现如实登记：对话框导入受管副本缺失+打开静默失败、软删不去重、页码口径滞后、移除确认待复验（[UI 研究](research/readest/ui-study.md) §1/§2）。

区分已发布、主分支新增、计划中、未核实；每项有稳定 ID、来源/版本、代码/UI 证据、AutoReader 状态、差距与建议（矩阵承载）。云服务、账号、付费和设备限制显式登记（约 25 项服务闸），不以无法体验判定已支持或无需支持。

## 4. 首批后续计划建议（P1~P6，调研收口产出）

以下为[决策 §5](research/readest/decisions.md) 的建议顺序，**无编号、未立项、未自动创建**；经用户认可后另立计划取号。

| 序 | 候选计划 | owner | 依赖 | 一句话范围 | 优先级理由 |
|---|---|---|---|---|---|
| P1 | Locator v2 与注释锚扩展 | auto-reader | 无 | cfi/page 可选字段 + 兼容迁移 + 逐字锚保留为失配仲裁 | 一切引擎/格式工作的地基；独立可交付 |
| P2 | 阅读引擎嵌入可行性探针 | auto-ui（框架 owner）+ auto-reader 消费 | 无（与 P1 并行） | 最小 WebView 表面装载 foliate-js 上游版，五接缝（焦点/IME/选区/滚动/无障碍）各一条真机路径 | 决定路线 A 生死，避免全量押注 |
| P3 | 书库日用面 | auto-reader | 无 | 书封/分组/标签/排序筛选/跨书搜索聚合/批量导入 | 用户可见收益最大、风险最低 |
| P4 | 导出与互操作增强 | auto-reader | P1 | 导出补稳定引用行；评估自有 deep-link 协议 | 与 P1 协同小成本 |
| P5 | TTS 本地面 | auto-ui speech 面 + auto-reader | P2 结论 | 系统 TTS 朗读 + 句级高亮 + 播放控制 | C05 最高频辅助面 |
| P6 | PDF/漫画评估（不实施） | 视 P2 | **P2 通过** | 引擎内 pdf.js/漫画渲染面评估与范围界定 | 依赖引擎结论，防无效立项 |

覆盖率目标阈值待 P1~P3 落地后按实测口径提出；功能与平台矩阵分开（矩阵 §0 口径）；Linux 仍 WAIT_DISTRO_M1，移动/电子墨水平台不直接成为当前必达项。

## 5. 研究收口与后续入口

调研已收口：已证实/被推翻/仍未验证的假设核对见[报告 §2](research/readest/report.md)；覆盖计数规则与分母见[矩阵 §0/计数节](research/readest/capability-matrix.md)；引擎与迁移有证据后形成 P1~P6 合同（[决策 §5](research/readest/decisions.md)）；探针（P2）先于任何全量移植承诺。

## 6. 工程与系统依赖

使用 D:/autostack/auto-reader 独立 clone main，一 app 一写入者，顺序复审用同一检出；不在 OS 子模块内开发。006 为研究计划：不改当前 Spec、旧 ledger、业务源码或 OS gitlink；Readest 源码检出（D:/autostack/readest）仅作研究只读基线，不在其中开发。后续实施计划按各自 Spec 增量流程沉淀。

框架能力先实查 owner/版本，不沿用“没有 image widget”或旧 zip 首红等失效归因。原生写传输与 scroll-pane 工具路径缺口保留并核验当前状态；修复另走实际 owner 的计划。非框架修改不在 auto-lang 跑 cargo/docs_gen。

Notes 交接仍属 OS 协同，不重开 002-B；组合装配由统一 OS 计划接收精确提交。独立研究与应用交付不以系统装配或 Linux 为前置。

[README](../README.md) · [规划入口](README.md) · [总设计](design/01-product-design.md)
