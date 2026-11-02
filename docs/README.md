# AutoReader 产品规划与执行入口

更新：2026-11-03。新增 [READER-007：正式EPUB阅读表面接入与定位兼容](plans/007-epub-product-reader-and-locator-compatibility.md)（drafting/r1、0/13），当前只起草，等待auto-ui/029全部必需门、独立review与固定版本交付后实施。本地029仍executing、9/12，不能按已完成处理。

- [产品总设计：覆盖 Readest（coverage v5）](design/01-product-design.md)
- [路线图：原生输入与接缝收口后进入EPUB产品化](roadmap-v0.6.md)
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
| [auto-ui/PLAN-026 阅读引擎嵌入与定位回传探针](https://github.com/auto-stack/auto-ui/blob/master/docs/plans/archived/026-reader-engine-embedding-and-locator-probe.md) | archived/r1、流程10/10；Vue指定样本30/30，原生嵌入/引擎/IPC已证，输入/IME/无障碍及部分隔离负控未闭合；下一阶段先补原生链，不能按归档算双端全门go |
| [auto-ui/PLAN-029 原生输入链与必要接缝收口](https://github.com/auto-stack/auto-ui/blob/master/docs/plans/029-reader-native-input-and-surface-closure.md) | 本次核查executing、9/12；已有原生接入及多项门证据，Vue重排GAP、最终冻结验收/独立review/交付待核；007实施硬前置，不改其在途合同 |
| [007 正式EPUB阅读表面与定位兼容](plans/007-epub-product-reader-and-locator-compatibility.md) | drafting/r1、0/13；Reader主导，正式书架/reading_page、结构样式与导航、精确标注、v1/v2兼容和冷恢复；依赖029全门交付，未实施 |

## 工作约定

使用 D:/autostack/auto-reader 独立 clone main 进行计划、实现与顺序复审，一 app 一写入者，不建 junction/symlink，不在 OS 子模块开发。006 源码基线为 `D:/autostack/readest`（detached v0.12.16，只读）。原始 UI 运行目录已按归档回执清理；以研究耐久摘要与归档复审记录为依据，必要时按 baseline 重建隔离环境。

现实现单源为docs/specs/；本次仅007合同与导航，不改产品代码/Spec，也不接管029的driver_vue.py WIP。029实际门/独立review与固定交付不齐则007不实施；007使用独立clone main单写者顺序开发/复审，UI仅作为已交付依赖。

[运行与测试完整入口](../README.md)
