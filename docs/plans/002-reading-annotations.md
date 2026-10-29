---
plan_id: READER-002
title: "本地阅读体验、摘录与分阶段Notes联动"
status: drafting
feature_name: "本地阅读体验、摘录与分阶段Notes联动"
author: [Codex]
created_at: 2026-10-04T00:00:00Z
updated_at: 2026-10-29
plan_revision: 3
current_step: 0
total_steps: 11
base_branch: main
base_commit: 4d6345cc37882b0216480661eefae4c773617c2d
source_import_commit: 25d28c481aa7bcf375f0d21f04e4af7b6f624d58
depends_on: ["READER-001", "READER-003"]
supersedes_spec_components: ["docs/specs/reader/real-library.md"]
new_spec_components: ["docs/specs/reader/reading-annotations.md", "docs/specs/reader/notes-capture.md"]
touched_goals: ["auto-reader/first-real-release"]
---

# READER-002：本地阅读体验、摘录与分阶段Notes联动

## 0. 变更摘要

r3保留阅读增强/摘录/知识交接方向，改为003最小EPUB先行、002-A本地增强与摘录独立交付、002-B随后接Notes。003不依赖本计划；本计划消费003已交付的内容/资源/定位接口，避免两份Plan各写一套EPUB定位。

阶段A可单独review并按批准阶段交付，Notes不可用不阻塞A；B未完成时整份002保持executing，不把Phase A通过当整Plan完成或归档。001继续归档，不因新增增强需求重开。

## 1. 目标

覆盖原R03/R04（本地A）与R06（Notes交接B）；R05最小EPUB及必需的基础R02/R03子集归003，不反向要求完整002。

A阶段：字体/行距/边距/主题等本地偏好、宽窄布局与搜索/快捷键、书签/高亮/注释/标签/回访、带出处的Markdown导出，均可离线独立使用。字体/布局变化与重启后保持同一原句；重复文本与源版本变化不静默误定位。

B阶段：基于A已持久保存的摘录生成CaptureEnvelope，接Notes真实接收与耐久回执、幂等重试及离线待发送内容恢复。Notes未运行时本地阅读/注释/导出正常，尚未发送的内容不丢失。

不实现全书AI索引、Jade真实写入、同步/多端冲突平台或完整知识系统；不以这类未来系统作为本地能力前置。

## 2. 架构方案

唯一应用开发、检查与顺序复审检出为 `D:/autostack/auto-reader` 独立clone，分支main；一个写入者，不切走他人WIP。AutoOS内 `apps/auto-reader` 仅组合固定pin，app提交/推送后在干净且无人写入的子模块集成精确SHA并保持detached，独立clone留main。语言/UI框架缺项由实际owner另立最小前置并遵守其worktree规约，不在app手写Rust或手修生成物，不创建junction/symlink。

A复用003内容模型/locator与001书库、受管原件和状态；拟新增本地annotations/settings/export模块与reading_page/book_store接缝。稳定annotation_id不随标题/标签/样式改变，注释记录绑定书版本/资源、quote/context和人工comment，不能只记百分比或把无歧义失败默默选第一处。

B仅新增独立capture适配与本地待发送仓储，不复制Notes存储或擅自写Notes数据库；通过实际已交付的接收接口/文件导入协议。Notes接收契约以其规范和回执为准，本Plan不编造尚未存在端点。一个发送意图一个稳定request_id，重试复用；同文字新意图不能被正文hash合并。

## 3. 技术栈

Auto/AutoUI纯.at＋003已验证的内容/locator接口；UI两端沿001的Vue＋VM HTTP、原生VM＋VM HTTP明确profile。A为纯本地能力，不需要Notes进程、broker或全局知识服务。B使用版本化CaptureEnvelope/SourceRef及真实Notes接收协议；文件导出是离线交付能力，不等同于真实接收端已验收。

## 4. 需求分析与背景调查

2026-10-29用户明确要求：优先补齐最小EPUB阅读，002的本地阅读体验与Notes联动分阶段；003不等待完整002；同步001归档、roadmap和AutoOS总表，暂不开始实现。r3继承原方向并按本次授权调整范围归属和依赖，不重新取号，不把本轮起草视为代码执行授权。

现实现基线 `4d6345cc37882b0216480661eefae4c773617c2d`（main）；001为[archive/001-real-library.md](archive/001-real-library.md)，r9、32/32、archived。其最终复审055a5a6绑定268c7d4并重跑原生恢复16/16；合入后main landing check已记录PASS。当前HEAD相对268c7d4的src/tests/pac.at无差异（本轮只读核对，不是重新执行验收）。001源文件、canonical和ledger本轮保持原样。

