# AutoReader 产品规划与执行入口

更新：2026-11-01。001～006均已交付，现行设计/路线为coverage v3。正式后继探针为 **auto-ui/PLAN-026**（drafting/r1、0/10），仅规划、暂不实施；Reader保留跨仓指针，不分配007。

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
| [auto-ui/PLAN-026 阅读引擎嵌入与定位回传探针](https://github.com/auto-stack/auto-ui/blob/master/docs/plans/026-reader-engine-embedding-and-locator-probe.md) | drafting/r1、0/10；UI持唯一合同并负责宿主/桥/资源与清理，Reader负责隔离受管EPUB、纯.at消费/保存/恢复与独立oracle；双端各自验收，暂不实施 |

## 工作约定

使用 D:/autostack/auto-reader 独立 clone main 进行计划、实现与顺序复审，一 app 一写入者，不建 junction/symlink，不在 OS 子模块开发。006 源码基线为 `D:/autostack/readest`（detached v0.12.16，只读）。原始 UI 运行目录已按归档回执清理；以研究耐久摘要与归档复审记录为依据，必要时按 baseline 重建隔离环境。

现实现单源为docs/specs/；本次仅UI/026起草与导航，不改研究报告/归档/产品代码。P2已正式起草，后续依其真实结论安排P1与完整EPUB交付，P3分期。026未来UI代码用其独立实施树，Reader消费改动按本仓main单写者纪律顺序执行/复审。Notes留系统协同，Linux仍等Nix＋COSMIC基础。

[运行与测试完整入口](../README.md)
