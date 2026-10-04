# Auto Reader：需求、架构与 UI/UX

状态：proposed；日期：2026-10-04。目标为安静可靠的个人阅读器，连接 Notes/Jade，辅助阅读与回访原文。

## 1. 现状与目标

`src/back/db.at` 明确是内存种子库；`create_book` 按标题/作者生成3个占位章节。现有 bookshelf/reading/book_detail/settings 和 book_store 提供界面原型；Book 的整数progress不足以在更换字体后准确恢复阅读位置。第一步是导入真正文件、保存真实书库，而不是继续添加假书。

用户路径：导入一本书 → 读到指定段落 → 调字体 → 关闭重启回到原段落 → 高亮加一句笔记 → 发到Notes/Jade → 点击来源返回书内位置。AI解释作为可选动作，不能替代读者阅读、标注、决定理解。

## 2. 需求矩阵

| ID | 范围 | 验收意义 |
|---|---|---|
| R01 | P0/M1 | 真实TXT/Markdown导入、编码错误提示、去重提示、持久化书库与原文件 |
| R02 | P0/M1 | 目录/搜索/进度恢复；定位不只存百分比；删除书目不默删原文件 |
| R03 | P0/M2 | 字体/字号/行距/边距/主题/连续滚动，键盘、窄屏与大字号；设置可保存 |
| R04 | P0/M2 | 高亮、书签、摘录注释、原文定位与Markdown导出 |
| R05 | P0/M3 | 无DRM重排版EPUB导入，package/spine/nav、图片与基本样式，离线阅读 |
| R06 | P1/M2–3 | Notes/Jade接收摘要/原文/书源，不丢上下文；接收端不在线可暂存 |
| R07 | P1/原型 | 选中段落解释/翻译/有引用的章节问答；可取消，标识AI生成 |
| R08 | P2/v0.7+ | PDF固定版式/扫描OCR、TTS听书、多端同步、OPDS/在线书源、完整出版物样式 |

先支持重排版内容；EPUB脚本不执行，固定版式/复杂CSS/嵌入字体等限制写能力表。小说与专业书两类fixture均要覆盖；复杂表格/公式渲染不是一句“能打开”就算通过。

## 3. 数据与位置

BookRecord：`book_id, source_hash, original_asset, format, title, author, toc[], import_version, created_at`。BookVersion 用 original hash 区分同书不同版；同hash导入提示复用，但允许用户保留独立阅读档案。ReadingState：`book_id, version, locator, settings, updated_at`。Annotation：`annotation_id, book_ref, locator, quote, comment, tags, revision`。

Locator v1：`resource_id/chapter_id, text_offset, exact_quote, prefix, suffix, source_hash, position_hint?`。格式adapter可以补EPUB CFI；不能只保存像素scrollTop，也不能把自定义locator宣传为标准CFI。恢复先验证资源/offset与quote，再精确/上下文搜索；多处匹配或源版本变化显示需重定位，保留原摘录不随便跳到错误句子。

原文件受管理复制，书架metadata、阅读状态与注释分别存储；删除书目进入可恢复状态，处理原文件另作显式动作。失败导入不创建可阅读假书；大文件解析可取消，不冻结UI。版本升级前迁移备份，注释不依赖展示标题作主键。

## 4. 模块设计

| 新模块建议 | 职责与边界 |
|---|---|
| src/back/library.at | 存储、导入事务、元数据、书版本与去重 |
| src/back/importers/ | TXT/Markdown/EPUB格式adapter；输出统一资源+目录，不改书籍原件 |
| src/back/locations.at | locator校验/恢复/版本变化；可独立fixture测试 |
| src/back/annotations.at | 稳定注释ID、引用、导出与幂等交接 |
| src/front/reader_view.at | 原文、目录、样式和选择工具条；接入既有reading页面 |
| src/integrations/ | Notes/Jade交接、可选AI；与渲染器解耦 |

EPUB ZIP/XML解析优先复用成熟依赖或现有桥；不自研全格式解析器。T0能力探针确定Vue与VM共享解析输出，不允许只靠浏览器iframe声明VM可用。包内路径严格归一，不能写出临时目录；资源失效有文字占位。首版只渲染允许的内容，不执行出版物的活动脚本。

## 5. UI/UX

```text
书架：继续阅读  |  搜索  |  导入
[书封/文字] 标题 作者 · 最近位置     [未读/在读/完成]

阅读：目录  书名                            搜索 设置
      安静正文，默认不展示AI侧栏
      [选中文字] → 高亮 / 注释 / 复制 / 记录到Notes / 解释
      章节与位置                            阅读进度
```

宽屏可选目录/注释侧栏，中间正文保持可读行宽；窄屏侧栏收起为抽屉，选择工具条不遮挡整段。初版以连续滚动为稳定基线，分页作为增强。字号变化保持同文字锚点；进度是估计展示，不作为恢复主键。搜索显示上下文并可回到原位置；查无结果不干扰当前位置。阅读快捷键在输入框/IME中停用。

没有书时提示导入真实文件，demo书只在显式demo入口。解析中、失败、资源缺失、找不到注释位置、接收端不可用都有可重试操作。设置保持读者主动选择，不用AI悄悄改变排版。附加图像可放大；正文/目录读屏顺序正确。

## 6. 质量与发布