已有TXT/Markdown受管导入、书库/移除/恢复、内容锚点与位置存储可复用；当前canonical明确EPUB属于003，尚无EPUB/annotations/capture的实现态Spec。旧根设计的内存Demo描述仅为2026-10-04历史观察，不能覆盖r9现实现。

- `src/back/api.at`：SHA256 `969ea9f6dd1da45b69d4777bf660a5ab6d8fb7976caa7dc9bf8fa326cad38078`。
- `src/back/library.at`：SHA256 `dd41fe7dfa978e2baccfe2b99ed7e005f76130c87f91e8d478545a2b024354cd`。
- `src/back/importers.at`：SHA256 `eae048808a071a27a95d470a4754697cba797289da11daf0295433341be579bf`。
- `src/back/hashx.at`：SHA256 `a959a54c3135c19ad728511a72ef989c03c880a01f33d65d16e9e485ff49ae93`。
- `src/back/jsonx.at`：SHA256 `13ec1d84941f57acc0f6a1559e62cabe33cae6bfb5dd49498c09a36953de7f9f`。
- `src/front/book_store.at`：SHA256 `3fbfa3a1e0309a8992665e9b24a1c4434a7c720bb5315216240601186aacf036`。
- `src/front/pages/reading_page.at`：SHA256 `d16ef8c9cea420d61622e9e04411938e9fdbe3a9647be61301b433fc2421b553`。
- `docs/specs/reader/real-library.md`：SHA256 `171aae8bd4734ff2a83bf76f382555bfab449884c057c7bfde094d27f2212350`。
- `pac.at`：SHA256 `36d1e3efa19401807e3f27fc5a11c8fe639d2c21eb190bdd3cba88569f7a5f42`。

[003 r3](003-epub-reflow.md)为本计划本地内容基线；[NOTES-002](D:/autostack/auto-notes/docs/plans/002-quick-card-assets.md)当前仍drafting，其真实接收未交付，因此只作为B阶段的依赖门，不阻塞003或本计划A。

原002 r2的R03/R04/R06需求与AC-01..05不撤销：本地体验/注释/导出移入A，真实接收与离线待发送移入B。旧工作目录/分支改为当前独立clone main；源码事实已由001更新，不能继续以“当前无Spec/内存demo”为执行基线。

## 5. 详细设计

### 阶段与依赖

| 阶段 | 就绪条件 | 可交付边界 | 不等待什么 |
|---|---|---|---|
| A 本地阅读/注释 | 001和003实际交付，固定真实内容与locator接口；T-00先调查 | 本地偏好/搜索/书签高亮注释、定位回访、Markdown导出、两端体验，可单独review/阶段merge | 不等Notes-002、Notes进程、全局知识系统 |
| B Notes交接 | A阶段已交付＋NOTES-002真实接收能力/协议与交付回执可消费 | 真实发送、离线待发、耐久收据、重试幂等及正确来源；完成最终review/merge后整份002才归档 | 不默认等Jade或未来broker |

推荐排程：003→002-A→002-B。只有B等待Notes；如果B暂时blocked，A交付可继续被使用，不撤回本地成果，也不把B标完成。Notes接收面若由其他实际交付合同承接，T-02记录其等价协议与范围证据，不凭“Notes能新建笔记”推定完整CaptureEnvelope已支持。

T-00有界冻结现有内容/locator/选区、Unicode与双端输入可达性、样式配置/注释版本、资源边界与错误；输出拟新增 `docs/plans/evidence/002/local-capability-decision.md`。003交付不等于选择/高亮/主题自动实现；必要平台缺口具名交owner，但不能重写003或扩成全局重构。

### A 本地边界

偏好保存与恢复以内容锚点为准；全文搜索/目录跳转/注释回访都绑定书版本和真实文本。至少3份书fixture、共20处可持久回访注释，覆盖TXT/MD与003支持的EPUB；源变化、多处同句或缺资源时明确需重定位，保留原摘录，不无声跳错。搜索/选区/注释快捷键在输入框/IME场景不抢事件。

Markdown导出必须含书名、原句、版本/来源身份、章节/资源locator和人工注释；未配置Notes也能生成可使用文件。仅预生成envelope或mock receiver不能关闭B。A不需要持有网络发送锁或Notes账户。

### B 发送/接收边界

待发送对象包含完整出处及稳定请求身份，确认接收前持久保留；重启或网络失败仍可重试，不以UI清空代表已发送。接收回执必须指向真实Notes持久对象，重复发送同意图只对应一个对象；新意图即使文本相同也可创建新记录。确认后重启双方再核对接收正文/出处与回执，避免“当前调用成功、下一次打开丢失”。预算/队列满的拒绝语义先固定，不能驱逐未发送内容。

