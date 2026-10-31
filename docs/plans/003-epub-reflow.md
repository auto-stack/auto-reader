---
plan_id: READER-003
title: "最小重排版EPUB导入与阅读"
status: drafting
feature_name: "最小重排版EPUB导入与阅读"
author: [Codex]
created_at: 2026-10-04T00:00:00Z
updated_at: 2026-10-29
plan_revision: 3
current_step: 2
total_steps: 7
base_branch: main
base_commit: 4d6345cc37882b0216480661eefae4c773617c2d
source_import_commit: 25d28c481aa7bcf375f0d21f04e4af7b6f624d58
depends_on: ["READER-001"]
supersedes_spec_components: ["docs/specs/reader/real-library.md"]
new_spec_components: ["docs/specs/reader/epub-reflow.md"]
touched_goals: ["auto-reader/first-real-release"]
---

# READER-003：最小重排版EPUB导入与阅读

## 0. 变更摘要

优先接续001，实现真实EPUB导入、目录/顺序、基本正文/图片、离线阅读与位置恢复。r3移除“完整002”为硬前置；最小内容adapter、基本排版和EPUB位置由本计划自己交付。002的高亮/摘录、完整阅读增强与Notes交接不进入003完成条件，后续沿[002 r3](002-reading-annotations.md)接续；001不重开，本轮不实现。

## 1. 目标

覆盖R05及最小阅读必需的R02/R03子集；完整阅读增强/摘录与R06交接仍归002-A/B。

让用户从真实文件导入一本无DRM重排版EPUB，通过目录/前后章阅读文本与图片、改变基本字号、退出重开仍回到同一内容位置；异常书和不支持的形态必须明确拒绝/提示。

首版profile：EPUB 3无DRM重排版，按EPUB 3.3的OCF/package/spine/navigation与XHTML基本结构确定应用子集，不宣称完整阅读系统一致性或覆盖所有EPUB。支持段落、标题、列表、基本行内强调、本地图片及内部链接/脚注跳转回返，连续滚动；复杂CSS、固定版式、脚本、嵌入字体/多媒体等不执行，限制写能力表。EPUB2/NCX-only不作为本轮最低承诺，探针如发现可无损支持则先说明/修订范围，不悄悄扩成全格式。

非目标：注释/高亮管理、Notes/Jade联动、PDF/OCR、TTS、网络书库/同步、完整CSS渲染器、Rust后端补齐、Linux适配。高亮恢复原要求的归属迁到002-A并保留，不是已实现或被删除。

## 2. 架构方案

唯一应用开发、检查与顺序复审检出为 `D:/autostack/auto-reader` 独立clone，分支main；一个写入者，不切走他人WIP。AutoOS内 `apps/auto-reader` 仅组合固定pin，app提交/推送后在干净且无人写入的子模块集成精确SHA并保持detached，独立clone留main。语言/UI框架缺项由实际owner另立最小前置并遵守其worktree规约，不在app手写Rust或手修生成物，不创建junction/symlink。

保留001的library/API入口、稳定book_id、受管原件和旧TXT/MD状态。拟新增 `src/back/epub.at`、资源/内容adapter与必要API，具体拆文件由T-00冻结；现有 `importers.at` 是文本切章，不能把ZIP先read_text再当TXT导入。将EPUB3的container→package→manifest/spine/nav→XHTML/资源映射成两端共用的内容模型，再由现有reading_page渲染；Vue可用DOM不代表VM具备同能力。

EPUB持久身份以原始二进制内容证明/摘要＋格式版本区分，T-00选定实际SDK可支持的二进制摘要/字节核对方案；不得把文本ph1或标题当作二进制完整性证明，也不改变旧ph1记录的含义。Locator补充资源href/稳定资源身份、段落/文本锚点与source_hash，保留001旧格式读取；不能只用滚动像素/百分比，也不把自定义locator宣称为标准EPUB CFI。002后续消费同一模型，不复制第二套解析器/位置协议。

## 3. 技术栈

纯.at应用逻辑＋实际可消费的ZIP/XML/二进制文件/图像SDK或成熟依赖adapter；目前这些能力仅为候选，不能先写不存在API。T-00查版本、许可、真实双端/后端消费链，必要时在框架owner立具名最小前置。

