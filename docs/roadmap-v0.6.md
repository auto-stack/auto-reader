# auto-reader：独立可用性路线图

更新：2026-10-31。现实现以Spec和实际交付为准；归档记录的历史元数据差异不通过改写旧计划掩盖。

| 阶段 | 计划/成果 | 当前状态与证据边界 |
|---|---|---|
| 基础 | [001真实书库与恢复](plans/archive/001-real-library.md) | archive/r9、32/32，10MiB与内容锚点已有交付；不等于全EPUB/全UI验收 |
| EPUB数据面 | [003最小EPUB](plans/archive/003-epub-reflow.md) | merge24c9838/landing21/21已有记录；图片标记、链接和UI门留缺口。旧frontmatter仍drafting，仅登记此差异 |
| 本地增强 | [002 r4本地A](plans/archive/002-reading-annotations.md) | 已按用户裁决收尾；搜索/注释/Markdown导出已落地，原生门有历史skip；7/9为旧计数，不擅自重写 |
| 测试归属 | [004驱动与夹具迁入](plans/archive/004-reader-test-ownership-migration.md) | archived/delivered；CLI/tool身份已纠正，导入36/36及原生required有记录；实际保存含HTTP面，非所有产品UI行为证明 |
| 当前优先 | [005真实EPUB阅读与双端收口](plans/005-standalone-epub-and-ui-acceptance.md) | drafting/r1、0/9，未实施；T-00先查现有image/媒体URI、真实输入与预算；依001/003/002本地A/004交付，不等Notes或Rust全映射 |

005闭合：独立split启动→真实UI导入→图像（首次/缓存/冷重启正确）→书内/脚注往返→搜索/20条注释回访与导出→实际保存/退出重开/下一次编辑。新增门必须检测错图/错锚/假UI成功，原生必需任务不能保留skip。

AutoUI已有Vue图片发射、原生图片路径与auto-photos消费者，应先核验接入，不沿“没有image widget”的旧归因直接建框架前置。旧zip首红已定位陈旧auto-ui-tool；先固定CLI＋真实tool再判断缺陷。确有框架缺项才提实际owner最小前置。

Notes交接仍为OS级TODO：等待应用间通讯协议和能力包共享机制，未来另立计划，不恢复002-B。PDF/OCR/TTS/复杂出版物与网络书源继续后置。Linux仍WAIT_DISTRO_M1。

开发位为D:/autostack/auto-reader独立clone main；本轮只计划/文档并push，不实现、不更新AutoOS子模块。后续以统一OS计划装配已单独验证的精确交付提交。

[README](../README.md) · [规划入口](README.md) · [现实现规范](specs/reader/real-library.md)