至少3本TXT/Markdown及3本EPUB公开/自制测试书，含中文、图片、脚注链接、长章节、重复句、损坏资源。已保存阅读状态和注释重启恢复；换字号回到同文本；导出后出处可解析。目标：1000书metadata查询p95≤150ms，章节切换p95≤200ms（不含首次解析）；实际数据量/平台单列。

AI问答先只读取用户选择的片段或本章，答案展示引用；无法找到原文依据时标明。全书索引/跨库问答与AutoOS知识系统留后续。v0.6知识入口仅用稳定引用和可导出内容，不能绑死尚未交付的系统服务。


## 跨应用契约 v1（设计提案）

这些字段是本轮四个应用共同采用的草案，尚未成为 AutoOS 已实现的系统 API。首版用版本化 JSON 和应用内适配器实现；不得等待 HIR、Atom/Batom v2、AutoC 或完整知识系统才能运行。

| 对象 | 必需字段 | 规则 |
|---|---|---|
| EntityRef | namespace、entity_id、revision、kind | 应用生成稳定字符串 ID；改标题、路径或展示名不改 ID；跨仓引用带 namespace |
| AssetRef | asset_id、sha256、mime、size、storage_ref、original_name | 文件拷入受管理目录后才确认接收；storage_ref 是逻辑定位符，不是另一机器的绝对路径 |
| SourceRef | producer、original_uri、captured_at、locator、source_revision | 缺失字段显式 null；网页 URL、书内位置、截图区域分类型表示；保留原文 |
| CaptureEnvelope | schema_version=1、request_id、producer、text、asset_refs、source_refs、created_at | 一个请求的重试复用 request_id；同内容的新意图允许新请求；不以正文 hash 合并不同笔记 |
| CaptureReceipt | request_id、entity_ref、durable_at、status | 持久化正文及必需附件后才返回 committed；失败可重试，重复请求返回原收据 |

`request_id` 的幂等记录与实体创建在同一事务边界内提交。接收者不能只相信来自外部的 hash 或 MIME，须校验实际文件。建议附件交换采用显式授权的暂存目录加 manifest；只接受目录内的普通文件，不追随链接，不接受任意本机路径。

未决定的系统 transport 由 adapter 隔离：首个可验收版本支持导入/导出 envelope 文件或当前运行时已有的本地调用能力；本轮不擅自登记新的全局 URI scheme。未来 Launcher、AutoScape、AutoLens、copy-paste bin 使用相同语义，并以能力协商声明可用格式。

知识对象可以被多个应用访问，存储所有权不等于 Jade 的 UI 所有权。尚无共享知识服务时，Notes 持久化到可导出的本地 Inbox；提供外部引用与显式迁移收据。该阶段不声称已实现 Jade 双向共享编辑。共享服务就绪后，同一对象通过 revision 条件写入，冲突返回两版供选择，不用静默覆盖解决。


## 系统通信与 DevTools 的追加方向（2026-10-04）

用户确认应用通信/AutoAI和系统级DevTools是v0.6重点。本文的envelope、业务对象和provider是领域契约；注册/发现、会话、授权、错误、trace、stream与task复用公共系统层，应用不各自实现一套底层协议。

公共方案见[AutoOS通信RFC](https://github.com/auto-stack/auto-os/blob/v0.6-dev/docs/design/strategy/auto-app-communication-v0.6.md)与[系统DevTools RFC](https://github.com/auto-stack/auto-os/blob/v0.6-dev/docs/design/strategy/system-devtools-v0.6.md)。两份RFC尚未冻结；当前app计划仍可先完成独立本地数据与fixture闭环，之后把现有adapter接入公共服务，不以尚未实现的broker作为开始保存真实数据的前置。

应用提供业务Service及能力描述，UI/backend adapter提供观察树和允许动作；系统组件提供Inspector、Agent SDK与diff。复用现有AutoUI能力并显式声明Vue/VM/Rust的差异，不要求本app自行嵌入另一套DevTools面板。AI优先调业务能力，体验验证才走UI动作。

## 工程边界与实施约束

当前基线是 2026-10-04 的独立仓库导入版本；主力机器的 v0.5 尚有未公开工作。新增产品模块优先放新路径，用 adapter 接入既有页面；保留 SOURCE-IMPORT.json、source-sync 分支及教学来源。恢复 v0.5 后从 source-sync 基线做三方差异导入，不直接覆盖产品目录。

本次只是研究与设计，文档中“支持”“应当”均为目标；实现状态以计划验收证据为准。应用后端保持纯 Auto `.at`；不编辑 a2r 生成的 Rust。若现有运行时缺少必要平台能力，先输出最小能力探针和单独的跨仓提案，不把大规模框架改动塞进应用计划。

平台基线：Windows/Linux 桌面及 Web 先完成可用闭环；Harmony 是 v0.6 demo 与适配探针范围。窄屏设计纳入本轮，不能据此宣称已交付手机原生版。Android、iOS/macOS 及完整移动平台产品支持没有在本轮被追加为 v0.6 必达项。

AI 派生内容须标记来源、模型/处理器版本和生成时间；原文、原资产、人工更正均可追溯。未配置 AI 或断网时，核心本地流程仍能完成。任务可取消，可见错误，可重新执行。个人内容传给远程服务由用户选择；默认不自动上传整库。


## 配套文档

[调研依据](../research/20261004-benchmarks.md) · [首版路线](../roadmap-v0.6.md) · [执行入口](../README.md)