### 规范增量

| delta_id | action | docs/specs target | before/after rule | 理由 | AC |
|---|---|---|---|---|---|
| SD-01 | add | docs/specs/reader/reading-annotations.md | 无本地增强规范 → A阶段偏好/注释/回访/导出和双端边界 | 可离线独立交付，不冒称Notes联动 | AC-01/02/03/05 |
| SD-02 | modify | docs/specs/reader/real-library.md | 已交付基础位置 → 与实际A设置/locator消费兼容的扩展，不破坏旧状态 | 与003单一位置模型复用 | AC-01/02/05 |
| SD-03 | add | docs/specs/reader/notes-capture.md | 未交付跨应用提案 → B真实接收、离线队列和幂等回执合同 | fixture/导出/真接收分账 | AC-03/04/06 |

本轮不改canonical/ledger。阶段A只能在其review/merge后沉淀SD-01/02的实际范围，SD-03保持待实施；B完成后按最终review沉淀SD-03。不把未实现的B写成current-state。

## 6. 测试设计

原始日志/截图/探针输出在本地 `docs/plans/attachments/` 留存，不提交非md证据；Plan只记命令、退出码、实际选择数/结果、版本与输入/制品hash摘要。使用隔离数据目录与明确空闲端口，只关闭本次拥有的进程，不清用户真实书库或他人服务。

| case_id | 阶段 / AC / work owner | 实际输入/入口 | 结果与oracle |
|---|---|---|---|
| A-01 | A / AC-01/05 / T-01/04 | 三份书、混排/窄屏/大字号、修改本地样式后退出重开 | 恢复同原句且pane正面积可见；偏好持久化，搜索/选区/输入框/IME不误触快捷键 |
| A-02 | A / AC-02 / T-03/04 | 20处书签/高亮/注释，重复句与同书改版、中文emoji | 稳定annotation_id与source版本；唯一匹配准确，歧义显示重定位，原摘录/注释不丢 |
| A-03 | A / AC-03/04本地面 / T-05 | Notes不存在/端口不可达，导出Markdown后独立解析 | 完整原句/书名/版本/章节/locator可核对；本地操作与导出不失败或丢内容；不记作真实接收成功 |
| A-04 | A / AC-01/02/05 / T-04 | 不可写/坏本地注释状态、UI操作失败、正常/硬退出重开 | 无虚假saved、不清草稿或覆盖旧注释；恢复条件后下次写/回访可成功；两端真实操作 |
| B-01 | B / AC-06 / T-02/08 | 真Notes接收实例、同request_id重试及同文新request_id | 正文/出处准确落盘，重试同对象，新意图新对象，重启接收端后对象/收据仍可读；mock结果另列 |
| B-02 | B / AC-04/06 / T-08 | Notes停机→记录待发→Reader重启→恢复接收/失败回执/队列边界 | 待发内容和request_id保留，失败可见且不误清空，恢复重试不重复接收；本地A能力仍正常 |

拟新增 `tests/annotations/verify_local.py --profile vue|vm`（T-04/T-05制作）和 `tests/integration/verify_notes_capture.py`（T-08制作）；这些不是当前已有入口。实际Notes接口/fixture/服务启动参数在T-02用交付合同冻结，不编造端点。阶段A验收与B真实集成结果分别记录；复用未变证据须绑定同实现/依赖/配置/输入，不能用旧TXT样例代替新增EPUB注释或真实接收。

## 7. 验收标准

| ID | owner_stage | 阶段/可观察标准 |
|---|---|---|
| AC-01 | work | A：字体/窗口变化与重启后恢复同原句，真实可见，不只相似百分比；偏好可保存 |
| AC-02 | work | A：3份书fixture共至少20处注释可持久回访，稳定身份/版本准确，重复句/源变更不无声跳错；包括从003转交的EPUB高亮恢复 |
| AC-03 | work | A导出＋B来源传递：原句/书名/版本/章节/locator准确；A文件由独立解析核对，B由真实Notes持久对象核对，二者不得混称 |
| AC-04 | work | A本地导出独立＋B离线待发送：Notes未运行时本地功能正常，待发送内容跨退出/重启保留；配置/fixture/真实接收分账，未发送不假称成功 |
| AC-05 | work | A：宽窄布局可读，搜索/选区/注释不误触键盘/IME；Vue和原生VM各有真实操作、错误及恢复证据，不能以API代替 |
| AC-06 | work | B：消费实际Notes交付接收面，同request_id重试只一对象、同文新意图可新建；确认后双方重启读回正文/出处/收据一致，无必需集成门pending |
| AC-07 | review | A阶段只签AC-01/02/05和AC-03/04本地部分的phase review；最终必须再核全AC-01..06/SD与依赖/失败控制。阶段pass不等于整Plan reviewed |
| AC-08 | merge | A scoped门通过后可阶段交付并保留002 executing/B未勾选；B最终门后才整Plan归档、Spec/ledger/精确pin/健康/总表收尾；独立clone留main、子模块detached |

