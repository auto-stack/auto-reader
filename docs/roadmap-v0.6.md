# auto-reader：首版路线图

更新：2026-10-29。001已交付归档；002/003本轮仅修订为r3，尚未实施。产品版本与平台支持以实际交付证据为准，pac.at导入版本号不等于所有规划完成。

## 当前顺序

| 顺序 | 成果 | 计划与启动条件 | 当前状态 |
|---|---|---|---|
| 1 | 真实TXT/Markdown书库、内容锚点与重启恢复 | [READER-001](plans/archive/001-real-library.md) | archived/r9，32/32；最终复审055a5a6、实现268c7d4、合入后landing PASS。这里同步既有证据，本轮未重跑验收 |
| 2（当前优先） | 最小EPUB3重排版导入、目录/图片/内部链接、基本字号与离线位置恢复 | [READER-003 r3](plans/003-epub-reflow.md)；依赖已交付001＋T-00确认的必要ZIP/XML/二进制/渲染/真实输入能力 | drafting，0/7；不等完整002或Notes；先做有界能力与资源预算调查 |
| 3 | 本地阅读体验、搜索、书签/高亮/注释、准确回访与Markdown导出 | [READER-002 r3 阶段A](plans/002-reading-annotations.md)；消费001/003已交付内容与locator接口 | drafting，本地阶段可独立验收/阶段交付，不等Notes运行或接收服务 |
| 4（TODO） | （AutoOS TODO）app 间互动：Reader→Notes 摘录交接 | 前置未建：①OS 级 APP 间通讯框架协议 ②OS 级应用功能包共享机制（2026-10-31 用户裁决整体 TODO）。未来形态：笔记记录与分享做成 OS 级能力服务，AutoNotes 主入口，各 app 按积木集成——届时另立计划消费 | READER-002 以阶段A收尾（r4），本行整体 TODO |

依赖图为 `001 → 003 → 002-A → 002-B`，Notes接收能力只进入B。003自己交付最小内容adapter、基本阅读与EPUB位置；002消费同一模型，不反向要求003先等注释或Notes。003旧合同的高亮恢复要求移入002-A，仍需验收，不当成已经实现或被删除。

002-A可phase review/merge并让本地成果投入使用；B未完成时002保持executing，不把A通过称整份002完成或归档。后续双端结论分别记录，不用Vue成功替代原生VM。

## 003的真实前置

001/r9提供书库、受管原件、状态及恢复基础。EPUB专用ZIP/XML/二进制身份、受管资源、两端基本文本/图片/定位、真实UI导入/导航与资源预算，由003 T-00逐项验证；缺少公共能力时在实际框架owner立最小前置，消费其交付回执后再实施依赖任务。不以“当前能读TXT”推定“当前能读EPUB”。

Notes/Jade、auto-web建仓、全局知识服务、整轮框架结构收口与Linux发行版基础均不作为003的全局启动门。实际共享文件/接口按owner协调；真正缺少的ZIP/渲染/输入能力不能用mock绕过。

## 001归档状态及边界

001实际归档位置是 `docs/plans/archive/001-real-library.md`，r9、32/32。其收据记录：10MiB成功导入与全章oracle、混排内容锚点真实可见、原生恢复驱动16/16、真实Vue回归及main landing PASS；早期r7/r8 needs_fix或未验收说明保留在历史，不能作为当前001状态。

001不是EPUB完成证据，也不宣称所有运行栈/平台均可用。当前已验UI组合为 `auto run --server=vm` 和 `auto run -r vm --server=vm`；Rust后端映射、原生导入请求体/部分导航驱动等限制见[现实现规范](specs/reader/real-library.md)与001记录。003若实际需要这些入口，必须在其能力门中关闭，不能用001的API预导入/恢复夹具冒充003的真实UI导入。

## 执行与交付

- 开发/计划/顺序复审使用 `D:/autostack/auto-reader` 独立clone的main，一app一写入者；`auto-os/apps/auto-reader`只固定已推送交付版本，平时detached。先推app，再更新AutoOS精确pin并验证。旧v0.6-dev及Demo编号目录仅为历史。
- 001保持归档，不为新增增强需求重开；本轮只改002/003、导航/路线和总表，不修改业务源码、canonical Spec或ledger，不取新号、不启动实现、构建或GUI。
- 规模和资源预算在003 T-00/002 T-00明确单位、边界及超限结果；未提出硬上限不等于无限规模承诺，也不以过去的周数估算代替能力验证。
- 最终测试与复审按各Plan指定阶段/触面执行；原始证据本地保留、Plan记摘要，不改语言crates时不跑其Cargo全量或docs_gen。
- Linux另等auto-os-distro完成Nix＋COSMIC基础；本次Windows已验组合与EPUB本地实现不等待该基础，也不冒称Linux已验证。

## 后续增强

PDF/扫描OCR、复杂出版物排版、听书、在线书源和多端同步继续留待后续；AI解释不抢占真实阅读与数据可靠性。002的本地增强/真实Notes交接按上述阶段保留，不因优先EPUB而撤销需求。

[产品设计（目标态）](design/01-product-design.md) · [执行入口](README.md) · [AutoOS总跟踪表](https://github.com/auto-stack/auto-os/blob/main/docs/plans/b-apps-basic-capabilities.md)
