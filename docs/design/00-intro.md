# 设计入口

更新：2026-11-01（006 交付后的设计收敛）。产品目标为覆盖 Readest 的绝大多数能力；详细调研已交付，总设计与路线现为 **coverage v3**。

| 文档 | 状态 | 范围 | 对应计划 |
|---|---|---|---|
| [01 产品总设计](01-product-design.md) | proposed / **Readest coverage v3** | 固定研究基线与证据边界、应用数据主干、阅读表面探针优先、锚迁移依赖、双端与产品闭环 | 基于 [READER-006](../plans/archive/006-readest-deep-research.md)（archived/r1），后续计划尚未取号 |
| [调研报告](../research/readest/report.md) · [能力矩阵](../research/readest/capability-matrix.md) · [代码地图](../research/readest/code-map.md) · [UI 研究](../research/readest/ui-study.md) · [决策](../research/readest/decisions.md) | delivered（已归档） | 257 项发布能力对照、真机 U01~U07、三路线裁定、P1~P6 首批计划建议 | READER-006 |

当前实现以 [Specs](../specs/reader/standalone-reading.md) 为准。v3的首份后继已起草为 [auto-ui/PLAN-026](https://github.com/auto-stack/auto-ui/blob/master/docs/plans/026-reader-engine-embedding-and-locator-probe.md)（原P2，drafting/r1、0/10，暂不实施）。本仓为消费方，仅留指针；后续再据真实契约冻结新定位模型与EPUB完整阅读闭环，分工见[路线图](../roadmap-v0.6.md)。