本计划UI双端采用001已声明的 `auto run --server=vm` 与 `auto run -r vm --server=vm`，端口17824/17825；不将默认a2r Rust后端缺口追加为EPUB全局门，也不误用无HTTP的merged形态。未来其他运行栈另按其计划验收。

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

标准输入：[W3C EPUB 3.3](https://www.w3.org/TR/epub-33/)（2026-10-29查阅）；它定义出版物/容器等结构，本计划只承诺上列经实测子集。原003 r2及其AC/T记录保留在本基线Git中，blob见§9。

001当前边界仍在：原生导入对话框的Http.post缺参（N-r8-1）、部分原生导航驱动（N-r8-3）与Rust映射差距。001归档不等于这些路径已修。003的真实EPUB导入/阅读动作若碰到它们，必须定界并关闭实际必需的入口，不能沿用001“API预导入＋只验恢复”证据冒称完整EPUB用户流程。

## 5. 详细设计

### 真正前置与首任务

| gate | 归属/状态 | 解除条件与对003的影响 |
|---|---|---|
| DEP-01 | READER-001，已归档r9 | 执行前核对交付SHA/公开library与位置接口；不重开001、不等002 |
| CAP-01 | 003 T-00，二进制/ZIP/XML | 真实.at可调用链、许可/版本、资源路径和受限解码探针；缺项转实际SDK owner最小Plan，取得交付回执才做依赖实现 |
| CAP-02 | 003 T-00/T-02，内容/图片/定位 | 原生与Vue均能显示拟定基本块和本地图像、定位具体文本；不拿浏览器HTML成功替代原生证据 |
| CAP-03 | 003 T-00/T-03，资源/提交 | 冻结文件大小/累计解压字节/单项大小/项数/嵌套与图像像素预算、拒绝语义；验证导入提交失败不污染旧库及后续重试 |
| CAP-04 | 003 T-00/T-04，真实用户入口 | 核对N-r8-1/N-r8-3在当前工具链下的实际影响，给出可重复真实输入/导航路径；必需缺口按owner关闭，不以fixture注入书或后台成功替代UI导入 |

首个就绪任务T-00只做有界能力与依赖决策，输出拟新增 `docs/plans/evidence/003/capability-decision.md`：实际API/根路径、依赖版本/许可证、CPU/内存/解压预算的单位与边界、内容和locator schema、UI验证路线、缺项owner/计划及关闭条件。表中CAP不是已存在的框架实现承诺；没有缺项不强行另建前置。002、Notes、Jade、auto-web、整轮结构收口及发行版基础都不是该调查的启动门。

### 导入、资源和最小阅读

用户原文件只读保留。导入在本书专属暂存/受管空间解析与核对，全部必需资源和索引待发布状态通过后才承认成功；失败不留可读假书、不动已有书目/资产/状态，临时残留可诊断并可重试。无法原子rename/fsync时按实际验证的恢复协议说明，不承诺掉电级原子性。

容器路径与href统一解析/规范化，拒绝绝对路径、盘符、越界/编码后越界、链接/reparse条目及目标碰撞；XML不加载DTD/外部实体，正文不执行脚本/事件处理，不自动获取远程资源。预算必须在分配/展开前及实际流式输出中计数，不能只相信ZIP头。缺资源/坏XML/不支持书型返回可理解错误，不能回落Demo或空正文后报成功。

先完成book格式分派与书库准入的向后兼容，再实现最小块模型/目录/阅读顺序/内部链接/图片与基本字号。进度保存绑定具体书版本和资源/原句；换字号、图像导致混排和重启后目标须真实落入阅读pane，保留001正面积可见oracle；重复文本/源版本变化不得静默跳错。高亮/注释只保留可扩展定位接缝，业务实现属于002-A。

### 规范增量

| delta_id | action | docs/specs target | before/after rule | 理由 | AC |
|---|---|---|---|---|---|
| SD-01 | add | docs/specs/reader/epub-reflow.md | 无EPUB实现态 → 实际支持的EPUB3最小profile、解析/资源/拒绝与双端范围 | 不能把能解ZIP当可阅读 | AC-01/03/04/05 |
| SD-02 | modify | docs/specs/reader/real-library.md | txt/md＋既有locator → 兼容的epub分派、二进制原件/书版本与资源定位 | 保持旧库可用且不串书/错位 | AC-02/03/05 |

本轮不改canonical/ledger；T-04准备实际增量，复审与merge后再落地。

## 6. 测试设计

原始日志/截图/探针输出在本地 `docs/plans/attachments/` 留存，不提交非md证据；Plan只记命令、退出码、实际选择数/结果、版本与输入/制品hash摘要。使用隔离数据目录与明确空闲端口，只关闭本次拥有的进程，不清用户真实书库或他人服务。

| case_id | AC / work owner | 输入与实际入口 | 观察oracle与覆盖边界 |
|---|---|---|---|
| E-01 | AC-01/04，T-00/01/04 | 3份自制/可分发EPUB3：至少中文一本、混合图像/脚注一本；真实导入UI→书库→目录→章节 | 独立出版物清单核对spine顺序/标题/正文/图片字节，离线重开仍可读；记录fixture来源/许可/hash |
| E-02 | AC-02，T-02/04 | 同文重复段、同标题不同书版本、长短段与图片混排；改字号/重启 | 恢复同资源/原句并与pane有正面积交集，不能仅断言百分比/索引；歧义诚实提示，旧TXT/MD恢复仍过 |
| E-03 | AC-03，T-03/04 | zip-slip/绝对盘符/编码路径/重复规范路径/链接项、XXE及脚本/远程引用 | 本书与书库外哨兵字节不变，无自动网络请求或脚本副作用；合法同目录资源控制可读 |
| E-04 | AC-03，T-00/03/04 | 冻结预算边界前/等于/超出、小型高压缩比夹具/伪造声明长度 | 限制前检查且实际输出累计受限，超出明确拒绝不OOM/无限展开；不是压缩输入小就放行 |
| E-05 | AC-03/04，T-01/03/04 | 缺OPF/spine目标/图片、坏XML/ZIP、DRM/固定版式、不可写/中断 | 错误/不支持明确可见，不发布空书；既有库与原件保持，恢复条件后下一次导入可成功 |
| E-06 | AC-05，T-04 | 两端实际输入导入路径、点目录/内链/改字号/保存并退出重开 | UI事件确实触发生产处理链；HTTP预导入只属API隔离，不计本项通过；0场景/跳过/超时非pass |

拟新增 `tests/fixtures/epub/` 与 `tests/epub/verify_epub.py --profile vue|vm`（T-04制作永久入口，当前不存在）；固定数据根/端口/实际CLI/MCP版本与制品hash。复用既有 `tests/real-book.spec.ts`、`tests/review/reader001_r8_native_vm_restore.py` 的有效方法，不能改弱其几何判据。原001应用级/框架检查按实际共享路径复跑，纯计划阶段不跑Cargo/docs_gen/GUI。

## 7. 验收标准

| ID | owner_stage | 可观察标准 |
|---|---|---|
| AC-01 | work | 3份真实reflow EPUB3（含中文）在离线状态具有正确目录/spine顺序、正文/本地图片和内部链接回返；原件受管保存，不依赖002/Notes |
| AC-02 | work | 书版本/资源/内容locator正确，改基本字号/混排及正常/异常退出重开回到原句真实可见；旧TXT/MD不回归。原r2高亮恢复由002-A的AC-02承担，未据此宣称高亮已实现 |
| AC-03 | work | E-03/04/05安全/预算/失败与重试闭环通过，越界/坏书不影响既有库；资源预算/支持决策在依赖实现前固定 |
| AC-04 | work | 固定版式/DRM/复杂未支持特性给准确结果，支持矩阵与实际一致；不以空白正文/只解析ZIP宣称导入成功 |
| AC-05 | work | Vue＋VM HTTP和原生VM＋VM HTTP分别有真实UI导入/阅读/恢复证据；CAP-01..04必需缺口已关闭，MCP/环境限制未解决不转为债务放行 |
| AC-06 | review | 冻结实现/依赖，核对AC-01..05、独立失败控制/旧库和SD-01/02，无未闭项；说明review上下文独立性限制 |
| AC-07 | merge | 最终门后沉淀实际Spec/ledger、提交推送、归档003与AutoOS精确pin/健康/总表；独立clone留main、组合子模块detached，不声称Linux或002联动已完成 |

## 8. 执行步骤

- [x] T-00（owner_stage=work；依赖001实际交付；AC-01..05）：冻结CAP-01..04与最小profile；验证候选ZIP/XML/二进制/图像/原生入口，输出capability-decision.md；必要缺项具名立最小owner前置，不依赖完整002。[✅ 2026-10-31] capability-decision.md 已产出（commit f251eed）：真sha256/字节读写字节精确/file.copy/image.thumb 可用；zip/xml native 不存在→纯.at 栈；惰性按章解压架构（导入期结构校验、首读期解压）；预算冻结。探针 t00_epub_cap_probe{,2..10}.as。
- [x] T-01（owner_stage=work；依赖T-00与实际具名前置交付；AC-01/03/04）：实现EPUB容器/package/spine/nav/资源adapter与受管导入提交、旧库格式兼容；数据先验证再发布，不改原件。[⛔→✅ 2026-10-31 解除] 原纯.at DEFLATE 路径被运行时列表缺陷 N-003-1..6 阻断（framework-gap.md 在案）；用户裁决走选项 B，auto-lang 仓 **PLAN-897 已交付归档**（zip.list_json/read_text/extract_entry 三 native，VM 轨探针 22/22 PASS，merge a25e67983、archive 3fa75dd9c）。新 CLI＝D:/autostack/auto-man/target/debug/auto.exe SHA256 706d13f56277fc70913571bee675b554a3d08e4809d67953fe4d8ed5a2310543（版本串仍 118；以 SHA 为准）。T-01 改线：ZIP/解压全走 zip natives（max_bytes 直传 CAP-03 预算），XML/OPF/nav 用纯 .at str 扫描（字节索引域，可靠）；inflatex.at 归档为能力研究记录（不被消费）。 [✅ 2026-10-31 r2 续跑] epub.at 导入事务交付（commit 5e9b513）：zip natives（PLAN-897）+ 纯 .at XML 扫描（find/substr 字节域）；sha256 整文件身份；file.copy 受管副本 + sha256 读回对账；epubmeta 边车；library .epub 分派（UTF-8 预检前）。t08 spec 8/8 PASS（首导/去重/force/非EPUB/缺文件）；过程实录：VM 字符串机制多坑（多操作数拼接链毒化、 转义不受支持、tag 前缀边界）→ 改线为单遍 manifest 扫描 + 可见分隔符。
- [ ] T-02（owner_stage=work；依赖T-01；AC-01/02/05）：接共用最小内容模型、真实目录/图片/内链与基本字号，扩充兼容locator和持久恢复；不实现002注释系统。
- [ ] T-03（owner_stage=work；依赖T-01及T-00预算决策；AC-03/04）：完成规范化路径、禁止活动内容/外部实体/远程加载、实际解压/图像预算与失败回滚/可重试状态。
- [ ] T-04（owner_stage=work；依赖T-02/T-03；AC-01..05）：制作永久fixture/双端入口并跑E-01..06及受影响旧库回归，准备SD-01/02，提交实现/证据摘要后execution_done；本轮不执行。
- [ ] T-05（owner_stage=review；依赖T-04；AC-06）：同一clone暂停实现，冻结版本最终复审真实用户任务/负控/Spec；无pass不进入merge，不以002未来能力代替。
- [ ] T-06（owner_stage=merge；依赖T-05；AC-07）：完成实际统一门、交付、规范/账本、归档与组合pin/总表；给002-A提供已交付内容/定位接口。

## 9. 复审记录

r3变更授权与归属：原r2保留于 `4d6345cc37882b0216480661eefae4c773617c2d`，blob `ea72d53012faff52a28c39d0cdc3c356682a1ed3`。原003依赖完整002改为仅依赖已交付001＋本计划能力门；原T-00..04编号保留并细化，新加review/merge步骤。原AC-01/03/04/05范围保留；AC-02拆为本计划必需的位置恢复与002-A必需的高亮/注释恢复，不丢失原需求，也不把后者算作本次已经通过。

stage: new | plan_id: READER-003 | plan_revision: 3 | outcome: pass（首个有界能力调查就绪，非EPUB功能通过） | next: work/T-00（仅在另行进入执行时）。7项任务全未勾选，本轮无实现/构建/运行验收。

stage: work | plan_id: READER-003 | plan_revision: 3 | round: 1 | outcome: **blocked（T-01 被运行时列表缺陷阻断；T-00 已完成）** | worktree_path: D:/autostack/.wt/reader-003/auto-reader | branch: plan-003-dev | base_commit: fa6185e | code_commit: f251eed（T-00 能力决策）→ ca9d86f（T-01 inflate 参考实现 + framework-gap.md） | dependency_revisions: auto 0.1.0+v0.0.20-118-ge6cc06f（较计划基线 -117 新一个补丁集；全部探针/证据在 -118 上实跑） | task_ids: T-00 ✅, T-01 ⛔ | evidence: docs/plans/evidence/003/{capability-decision.md,framework-gap.md}；探针 tests/probe/t00_*（26 个）；运行时失真直接证据＝%TEMP%/partial_out.bin（解码输出=期望文本逐字节+7）对照 vec_fixed_expected.txt | blockers: N-003-1..6（VM 列表读写语义，见 framework-gap.md 缺陷目录）；解除动作＝框架 owner 交付最小前置（选项 A 修复列表读值语义 / 选项 B 提供 zip·inflate native）并取得交付回执 | next_responsible_role: 框架 owner（auto-lang/auto-man），随后本计划 work 续跑 T-01..T-04

stage: goal | plan_id: READER-003 | plan_revision: 3 | round: 1 | from: work | to: user（框架侧前置） | status: executing | outcome: blocked | worktree: D:/autostack/.wt/reader-003/auto-reader（保留，plan-003-dev @ ca9d86f） | commit: 34d762c 不可用（本轮主仓仅计划记账） | next: user/框架侧；goal 链按停止条件交回，恢复动作见 §10 与 framework-gap.md

stage: goal | plan_id: READER-003 | plan_revision: 3 | round: 2 | from: user（框架前置交付） | to: work | status: executing | outcome: pass（解除条件达成，T-01 续跑） | framework_delivery: auto-lang PLAN-897 archived（3fa75dd9c；natives merge a25e67983；新 CLI SHA256 706d13f5…） | worktree: D:/autostack/.wt/reader-003/auto-reader（保留） | next: work/T-01（zip natives + 纯 .at XML 改线）

stage: work | plan_id: READER-003 | plan_revision: 3 | outcome: pass（T-01 完成；T-02..T-04 继续 executing） | worktree_path: D:/autostack/.wt/reader-003/auto-reader | branch: plan-003-dev | base_commit: fa6185e | code_commit: 5e9b513（epub.at 导入事务 + library 分派 + t08 spec） | dependency_revisions: auto CLI SHA256 706d13f5…（PLAN-897 后） | task_ids: T-01 ✅ | evidence: tests/spec/t08_epub_import_spec.as 8/8 PASS（隔离 AUTO_READER_DATA）；fixture 生成器 tests/spec/plan897_make_epub.py | blockers: 无（T-02 章读取/目录/T-03 收尾/T-04 验证套件待做） | next_responsible_role: work（同会话继续）

stage: work | plan_id: READER-003 | plan_revision: 3 | outcome: pass（T-02 后端完成；前端 reading_page EPUB 分支 + T-03/T-04 继续） | code_commit: 7eb48b9（epub 章惰性解压+缓存、epub_toc_json、library toc/chapter EPUB 分支） | task_ids: T-02 后端 ✅（前端待做） | evidence: t08 19/19 PASS（含 TOC nav 标签→spine 序号、章文本/图片标记行/缓存一致性/越界占位、TXT 旧路不回归） | 过程实录: find_after 包含语义使记录遍历 e==s 卡死 → 改「管道=记录尾」遍历（substr(pos, s-pos), pos=s+1） | next_responsible_role: work（同会话继续）
stage: goal | plan_id: READER-003 | plan_revision: 3 | round: 3 | from: work(T-02 后端) | to: work(T-02 前端) | status: executing | outcome: pass（续跑点已冻结） | 续跑清单: ① reading_page.at EPUB 分支——is_real 时按段落文本前缀 "img:" 渲染图片（image widget；src 需后端解析媒体 URI：先探 image.thumb 在 VM HTTP 服务上下文可用性＝capability-decision §CAP-02 首探针，不可用则回退占位行+诚实提示并升级缺口路由）；② T-03 收尾：epub_href_ok 已拒 ../绝对/盘符/反斜杠//%——补导入失败回滚对账（受管副本 sha256 对账已做，索引失败时受管孤儿=可诊断可重试语义已在案）；③ T-04：fixtures book1.epub（生成器已提交）+ verify_epub.py 双端入口 + E-01..06 + t01-t07 回归 + HTTP 层（library/import 走 .epub 分派的端到端）→ execution_done；④ 复审/merge 按 T-05/T-06。 | 关键事实: 新 CLI SHA256 706d13f5…（zip natives）；t08 19/19；TXT 旧路不回归；inflatex.at 归档为研究记录；epubmeta 字段 spine/man已删/toc/opf_dir/source_sha256/title/author/spine_n/toc_n | worktree: plan-003-dev @ 7eb48b9+89e8847(记账)
stage: work | plan_id: READER-003 | plan_revision: 3 | outcome: pass（images 解析完成） | code_commit: a640df4（img: 行 → zip.extract_entry 落缓存 + image.thumb 媒体 URI → 章 JSON images[] 字段；封面 72B 字节精确落盘） | evidence: t08 20/20 PASS | CAP-02 首探针: image.thumb 在新 CLI VM 轨可用（t10 probe，uri=/api/__auto/media/{id}/{rev}） | next: reading_page EPUB 分支（img: 段落→images[k] URI 渲染；Vue img / VM image widget）→ T-03/T-04

## 10. 待澄清事项

**⛔ 当前阻断（2026-10-31，T-01 work 阶段）**：纯 .at DEFLATE 解压被运行时列表缺陷阻断（N-003-1..6，证据与最小复现见 docs/plans/evidence/003/framework-gap.md；最直接证据＝解码输出与期望文本逐字节 +7 位移）。**解除动作（具名）**：框架 owner（auto-lang/auto-man）按 framework-gap.md「最小修复选项」交付其一——A：修复 VM 列表读值失真（convert.rs Vec<i32> push_to_stack 路径嫌疑）使 src/back/inflatex.at 参考实现通过 t00_inflate_probe；或 B：提供 zip/inflate native。取得交付回执后本计划按 CAP-01 路由恢复 T-01..T-04，目标/AC/范围不变。在回执前本计划不推进实现、不以 fixture 注入或降低验收替代。

产品优先级与不等待完整002已获用户确认，无需重复确认。T-00负责确定真实依赖/许可、二进制身份、内容/locator schema、资源预算及原生导入/导航可驱动性；这些不确定性不能留到写完解析器后再假设。若需要超出最小profile或变更旧库兼容承诺，先提出具体修订，不自行扩面。

本轮文档预检：直接依赖仅001，CAP门有具名owner与首探针；任务/AC/规范增量、源码hash及链接检查通过；未实现EPUB、未运行应用功能测试。

2026-10-31 T-00 补充裁定（冻结于 capability-decision.md）：真 sha256（hash.file_sha256/sha256）可用→EPUB 书版本身份用 sha256（TXT/MD 的 ph1 语义不动）；字节读写带规避可用；zip/xml native 不存在→纯 .at ZIP/inflate/XML；图像走 image.thumb 媒体 URI 双端同源；惰性按章解压（导入期结构校验、首读期解压+逐条目完整性）；条目完整性以 inflate 结构完成性为准（CRC-32 因无位运算逐位模拟异或成本不成比例，SD-01 如实记录弱化）。运行时 CLI 由 -117 漂移到 -118，按「假设变更即重跑」全部证据在 -118 重建。
