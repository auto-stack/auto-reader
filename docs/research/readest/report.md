# Readest 详细调研综合报告（READER-006 T-05 / report）

状态：drafted · 2026-11-01。研究基线：**源码 = tag v0.12.16（commit 3cc39ad7）**，**实际 UI = 官方 0.12.16 Windows x64 portable（SHA256 683a620d…）**——两者同 tag 对应，版本映射关系成立（不可重复构建性如实登记，见 [baseline](baseline.md) §6）。main 分支领先 183 提交，其能力一律另列候选不混入分母。

证据导航：**[capability-matrix](capability-matrix.md)**（C01~C07 逐能力对照，稳定 ID RDT-Cxx-NNN）· **[code-map](code-map.md)**（引擎/链路/服务 path:line）· **[ui-study](ui-study.md)**（真机 U01~U07 实测，截图与运行记录索引）· **[decisions](decisions.md)**（三路线/迁移/服务决策与首批计划建议）· 原始运行记录 `D:/autostack/plan-artifacts/plan-006/`（复审可复演）。

## 1. 核心结论

1. **Readest 的产品广度与工程形态已被完整盘点**：发布分母 257 项能力（matrix 计数节：全量 259 行 − 主分支候选 C04-010 − code-only C05-035），其中约 25 项为 Plus/Pro/外部服务闸；真机核心日用链路（导入→阅读→精确选区标注→重复句消歧搜索→关闭重开恢复→导出深链）**全链实测通过**。
2. **AutoReader 已有面不是空地**：书库导入事务诚实性（sha256 去重+逐字核对）、注释锚核验（quote 逐字子串+occurrence 消歧）、可恢复移除（Readest 无恢复入口）、30MiB 长文门、双端同源验收驱动——这些域 AutoReader 架构**持平或占优**（matrix 逐行对照）。
3. **最大差距在阅读表面**：Readest 阅读面 = foliate-js fork（上游 + 254 commits）+ pdf.js + WebView；AutoReader = 章→文本行重排（Locator v1 段锚，非 CFI）。C02 深排版（出版物 CSS/竖排/公式/分页对齐）、C04 多格式（PDF/漫画/Kindle 系）按 matrix 逐行大部分"缺失"。差距的本质是**一个成熟文档引擎 vs 自研渲染**，不是功能清单长度。
4. **两条 Windows 0.12.16 实证缺陷**（真机发现，对 Readest 是 bug，对本研究是机制透镜）：①对话框导入的受管副本缺失且打开静默失败；②软删记录不去重（tombstone 跳过路径索引）。另：页码计数与 CFI 位置口径不一致；删除确认一次未生效待复验。
5. **服务面分层清晰但成功面缺证**：本地免费面（系统 TTS、本地词典、OPDS 客户端）与 Plus/Pro 闸面（Readest Voice、自定义翻译、AI、第三方云同步）分开；除本地 TTS 实测外，其余账号面全部具名缺证（ui-study §6），不以文档宣称充当已验证。

## 2. 假设核对（起草时 → 调研后）

