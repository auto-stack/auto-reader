# AutoReader 产品规划与执行入口

更新：2026-11-01。001～005 已交付；当前新增计划为 **006 Readest 详细调研与路线再设计**，drafting/r1，尚未执行。

- [产品总设计：覆盖 Readest](design/01-product-design.md)
- [路线图：研究先行、再确定实施计划](roadmap-v0.6.md)
- 现实现：[书库](specs/reader/real-library.md) · [EPUB](specs/reader/epub-reflow.md) · [注释](specs/reader/reading-annotations.md) · [独立阅读](specs/reader/standalone-reading.md)
- [早期业界调研（历史参考）](research/20261004-benchmarks.md)；006 详细报告尚未产出。

## 计划

| 计划 | 当前范围/状态 |
|---|---|
| [001 真实书库与恢复](plans/archive/001-real-library.md) | archived/r9、32/32 |
| [003 最小 EPUB](plans/archive/003-epub-reflow.md) | merge 24c9838 已有回执；旧元数据差异保持历史，后由 005 接续 |
| [002 本地阅读与注释](plans/archive/002-reading-annotations.md) | archived/r4；本地 A 收尾，历史计数 7/9；Notes 交接为 OS TODO |
| [004 驱动/夹具归属](plans/archive/004-reader-test-ownership-migration.md) | archived/delivered；框架正对照/HTTP 保存有明确边界 |
| [005 真实 EPUB 阅读与双端收口](plans/archive/005-standalone-epub-and-ui-acceptance.md) | archived/r1、9/9；原生写传输与自动化按压缺口仍在册 |
| [006 Readest 详细调研与路线再设计](plans/006-readest-deep-research.md) | drafting/r1、0/10；文档/代码/UI → 覆盖和架构决策 → 总设计/路线二次修订 → 后续计划建议 |

## 工作约定

使用 D:/autostack/auto-reader 独立 clone main 进行计划、实现与顺序复审，一 app 一写入者，不建 junction/symlink，不在 OS 子模块开发。Readest 源码在 006 执行阶段使用独立真实 clone；本次不克隆、不运行竞品、不实现产品功能。

现实现单源为 docs/specs/；本次只更新 proposed 总设计、路线、导航和 006，不改 Spec、旧 ledger 或 OS gitlink。后续实施先完成调研与二次修订，不提前确定引擎或 Plan 编号。Notes 留系统协同，Linux 仍等 Nix＋COSMIC 基础。

[运行与测试完整入口](../README.md)
