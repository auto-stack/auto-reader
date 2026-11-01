# 设计入口

更新：2026-11-02（026归档后的证据边界与原生收口）。产品目标为覆盖 Readest 的绝大多数能力；详细调研已交付，总设计与路线现为 **coverage v4**。

| 文档 | 状态 | 范围 | 对应计划 |
|---|---|---|---|
| [01 产品总设计](01-product-design.md) | proposed / **Readest coverage v4** | 固定研究基线与证据边界、应用数据主干、阅读表面探针优先、锚迁移依赖、双端与产品闭环 | 基于 [READER-006](../plans/archive/006-readest-deep-research.md)（archived/r1），后续计划尚未取号 |
| [调研报告](../research/readest/report.md) · [能力矩阵](../research/readest/capability-matrix.md) · [代码地图](../research/readest/code-map.md) · [UI 研究](../research/readest/ui-study.md) · [决策](../research/readest/decisions.md) | delivered（已归档） | 257 项发布能力对照、真机 U01~U07、三路线裁定、P1~P6 首批计划建议 | READER-006 |

当前实现以 [Specs](../specs/reader/standalone-reading.md) 为准。[auto-ui/PLAN-026](https://github.com/auto-stack/auto-ui/blob/master/docs/plans/archived/026-reader-engine-embedding-and-locator-probe.md)已归档（流程10/10），Vue指定样本30/30，原生嵌入/装载/IPC已证但真实输入与应用回传/恢复未闭合。下一阶段先收口原生输入、必要接缝与失败/隔离门，再进入Locator v2与完整EPUB产品化；分工/退出门见[路线图](../roadmap-v0.6.md)，本次未新取号或实施。
