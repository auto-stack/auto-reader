# AutoReader 产品规划与执行入口

更新：2026-11-01（006 调研交付后）。001～005 已交付；**006 Readest 详细调研已完成研究任务**（待独立复审与归档），产出五份研究报告与总设计/路线二次修订。

- [产品总设计：覆盖 Readest（coverage v2）](design/01-product-design.md)
- [路线图：首批计划建议 P1~P6](roadmap-v0.6.md)
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
| [006 Readest 详细调研与路线再设计](plans/006-readest-deep-research.md) | work 完成（r1，7/10）；T-08 独立复审、T-09 归档待行；产出 = 上表五份研究报告 + 总设计/路线二次修订 |

## 工作约定

使用 D:/autostack/auto-reader 独立 clone main 进行计划、实现与顺序复审，一 app 一写入者，不建 junction/symlink，不在 OS 子模块开发。006 研究基线：Readest 源码检出 `D:/autostack/readest`（detached v0.12.16，只读），实际 UI 证据在 `D:/autostack/plan-artifacts/plan-006/`。

现实现单源为 docs/specs/；006 只更新 proposed 总设计、路线、导航、研究报告与计划本身，不改 Spec、旧 ledger 或 OS gitlink。后续实施（P1~P6 经用户认可后另立计划取号）先探针后承诺，不提前锁定引擎。Notes 留系统协同，Linux 仍等 Nix＋COSMIC 基础。

[运行与测试完整入口](../README.md)