## 8. 执行步骤

- [ ] T-00（owner_stage=work；phase=A；依赖001/003实际交付；AC-01..05）：核实内容/locator/选区、两端能力与数据模型，输出local-capability-decision.md；不等待Notes，仅对真实缺项立具名最小前置。
- [ ] T-01（owner_stage=work；phase=A；依赖T-00；AC-01/05）：实现本地样式/偏好、搜索/目录和布局输入规则，持久保存并保持同内容锚点；复用003基本阅读，不另写EPUB解析器。
- [ ] T-03（owner_stage=work；phase=A；依赖T-01；AC-02）：实现稳定注释/书签/高亮/评论/标签、列表回访与重复句/源版本变化的诚实重定位。
- [ ] T-05（owner_stage=work；phase=A；依赖T-03；AC-03/04本地面）：完成带完整出处的本地Markdown导出；Notes缺席也可用，不把文件导出说成已接收。
- [ ] T-04（owner_stage=work；phase=A；依赖T-03/T-05；AC-01..05本地面）：建立永久本地双端入口并跑A-01..04，准备A的SD-01/02；只提交A实现/摘要，申请phase review，整体不因A结束就execution_done。
- [ ] T-06（owner_stage=review；phase=A；依赖T-04；AC-07阶段面）：固定A提交做phase review，范围仅A本地AC/SD，B必需项明确未验；无pass不阶段merge。
- [ ] T-07（owner_stage=merge；phase=A；依赖T-06；AC-08阶段面）：完成A适用门/规范/推送/组合pin，记录阶段交付；整Plan保持executing、B未勾选。B等Notes不撤回A成果。
- [ ] T-02（owner_stage=work；phase=B；依赖T-07及NOTES-002实际接收交付；AC-03/04/06）：冻结真实协议与回执，做CaptureEnvelope/SourceRef、持久待发和稳定意图ID；不擅自写Notes数据库或假造系统API。
- [ ] T-08（owner_stage=work；phase=B；依赖T-02；AC-03/04/06）：制作真实Notes集成入口，验证B-01/02与A仍可离线使用，准备SD-03、提交实现，全部work完成后execution_done。
- [ ] T-09（owner_stage=review；phase=final；依赖T-08；AC-07最终面）：冻结实现/接收依赖最终复审全AC-01..06及SD，复用合法A证据并重验受B影响项；声明上下文限制。
- [ ] T-10（owner_stage=merge；phase=final；依赖T-09；AC-08最终面）：统一门、B规范/索引/归档、app与AutoOS精确pin/总表收尾；全部必需项真过才归档002。

## 9. 复审记录

r3依据用户授权调整排程与依赖；r2原文保留在 `4d6345cc37882b0216480661eefae4c773617c2d`、blob `f18f2756a1978d6ba1a2f78baca0dc946a150dbf`。原AC-01/02/05归A，AC-03分本地导出与B真实来源接收，AC-04分本地可用与B持久待发，接收幂等要求明确为AC-06；原需求全部保留分阶段，不以A过门关闭B。原T-00..04编号保留并重新标注阶段/细化，新增T-05..10承担导出及阶段/最终交付，尚无实现成果被重置。

stage: new | plan_id: READER-002 | plan_revision: 3 | outcome: blocked（合同分期就绪；首任务等待003实际交付，A不等Notes） | next: 先执行003；其实际交付后work/T-00，B另等Notes真实接收。11项任务全未勾选。

## 10. 待澄清事项

优先003、本地A与Notes-B分阶段已获用户确认，无产品优先级问题待重复确认。T-00解决A的真实选区/模型/预算，T-02根据已交付Notes合同冻结传输/回执与队列资源边界；接收依赖未交付时B保持等待，不能让它拖住003或A，也不能用mock降级整体002完成标准。

本轮文档预检：结构/任务唯一性、AC归属、阶段依赖无环、源码hash与链接检查通过；001/Spec/ledger及已有截图原样保留；未运行应用功能测试。
