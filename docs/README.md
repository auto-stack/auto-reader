# auto-reader 产品规划与执行入口

更新：2026-10-31。当前后续为005；001/003/002本地A/004交付范围与遗留覆盖见[路线图](roadmap-v0.6.md)，历史产品设计保留目标态。

- [产品设计与UI/UX（目标态）](design/01-product-design.md)
- [现实现书库规范](specs/reader/real-library.md) · [EPUB规范](specs/reader/epub-reflow.md) · [本地注释规范](specs/reader/reading-annotations.md)
- [业界调研](research/20261004-benchmarks.md)

## 计划

| 计划 | 当前范围/状态 |
|---|---|
| [001真实导入、书库与恢复](plans/archive/001-real-library.md) | archive/r9、32/32，保持历史 |
| [003最小EPUB](plans/archive/003-epub-reflow.md) | merge24c9838已有回执；归档frontmatter仍drafting的差异不在本轮改写；图片/链接/UI门由005接续 |
| [002本地阅读与注释](plans/archive/002-reading-annotations.md) | archived/r4；以本地A收尾，历史计数7/9；Notes交接按用户决定移OS TODO |
| [004驱动/夹具归属](plans/archive/004-reader-test-ownership-migration.md) | archived/delivered；框架正对照与HTTP保存不能代替所有真实产品操作 |
| [005真实EPUB阅读与双端收口](plans/005-standalone-epub-and-ui-acceptance.md) | drafting/r1、0/9；先T-00探针，未实施 |

## 工作约定

计划、实现与顺序复审使用D:/autostack/auto-reader独立clone main；一app一写入者，保留他人WIP，不建junction/symlink、不在OS组合子模块开发。框架缺项核实实际owner后另立最小前置，不沿历史归因重做已有能力。应用逻辑纯.at，测试隔离数据与自有进程。

本轮只建立/推送计划和导航文档，不实现、不改现实现Spec或旧ledger，也不更新AutoOS子模块。后续单独运行验收后由OS统一计划接收固定SHA。Notes交接与Linux不作为005前置；Linux仍等Nix＋COSMIC基础。

[运行与测试完整入口](../README.md)
