# auto-reader 产品规划与执行入口

更新：2026-10-29。001已交付归档；002/003为r3草案。历史2026-10-04产品设计保留目标态，当前实现以Spec与001最终收据为准。

- [产品设计与UI/UX（目标态）](design/01-product-design.md)
- [当前路线图：001→003→002-A→002-B](roadmap-v0.6.md)
- [业界调研](research/20261004-benchmarks.md)
- [现实现规范](specs/reader/real-library.md)
- [设计索引](design/00-intro.md)

## 计划

| 计划 | 当前状态/作用 |
|---|---|
| [READER-001：真实导入、书库存储与位置恢复](plans/archive/001-real-library.md) | archived/r9、32/32；最终复审和main landing已有记录，保持归档 |
| [READER-003：最小重排版EPUB导入与阅读](plans/archive/003-epub-reflow.md) | archived/r3；EPUB最小重排版已交付（merge 24c9838，landing 21/21） |
| [READER-002：本地体验、摘录与导出](plans/archive/002-reading-annotations.md) | archived/r4、7/9；阶段A交付落地 main=72aac4f（SD-01/02 Spec 在库，verify_local vue 50/50）；B（Notes联动）r4 移除→AutoOS TODO |
| [READER-004：Reader验收驱动与夹具归属迁移](plans/004-reader-test-ownership-migration.md) | drafting/r1；将auto-lang两组Reader夹具及对应驱动迁回应用，尚未实施 |

## 执行纪律

用户本轮只授权调整计划与跟踪，暂不开始实现。进入work前先读对应Plan、当前Spec、真实HEAD/WIP/工具链；不能看到draft就自动执行所有roadmap。

工作位为 `D:/autostack/auto-reader` 独立clone的main，顺序实现/检查/复审使用同一检出，一app一写入者。不覆盖已有 `src/front/tmp/` 等在途内容，不在AutoOS子模块内同时开发，不建junction/symlink。框架核心改动另在owner的专用worktree执行，实际跨仓依赖按环境变量→兄弟检出→主检出解析。

应用逻辑保持纯.at，不手写Rust业务后端、不修改生成Rust。测试使用独立临时数据目录与明确端口，仅关闭本次拥有的进程。当前已验入口为 `auto run --server=vm` 与 `auto run -r vm --server=vm`，17824/17825；其他组合需另有证据。

003 T-00先确认ZIP/XML/二进制、内容/图像/定位与真实输入链，给资源预算和必要owner前置；003的正文/位置由它自身交付。002-A复用003基线，Notes缺席时仍可读、注释和导出；002-B必须消费实际Notes接收，不以fixture顶替。阶段A通过只允许phase交付，002不提前终态归档。

先提交/推送app，再在干净且无人写入的AutoOS子模块更新精确交付SHA，健康检查并提交/推送父仓gitlink。组合子模块保持detached，开发clone留main；文档/计划提交同样登记pin。流程见[App开发与子模块约定](https://github.com/auto-stack/auto-os/blob/main/docs/design/strategy/app-submodule-workflow.md)。

001原文、current-state Spec与ledger本轮不改；拟议新增Spec由对应Plan实施/复审/merge后分阶段沉淀，不把B或EPUB草案写成已实现。