| 起草时假设（总设计 v1 / 计划 §4） | 调研结论 | 状态 |
|---|---|---|
| Readest 能力可用官方文档完整盘点 | 文档站滞后于代码（DOCX/RTF 已文档化但代码在 main）；**release-notes.json + 设置面板枚举 + 源码**才是可靠盘点源 | 部分推翻，已按多源交叉 |
| "覆盖绝大多数"可以比例计 | 分母可立（257 发布项 = 259 行全量 − 2 行非发布）但含服务闸项；核心任务须单列验收；比例目标**后置**到首批计划落地 | 采纳为计数规则 |
| foliate-js 是"成熟上游库" | 实为 **254 commit 深度 fork**（固定版式 261→2148 行、分页器重写、pdf.js 改造）——复用"上游 foliate-js"≠获得 Readest 阅读面 | 重大修正 |
| Tauri fork 是平台桥大变量 | fork 仅 **5 commits**；CEF 走上游 feat/cef；平台差异主要在 Readest 自有插件/服务层 | 修正（风险降级） |
| 阅读器标注锚定可用 CFI 直接替换 Locator v1 | 两套锚都已解决重复句消歧（Readest=CFI 偏移，AutoReader=occurrence）；迁移应是**字段扩展+逐字锚保留**，不是替换 | 采纳进 decisions §2 |
| 同步是"远程服务"单一问题 | 实为 Supabase auth + HLC CRDT 副本引擎 + 8 种第三方后端适配——复杂度独立立项级 | 采纳 |
| AutoUI Vue/VM 双轨可直接承载 web 引擎 | **未证**；WebView 表面五接缝（焦点/IME/选区/滚动/无障碍）无既有能力记载 | 待探针（decisions P2） |

## 3. 覆盖计数与规则（细则见 matrix 计数节）

- 分母 = v0.12.16 已发布能力 **257 项**（全量 259 行：C01 55 / C02 60 / C03 28 / C04 15 / C05 39 / C06 23 / C07 39；其中 C04-010 主分支候选与 C05-035 code-only 两行不计入）；主分支候选另列不混计；C08（AutoOS 知识流）单列。
- 服务闸项显式标注（不因"无法体验"判支持或判无需）。
- **本轮不宣称任何覆盖百分比**：目标阈值待首批计划（P1~P6）落地后按实测口径提出（decisions §6.2）。
- 核心日用任务单独报告：**真机已验证通过**（ui-study §3），与总量计数分开陈述。

## 4. 重大差距清单（按 matrix 汇总，非穷举）

1. 阅读表面引擎化（C02 主体 + C04 渲染）：探针 P2 决定路线。
2. 定位模型：CFI 级锚 + 迁移（P1）。
3. 行内子串样式（N-002-A-1 框架缺口）——高亮从段级到行内的前置。
4. 书库日用：书封/分组/筛选/跨书搜索聚合（P3）。
5. TTS 本地面（P5，宿主 speech 能力待实查）。
6. 多格式：PDF/漫画/Kindle 系（P6，探针后）。
7. 服务闸面（TTS 音色/翻译/AI/同步）：按"本地优先"逐个评估，不预设。

## 5. 对总设计与路线的二次修订（T-06 已执行）

总设计与路线已按本报告二次修订（修订标记 = Readest coverage v2）：引擎决策从"开放比较"更新为"B 主干 + A 有界探针 + C 长尾过渡"的三路线裁定；覆盖规则引用本报告计数节；后续工作流替换为 P1~P6 首批计划建议；差异与假设核对表以本报告 §2 为准。详见 [01-product-design](../../design/01-product-design.md) 与 [roadmap-v0.6](../../roadmap-v0.6.md)。

## 6. 复演与复审入口

- 固定源：`D:/autostack/readest`（detached at v0.12.16，子模块按 tag 检出——baseline §2 命令可重放）。
- 固定 UI：`D:/autostack/plan-artifacts/plan-006/ui/readest-portable/`（exe SHA256 在 baseline §4；portable 隔离 + CDP 端口 9223 的启动命令在 baseline §4 表）。
- UI 复演：ui-study.md §0 方法 + runlog-u01.md 步骤（含复现选区慢速拖拽、搜索 3 结果、导出深链的完整参数）。
- 源码核对：全部 path:line 在 tag 检出下有效；GitHub 永久链接形式见 code-map §头部。

## 7. 遗留与移交

- 待复验：删除确认点击、PDF 标注弹层、顶栏书签按钮（ui-study 各节已标）。
- 缺证具名：全部账号/服务成功面（matrix 条件列 + ui-study §6）。
- 后续入口：decisions.md §5 的 P1~P6 为首批建议——经用户认可后另立计划取号，执行与复审按 auto-plan 流程。
