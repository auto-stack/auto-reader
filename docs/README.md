# AutoReader 产品规划与执行入口

更新：2026-11-01。001～006 均已交付；006 交付基线、矩阵、源码地图、UI 研究、决策与综合报告，并完成 coverage v2。本次依据其结果进一步收敛总设计/路线为 **coverage v3**，尚未新增实施计划。

- [产品总设计：覆盖 Readest（coverage v3）](design/01-product-design.md)
- [路线图：引擎探针优先，随后形成 EPUB 产品闭环](roadmap-v0.6.md)
- 现实现：[书库](specs/reader/real-library.md) · [EPUB](specs/reader/epub-reflow.md) · [注释](specs/reader/reading-annotations.md) · [独立阅读](specs/reader/standalone-reading.md)
- 006 研究：[综合报告](research/readest/report.md) · [能力矩阵](research/readest/capability-matrix.md) · [代码地图](research/readest/code-map.md) · [UI 研究](research/readest/ui-study.md) · [决策](research/readest/decisions.md)；历史参考[早期业界调研](research/20261004-benchmarks.md)

## 计划

| 计划 | 当前范围/状态 |
|---|---|
| [001 真实书库与恢复](plans/archive/001-real-library.md) | archived/r9、32/32 |
| [003 最小 EPUB](plans/archive/003-epub-reflow.md) | merge 24c9838 已有回执；旧元数据差异保持历史，后由 005 接续 |
| [002 本地阅读与注释](plans/archive/002-reading-annotations.md) | archived/r4；本地 A 收尾，历史计数 7/9；Notes 交接为 OS TODO |
| [004 驱动/夹具归属](plans/archive/004-reader-test-ownership-migration.md) | archived/delivered；框架正对照/HTTP 保存有明确边界 |
| [005 真实 EPUB 阅读与双端收口](plans/archive/005-standalone-epub-and-ui-acceptance.md) | archived/r1、9/9；原生写传输与自动化按压缺口仍在册 |
| [006 Readest 详细调研与路线再设计](plans/archive/006-readest-deep-research.md) | archived/r1、10/10；产出 = 五份研究报告 + 总设计/路线二次修订（coverage v2）；后续 P1~P6 建议待取号 |

## 工作约定

使用 D:/autostack/auto-reader 独立 clone main 进行计划、实现与顺序复审，一 app 一写入者，不建 junction/symlink，不在 OS 子模块开发。006 源码基线为 `D:/autostack/readest`（detached v0.12.16，只读）。原始 UI 运行目录已按归档回执清理；以研究耐久摘要与归档复审记录为依据，必要时按 baseline 重建隔离环境。

现实现单源为 docs/specs/；本次只更新设计、路线与导航，不改研究报告、归档合同或业务实现。006 的 P1~P6 为候选代号，v3 推荐先做 P2，再据真实引擎/定位契约安排 P1 与完整 EPUB 交付；P3 分期推进。正式计划另行取号，Notes 留系统协同，Linux 仍等 Nix＋COSMIC 基础。

[运行与测试完整入口](../README.md)
