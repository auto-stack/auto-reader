# auto-reader 产品规划与执行入口

本轮文档是2026-10-04的设计基线；它们不表示功能已实现。

- [需求、模块设计与UI/UX](design/01-product-design.md)
- [第一版roadmap](roadmap-v0.6.md)
- [业界调研与来源](research/20261004-benchmarks.md)
- [设计索引](design/00-intro.md)

## 首批计划

1. [READER-001：真实导入、书库存储与位置恢复](plans/001-real-library.md)
2. [READER-002：阅读体验、摘录与知识交接](plans/002-reading-annotations.md)
3. [READER-003：重排版 EPUB 导入与阅读](plans/003-epub-reflow.md)

## 给执行agent

先读仓根README、SOURCE-IMPORT.json、对应计划和产品设计，再核对当前git状态及源码。所有计划暂为drafting；选定计划后按现有auto-plan规则确认并翻为executing，按任务执行，留证据，经独立复审才合入v0.6-dev。不要执行全部roadmap，不要以写过文档为验收。

本轮在各独立应用仓内从001–003编号，plan_id带应用前缀；核对本仓活动/归档计划为空后独占创建，不占用AutoLang/AutoOS的.next-id，也不与主力机739/740共用编号。新建后续计划按本仓取号机制检查活动及归档目录；本批不重新分配已存在ID。一个计划一个worktree，分支示例codex/auto-reader-20261004-01；组路径D:/autostack/.wt/auto-reader-20261004-01/auto-reader，禁止junction/symlink。先核实仓路径，使用git worktree add明确指定v0.6-dev起点。

跨仓框架依赖按AUTO_LANG_ROOT → 组内兄弟auto-lang → D:/autostack/auto-lang解析；不得用文件系统链接补依赖。Notes富文本需固定AutoDown子模块，其他应用按各自实际依赖准备；代码修改不落主检出。持久化/截图等验证用临时独立数据目录，不接触用户真实知识库。

按计划审查验收、遗漏/延后、格式、告警和调试输出，记录债务及spec-impact。实现完归档到docs/plans/archive/，保持原ID。只在v0.6-dev合入；恢复v0.5后按source-sync做来源差异导入。不得把本轮产品实验合进master或直接覆盖examples/ui教学demo。

应用代码合入之后才考虑推进AutoOS submodule指针：子仓先提交并推送，再由OS计划登记固定commit并验证宿主。当前文档提交不需要变更OS指针。worktree移除前必须有wt-guard clean证据；脚本缺失时保留worktree而不递归清理。

运行基线：在对应worktree根执行`auto run`（Vue）及`auto run -r vm`；端口17824 / 17825。安装匹配基线的auto CLI，先读pac.at；不将固定工具路径写死到产品。首批需要的测试fixture/脚本写在tests；既有脚本须核实针对本产品且端口一致后再复用。

API/平台缺失先做T0探针并登记跨仓能力计划；保持src/back纯.at，不修改生成Rust，不用mock替代真实验收。当前这些是实施前文档，因此没有声称已经跑过应用功能或性能测试。

### 第一计划 worktree 示例

从本仓根运行，先确认目标路径/分支尚不存在：

```powershell
git worktree add D:/autostack/.wt/auto-reader-20261004-01/auto-reader -b codex/auto-reader-20261004-01 v0.6-dev
```

这是执行准备命令，本轮文档任务没有执行它。需要的子模块在新worktree中按仓根README初始化；禁止用链接接入其他仓。
