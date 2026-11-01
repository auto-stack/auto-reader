# Readest × AutoReader 能力对标矩阵（READER-006）

状态：drafted · 2026-11-01。证据绑定：Readest 上游源码 = tag **v0.12.16**（commit `3cc39ad7a558e6612e1a8135058fbd6f3c90b3e3`，工作树干净）；UI = 官方 **0.12.16 Windows x64 portable**（SHA256 `683a620d…`，与源码同一 tag）。研究基线见 [baseline](baseline.md)；真机 UI 实测见 [ui-study](ui-study.md)；上游代码结构见 [code-map](code-map.md)。原始逐行清单与完整证据链在仓外 `D:/autostack/plan-artifacts/plan-006/notes/t01-inventory.md`。

## 0. 计数口径与列说明

**行 ID**：`RDT-Cxx-NNN` 自 T-01 清单原样继承，不重编号、不删行。跨域同能力仅在主域计数，跨引行标注「主行 RDT-…」。

**发布状态取值**：

- `released ≤0.12.16`：随 v0.12.16 发布线交付，早于最早 release-notes 条目（0.7.9）或无版本记载。
- `released x.y.z`：随发布线交付，RN 记载引入版本。
- `code-only`：代码在库但生产界面不可达（仅 RDT-C05-035）。
- `主分支候选`：仅存在于 main（v0.12.16..main，183 提交），**不进发布分母**，集中列于 §4。

**Readest 证据列标记**：

- `✓实测` = [ui-study](ui-study.md) 在 0.12.16 portable 真机上驱动验证过该能力（节号可溯）。
- `入口在册(实测)` = 真机见到入口/面板/失败面，功能成功面未驱动（缺证具名，见 §6）。
- `repo path:line` = tag v0.12.16 工作树内证据，路径默认相对 `apps/readest-app/`；`architecture.md`、`bookshelves.md` 等 = `apps/readest-app/docs/`；`RN x.y.z` = `release-notes.json` 条目；`docs` = readest.com/docs（2026-11-01 快照）。
- 付费/账号/在线等服务门在「平台/服务条件」列保持可见，不因真机不可达而从表内消失。

**AutoReader 现状列（受控词表）**——唯一来源为 [真实书库 Spec](../../specs/reader/real-library.md)、[EPUB Spec](../../specs/reader/epub-reflow.md)、[注释 Spec](../../specs/reader/reading-annotations.md)、[独立阅读 Spec](../../specs/reader/standalone-reading.md) 与[设计文档 §2](../../design/01-product-design.md)，外加 Spec 具名能力边界（Locator v1 非 CFI、高亮为段级标记、无 PDF、无 TTS、Notes 交接属 OS）：

- `完整`：Spec 记载且与本行等价或更强（从严使用）。
- `部分（差距：…）`：Spec 记载了对应能力但有具名差距。
- `缺失`：交付基线（设计文档 §2 表）之外、且 §3 列为对标域/具名差距的未交付面。
- `待验证(未在Spec中记载)`：Spec 未记载，不做猜测。
- `排除（需裁定来源）`：属需独立裁定的来源/商业模式（付费云体系，设计文档 §1）。

---

## 1. C01 文件与书库（55 行）

| ID | 能力 | 发布状态 | 平台/服务条件 | Readest 证据 | AutoReader 现状 | 差距与覆盖 |
|---|---|---|---|---|---|---|
| RDT-C01-001 | 本地导入书籍（文件选择、批量） | released ≤0.12.16 | — | `src/services/constants.ts:61-76`；`src/app/library/components/ImportMenu.tsx` ✓实测（导入→书卡链路；0.12.16 Windows 对话框导入存在受管副本缺失+打开静默失败缺陷，ui-study §1） | 部分（差距：路径式导入对话框已交付；原生文件选择器与批量导入未交付（§2 具名差距）） | 导入事务/错误码族已交付（Spec RL §3）；文件选择与批量面为差距 |
| RDT-C01-002 | 拖放导入 | released 0.9.21 | desktop | RN 0.9.21；`src/components/DropIndicator.tsx` | 待验证(未在Spec中记载) | 拖放导入面无 Spec 记载 |
| RDT-C01-003 | 拖放整个文件夹导入 | released 0.11.1 | desktop | RN 0.11.1 | 待验证(未在Spec中记载) | 同上 |
| RDT-C01-004 | 从文件夹导入（格式/大小过滤） | released 0.11.2 | desktop + 移动读外部文件夹 | RN 0.11.2；`ImportFromFolderDialog.tsx`；docs /docs/library | 待验证(未在Spec中记载) | 默认过滤 EPUB/PDF、≥20 KB |
| RDT-C01-005 | 递归导入文件夹 | released 0.9.95 | — | RN 0.9.95；`src-tauri/src/dir_scanner.rs` | 待验证(未在Spec中记载) | |
| RDT-C01-006 | 原地阅读（不拷贝） | released 0.11.2 | 原地删除连原文件 | RN 0.11.2；`src/services/ingestService.ts:45-63`；docs | 缺失（受管副本为唯一资产形态，Spec RL §2/§3） | 架构取向不同：AutoReader 恒建内容寻址受管原件 |
| RDT-C01-007 | 监视文件夹自动导入 | released 0.11.18 | desktop | RN 0.11.18；`WatchedFoldersPane.tsx` | 待验证(未在Spec中记载) | |
| RDT-C01-008 | 链接导入（URL→书/文章） | released ≤0.12.16 | 服务端抓取 | `src/pages/api/send/fetch-url.ts`；docs | 缺失（未交付；§3 C01 对标范围列名「URL 导入」） | |
| RDT-C01-009 | 网页浏览器剪辑（含登录页） | released 0.12.6/0.12.8 | 原生浏览器捕获；拒私有 IP | RN；`WebSourcesDialog.tsx:104`；`web_browser.rs`/`clip_url.rs`/`browser_fetch.rs` | 待验证(未在Spec中记载) | |
| RDT-C01-010 | 网络小说导入（章节选择） | released 0.12.1/0.12.6 | 章节 URL；0.12.8 解码加固 | RN；`ImportNovelDialog.tsx:236`；architecture.md:547 | 待验证(未在Spec中记载) | |
| RDT-C01-011 | 系统分享导入（Send to Readest） | released 0.11.2 | iOS/Android/macOS；网页剪为 EPUB | RN 0.11.2；docs（0.12.16 修复分享回归） | 待验证(未在Spec中记载) | |
| RDT-C01-012 | 浏览器扩展导入 | released ≤0.12.16 | Chrome/Edge/Brave/Arc；浏览器内以用户会话制 EPUB | `apps/readest-app/extension/send-to-readest`（architecture.md:21）；docs | 待验证(未在Spec中记载) | |
| RDT-C01-013 | 邮件发送到书库 | released 0.11.2 | **Plus/Pro/完整自定义**私有地址；25 MB/1 附件；主题标签→标签；发件人白名单 | docs；`workers/send-email`；`src/pages/api/send/inbox.ts`、`send/senders.ts`；`send/page.tsx` | 待验证(未在Spec中记载) | 服务门：付费私有地址；另有本机 drain（`inboxDrainer.ts`） |
| RDT-C01-014 | 内容/元数据哈希去重（同书不重导入） | released ≤0.12.16 | — | `src/services/ingestService.ts:17-119`；docs | 完整 | 与 AutoReader 等价或更强：ph1 候选+逐字核对（TXT/MD）、sha256（EPUB）、碰撞隔离不串文不误判重（RL §3、ER） |
| RDT-C01-015 | 编辑元数据 | released 0.9.64/0.9.67 | 改动存配置不改文件 | RN；`src/components/metadata/BookDetailEdit.tsx:69-160`（封面替换/锁定 :212-250） 入口在册(实测详情对话框) | 部分（差距：导入时题名/作者入索引已交付；导入后元数据编辑未在 Spec 记载） | BookRecord 字段集固定（RL §2） |
| RDT-C01-016 | 在线元数据补全（Google Books/Open Library） | released 0.9.67-era/0.10.1 | 在线服务 | `src/app/api/metadata/search`（architecture.md:341）；`BookDetailEdit.tsx:326` | 缺失（未交付；§3 C01 对标范围列名「元数据」） | |
| RDT-C01-017 | 封面提取/替换/保存 | released ≤0.12.16（SVG 0.9.95；封面目录 0.9.94） | — | RN；`BookDetailModal.tsx`；`src-tauri/src/cover_thumbnail.rs` | 缺失（§2 具名差距：书封未交付；BookRecord 无封面字段） | |
| RDT-C01-018 | Calibre 丛书信息解析 | released 0.9.100 | — | RN；docs（供 Series 分组） | 待验证(未在Spec中记载) | |
| RDT-C01-019 | MD 标题/作者自动解析 | released 0.12.1 | — | RN 0.12.1 | 部分（差距：MD `#`/`##` 章切分已交付（RL §3）；标题/作者自动解析未记载——无章头以文件主名为题） | |
| RDT-C01-020 | 自定义分组（嵌套「/」层级） | released 0.9.11/0.9.92 | 分组同步 0.12.6 | RN；`GroupingModal.tsx`、`GroupItem.tsx` | 缺失（§2 具名差距：组织与检索体验需对标） | |
| RDT-C01-021 | 多维分组（作者/丛书/标签/状态等） | released 0.9.99 | — | `src/types/settings.ts:45-52`；docs | 缺失（同上） | |
| RDT-C01-022 | 标签与批量打标 | released 0.12.10 | — | RN；`TaggingModal.tsx` | 缺失（同上） | 注意区分：注释级 tags 已交付（RA），书目级标签无 |
| RDT-C01-023 | 可配置书架系统 | released 0.12.10 | — | RN；`docs/bookshelves.md`（完整规格）；`BookshelvesDialog.tsx` | 缺失（同上） | 内置：最近阅读/有声书/播客/默认/已读完 |
| RDT-C01-024 | 排序（11 键） | released（0.9.35→0.12.16 累计） | — | `src/types/settings.ts:18-30`；`ViewMenu.tsx` | 缺失（§2 具名差距：组织与检索体验） | |
| RDT-C01-025 | 自然数标题排序 | released 0.12.16 | — | RN 0.12.16 | 缺失（同上） | |
| RDT-C01-026 | 次级排序 | released ≤0.12.16 | — | `ViewMenu.tsx:82`；`settings.ts:34-41` | 缺失（同上） | |
| RDT-C01-027 | 书架过滤条件（嵌套 AND/OR） | released 0.12.10-era | 定义 ≤60 KB | `docs/bookshelves.md:69-95`；`BookshelfFilterEditor.tsx` | 缺失（同上） | |
| RDT-C01-028 | 书库头部搜索 | released 0.9.31/0.9.67 | — | RN；`LibrarySearchResults.tsx` 入口在册(实测顶栏搜索入口，ui-study §5) | 缺失（§2 具名差距：组织与检索体验） | 书内搜索已交付（RA），书库级检索无 |
| RDT-C01-029 | 跨书全文搜索 | released 0.12.1 | 逐书 sidecar 索引；纯云书跳过 | RN；`LibrarySearchResults.tsx`；docs | 部分（差距：书内段粒度精确子串搜索已交付（RA，≤2000 章/≤50 条）；跨书检索未交付（§2 具名差距「跨书检索尚不完整」）） | |
| RDT-C01-030 | Goodreads 书目搜索 | released 0.11.10 | 在线服务 | RN 0.11.10 | 缺失（未交付；§2 具名差距：检索体验） | 服务门：在线 |
| RDT-C01-031 | 设置模糊搜索（命令面板） | released 0.9.99 | — | RN；`src/services/commandRegistry.ts`；`src/components/command-palette/` | 待验证(未在Spec中记载) | |
| RDT-C01-032 | 阅读状态管理（读完标记/设状态） | released 0.9.99 | — | RN；`SetStatusAlert.tsx`、`StatusBadge.tsx` | 待验证(未在Spec中记载)（ReadingState 进度态已交付（RL §5）；「读完标记」面未记载） | |
| RDT-C01-033 | 删除语义：仅本地/仅云端/两者；确认对话 | released（0.9.63→0.9.80） | 云端项在第三方 provider 激活时隐藏 | RN；docs /docs/sync；`src/services/cloudService.ts`（architecture.md:419） ✓实测（三选项+确认对话；复验一次未生效待重验，ui-study §1） | 部分（差距：本地可恢复移除已交付（removed.jsonl+restore，RL §4）；无云端语义（无云面）） | 对照：Readest 0.12.16 tombstone 永不复活、无恢复 UI（ui-study §1）；AutoReader 反具可恢复移除 |
| RDT-C01-034 | 全库 zip 备份/恢复 | released 0.10.1/0.12.10 | 恢复按戳合并（bookshelves.md:155） | RN；`BackupWindow.tsx`；`src/services/backupService.ts`；`src-tauri/src/backup_zip.rs` | 部分（差距：library.json.bak 单级备份+refuse-to-load+读回校验已交付（RL §2/§3）；全库 zip 备份/恢复未交付） | |
| RDT-C01-035 | 导入期页数统计；页数排序/过滤 | released 0.12.1/0.12.16 | 部分格式首开计数 | RN；docs | 部分（差距：导入期章节计数（chapter_count）已交付（RL §2/§3）；「页数」口径未交付） | |
| RDT-C01-036 | 批量刷新元数据 | released 0.10.1 | 在线 | RN 0.10.1 | 缺失（未交付；§3 C01 对标范围列名「元数据」） | |
| RDT-C01-037 | 最近阅读书架 | released 0.11.17/0.11.20 | 小组件联动 | RN；`RecentShelf.tsx` | 缺失（§2 具名差距：组织面） | |
| RDT-C01-038 | 导入失败清单对话框 | released ≤0.12.16 | — | `FailedImportsDialog.tsx`；docs | 待验证(未在Spec中记载)（导入错误码族已交付（RL §3）；失败聚合对话框未记载） | |
| RDT-C01-039 | 导入到当前选中分组 | released 0.9.92 | — | RN 0.9.92 | 缺失（依赖分组面，未交付） | |
| RDT-C01-040 | 图书分享公开链接（1/3/7 天过期、进度、撤销） | released 0.11.1 | 上传耗配额；读者需账号 | RN；`src/app/s/`、`src/app/o/`（architecture.md:177）；`SharedLinksSection.tsx`；`src/app/api/share/*` | 待验证(未在Spec中记载) | 服务门：配额 |
| RDT-C01-041 | 从详情导出原书文件 | released 0.9.98/0.11.4 | — | RN | 待验证(未在Spec中记载)（受管原件在库（RL §2）；导出端点未记载） | |
| RDT-C01-042 | 更改数据目录/迁移 | released 0.9.82/0.9.90 | — | RN；`MigrateDataWindow.tsx` | 部分（差距：AUTO_READER_DATA env 解析+损坏迁移为人工动作已记载（RL §2/§3）；数据目录迁移 UI 未交付） | |
| RDT-C01-043 | 云端存储管理（查看/删除） | released 0.9.92/0.9.95 | 账号 | RN；`StorageManager.tsx`；`src/pages/api/storage/*` | 缺失（无云面；§3 C07 对标域） | |
| RDT-C01-044 | 缓存管理 | released ≤0.12.16（mobile；desktop 主分支） | — | `CacheManagerWindow.tsx`；docs /docs/advanced | 待验证(未在Spec中记载) | desktop 版为主分支候选（#7066） |
| RDT-C01-045 | 桌面小组件（iOS 最近/Android 书架+在读+TTS 迷你播放） | released 0.11.17/0.12.12 | 仅移动端 | RN；docs | 待验证(未在Spec中记载) | |
| RDT-C01-046 | 隐藏封面（隐私） | released 0.12.6 | — | RN；`docs/bookshelves.md:39-48` | 缺失（书封面未交付，随封面的隐私开关不适用） | |
| RDT-C01-047 | 封面裁剪/适应+网格封面尺寸 | released 0.9.61/0.9.94 | — | RN；`docs/bookshelves.md:44-48` | 缺失（同上） | |
| RDT-C01-048 | 列表视图/按丛书浏览 | released 0.9.37/0.11.10 | 网格为默认 | RN | 缺失（§2 具名差距：组织面） | |
| RDT-C01-049 | 全选与多选批量操作 | released 0.9.49 | — | RN；`SelectModeActions.tsx` | 缺失（§2 具名差距：批量面未交付） | |
| RDT-C01-050 | 书目右键菜单 | released 0.8.9/0.8.6 | — | RN；`BookContextMenuPopup.tsx` | 待验证(未在Spec中记载) | |
| RDT-C01-051 | 首发示例书（分语言） | released ≤0.12.16 | web 平台按 URL 导入 | `useDemoBooks.ts`；`src/services/demoBooks*` | 部分（差距：书架含真实/Demo 徽标合并面已交付（RL §1）；首启自动导入/分语言样本未记载） | |
| RDT-C01-052 | 深链打开（readest://）+分享落地页 | released ≤0.12.16（批注深链 0.11.1/0.11.20） | tauri deep-link 注册 | `src-tauri/src/lib.rs:760,852-853`；docs | 待验证(未在Spec中记载)（hash 路由面已记载（RL §7）；外部 scheme 深链未记载） | |
| RDT-C01-053 | 文件关联/打开方式 | released 0.8.2+（macOS 0.9.96；iOS 0.9.96；Android 0.9.95） | — | RN；README；docs ✓实测（argv 携路径启动即导入直开；软删不去重缺陷在册，ui-study §1） | 待验证(未在Spec中记载) | |
| RDT-C01-054 | Windows 资源管理器缩略图+预览面板 | released 0.9.94/0.12.12 | Windows shell 扩展 | `apps/readest-app/extensions/windows-thumbnail`（architecture.md:23）；RN；docs | 待验证(未在Spec中记载) | |
| RDT-C01-055 | 子文件夹结构转分组导入 | released ≤0.12.16 | 文件夹导入选项 | docs（"Create groups from subfolders"）；ImportFromFolderDialog 选项核实 | 待验证(未在Spec中记载) | |

计数：55 行已发布；服务/账号门 4（邮件地址通道 C01-013、分享配额 C01-040、在线元数据 C01-016、Goodreads C01-030；C01-029 为部分门）。

---

## 2. C02 阅读与排版（60 行）

| ID | 能力 | 发布状态 | 平台/服务条件 | Readest 证据 | AutoReader 现状 | 差距与覆盖 |
|---|---|---|---|---|---|---|
| RDT-C02-001 | 分页模式（1/2→4 栏） | released ≤0.12.16（iPad 竖排多栏 0.9.58） | — | README；`LayoutPanel.tsx:750` ✓实测（双栏对页/单栏自适应，ui-study §2） | 缺失（§2 具名差距：分页未交付；当前为连续滚动阅读面） | |
| RDT-C02-002 | 滚动模式（连续） | released ≤0.12.16（EPUB 连续 0.10.1；单节 0.10.2） | — | RN；`ControlPanel.tsx:467-495` ✓实测（Shift+J 跨章连续，ui-study §2） | 部分（差距：连续滚动已交付（scroll-pane，RL §5/RA）；单章滚动/重叠/滚动条隐藏等控制未记载） | |
| RDT-C02-003 | 滚动重叠像素 | released 0.9.43 | — | RN；`ControlPanel.tsx:482-488` | 待验证(未在Spec中记载) | |
| RDT-C02-004 | 栏间距 | released 0.12.12 | 双页对开 | RN；`LayoutPanel.tsx:740` | 待验证(未在Spec中记载)（列宽三档（narrow|medium|wide）已交付（RA）；栏间距未记载） | |
| RDT-C02-005 | 栏宽/栏高上限 | released ≤0.12.16 | — | `LayoutPanel.tsx:758-768` | 待验证(未在Spec中记载) | |
| RDT-C02-006 | 四边边距+附加 % 边距 | released 0.9.58 | — | RN；`LayoutPanel.tsx:690-738` | 待验证(未在Spec中记载) | |
| RDT-C02-007 | 字体族（衬线/无衬线/等宽+中文槽） | released ≤0.12.16（CJK 字体 0.9.26→0.9.62） | — | `FontPanel.tsx:309-405`；README ✓实测（Bitter/Roboto/Consolas+霞鹜文楷，ui-study §2） | 缺失（§2 具名差距：完整字体控制需调研；当前仅字号/行距档位） | |
| RDT-C02-008 | 自定义字体导入（TTF/OTF/TTC/WOFF2） | released 0.9.75→0.9.80 | 字体同步 0.11.1；云端按需 0.12.16 | RN；`CustomFonts.tsx`；`fontService.ts` | 缺失（§2 具名差距：完整字体控制） | |
| RDT-C02-009 | 字号+最小字号+字重 | released 0.9.10/0.9.43 | — | RN；`FontPanel.tsx:313-341` ✓实测（16→20 即时重排+字重，ui-study §2） | 部分（差距：三档字号（medium|small|large）已交付（RL §5）；连续字号/最小字号/字重未交付） | |
| RDT-C02-010 | 行距/段距/词距/字距/缩进 | released 0.9.10/0.9.55 | — | RN；`LayoutPanel.tsx:615-688` | 部分（差距：行距两档（comfy|compact）已交付（RL §5）；段距/词距/字距/缩进未交付） | |
| RDT-C02-011 | 两端对齐+连字符 | released ≤0.12.16（连字符语言覆盖 0.9.86） | — | `LayoutPanel.tsx:675-688`；docs | 待验证(未在Spec中记载) | |
| RDT-C02-012 | 主题（浅/深/自动；书库/阅读分轨） | released 0.9.52/0.12.8 | — | RN；`src/store/themeStore.ts`；`ThemePanel.tsx:532` ✓实测（浅/深/自动+预设+分轨生效，ui-study §2） | 部分（差距：阅读面三主题（light|sepia|dark）已交付（RA/RL §阅读状态扩展）；自动跟随与书库/阅读分轨未交付） | |
| RDT-C02-013 | 自定义主题（色彩编辑器/同步） | released 0.9.22→0.12.16 | — | RN；`src/components/settings/theme/` | 待验证(未在Spec中记载) | |
| RDT-C02-014 | 自定义前景/背景色+背景图 | released 0.9.53/0.9.85 | — | RN；`LayoutPanel.tsx:883-941` | 待验证(未在Spec中记载) | |
| RDT-C02-015 | 背景纹理（书库纹理/同步） | released 0.11.17 | — | RN；`src/store/customTextureStore.ts`；`docs/bookshelves.md` | 待验证(未在Spec中记载) | |
| RDT-C02-016 | 覆盖出版方样式/允许 EPUB JS | released（allow-script 0.9.51） | JS 逐书选入 | RN；`ControlPanel.tsx:726-728` ✓实测（「覆盖书籍字体」开关在册，ui-study §2） | 缺失（章节 XHTML→文本行管线无出版方 CSS 层（ER；§2 具名差距「出版物样式」）；活动脚本按安全边界恒拒绝（ER §安全与拒绝）） | |
| RDT-C02-017 | 图片查看/保存/反色（图库/全屏/右键菜单） | released（0.9.101→0.12.12 累计） | — | RN；`ImageViewer.tsx`、`ImageContextMenu.tsx` ✓实测（单击→全屏查看器：缩放/分享/题注/图库导航，ui-study §2） | 部分（差距：章图提取+应用自有媒体端点+渲染/错误行已交付（ER/SR）；全屏查看器/缩放/保存/反色等查看面未在 Spec 记载） | |
| RDT-C02-018 | 宽表横向滚动/表格查看器 | released 0.11.4 | — | RN；`TableViewer.tsx` | 缺失（§2 具名差距：复杂表格未保留——XHTML→文本行管线（ER）） | |
| RDT-C02-019 | 代码语法高亮 | released 0.9.56 | — | RN；README；`commandRegistry.ts:437` | 待验证(未在Spec中记载) | |
| RDT-C02-020 | 笔记数学公式 | released 0.12.1 | MD 书内 $/$$ 为主分支 | RN 0.12.1 | 缺失（§2 具名差距：公式未保留） | |
| RDT-C02-021 | 中文直排（横竖切换/RTL 方向） | released 0.9.0→0.9.33 | — | RN；`LayoutPanel.tsx:556-611`（边框样式族在列） | 缺失（§2 具名差距：竖排未保留） | |
| RDT-C02-022 | 简繁转换（simplecc-wasm 全变体） | released 0.9.94 | UI 暴露子集 | RN；`LangPanel.tsx:379-380`；architecture.md:509；docs | 待验证(未在Spec中记载) | |
| RDT-C02-023 | 注音/割注（ruby/warichu） | released 0.11.1 | — | RN；architecture.md:509；docs | 待验证(未在Spec中记载)（XHTML→文本行管线未记载 ruby 处理） | |
| RDT-C02-024 | RTL 书籍支持 | released 0.9.19/0.10.6 | — | RN；`src/types/book.ts` | 待验证(未在Spec中记载) | |
| RDT-C02-025 | 脚注弹窗（响应式/回跳/弹内选区查词） | released（0.8.3→0.12.6 累计） | — | RN；`FootnotePopup.tsx` ✓实测（noteref 点击→浮层脚注原文，ui-study §2） | 部分（差距：书内链接/脚注往返已交付（链接 chips+JumpLink，ER/SR）；浮层弹窗形态未记载——现为行内 chips+抽屉跳转） | |
| RDT-C02-026 | 目录导航（嵌套/页码/当前位置高亮） | released（0.9.23→0.11.10 累计） | — | RN；`sidebar/TOCView.tsx`、`tocTree.ts` ✓实测（侧栏跳章+各章页数+当前位置高亮，ui-study §2） | 部分（差距：TOC 数据面+跳章已交付（/toc 端点+epubmeta，RL/ER）；嵌套层级/页码/当前位置高亮未在 Spec 记载（TOC 扁平）） | |
| RDT-C02-027 | 翻页动画（关/推/滑/卷） | released 0.9.101/0.11.18 | `docs/page-curl.md` 在该 tag 不存在 | RN；`ControlPanel.tsx:602-618` | 缺失（分页模式未交付（§2 具名差距），动画随之不适用） | |
| RDT-C02-028 | PDF 专属选项（主题色/反差/缩略图/缩放/手型/跨页选区/TTS+标注） | released（0.9.78→0.12.16 累计） | 主题色 iOS/macOS/Safari 受限（docs） | RN；`TOCView.tsx:80-96`；`ViewMenu.tsx:398-491` ✓实测（打开/缩略图/2-up/翻页/缩放/搜索；标注弹层未触发成功，ui-study §4） | 缺失（具名边界：无 PDF；§3 对标域） | |
| RDT-C02-029 | 固定版式（漫画 Webtoon/RTL 页序/动画/捏合） | released（0.11.10→0.12.10） | — | RN；`ViewMenu.tsx:535` | 缺失（具名边界：无 PDF/固定版式面；CBZ 未在 Spec 记载） | |
| RDT-C02-030 | 页眉页脚自定义（时间/电量/进度样式/剩余） | released（0.9.23→0.12.8 累计） | — | RN；`LayoutPanel.tsx:779-880`；`HeaderBar.tsx`；`footerbar/` | 待验证(未在Spec中记载) | |
| RDT-C02-031 | 常驻进度条+章节刻度 | released 0.11.17/0.9.96 | — | RN；`StickyProgressBar.tsx`、`ProgressBar.tsx` | 待验证(未在Spec中记载) | |
| RDT-C02-032 | 亮度调节（阅读器内/自动/边缘滑动） | released（0.9.85→0.11.2） | mobile | RN；`BrightnessOverlay.tsx`；`ControlPanel.tsx:663-672` | 待验证(未在Spec中记载) | |
| RDT-C02-033 | 竖屏/横屏锁定 | released 0.9.39 | mobile | RN；`LayoutPanel.tsx:952-971`（iOS 修复为主分支 #7146） | 待验证(未在Spec中记载) | |
| RDT-C02-034 | 电纸书模式（自动识别/全刷/全平台） | released（0.9.88→0.12.12） | e-ink 设备白名单 | RN；`ControlPanel.tsx:623-658`；`src-tauri/src/eink_identity.rs`；docs | 待验证(未在Spec中记载) | 白名单漂移守卫为主分支（#6834） |
| RDT-C02-035 | 氛围模式（视频叠加+环境音） | released 0.10.2/0.12.1 | — | RN；`AtmosphereOverlay.tsx`；`atmosphereStore.ts` | 待验证(未在Spec中记载) | |
| RDT-C02-036 | 自定义 CSS（正文/UI/书库三层） | released（0.8.5→0.9.62） | — | RN；`MiscPanel.tsx:199-211`；docs | 待验证(未在Spec中记载) | |
| RDT-C02-037 | 保留原书段落布局 | released 0.10.6 | — | RN；`LayoutPanel.tsx:617` | 待验证(未在Spec中记载)（管线即正文行，「原书版式保留」不适用——ER 能力边界） | |
| RDT-C02-038 | 缩放（Ctrl+滚轮/快捷键/级别） | released 0.9.94/0.12.8 | — | RN；`ZoomControls.tsx`；`ViewMenu.tsx:326-349` ✓实测（PDF Ctrl+滚轮放大，ui-study §4） | 待验证(未在Spec中记载) | |
| RDT-C02-039 | 全屏 | released 0.9.21/0.9.37 | desktop | RN；`ViewMenu.tsx:587`（触屏 web 全屏为主分支） | 待验证(未在Spec中记载) | |
| RDT-C02-040 | 快捷键帮助+自定义 | released 0.10.2/0.12.6 | — | RN；`KeyboardShortcutsHelp.tsx`、`KeyboardShortcutsSettings.tsx`；docs | 部分（差距：无全局键盘 handler 为具名边界（RA：widget 级触发）；快捷键自定义未交付） | |
| RDT-C02-041 | 点击/手势翻页定制（换边/禁双击/滚轮反向） | released（0.8.5→0.9.69） | — | RN；`ControlPanel.tsx:501-545,686-707` ✓实测（快速横拖被识别为翻页手势——边界观察，ui-study §0） | 待验证(未在Spec中记载) | |
| RDT-C02-042 | 手柄翻页 | released 0.9.99 | desktop/mobile | RN；`ControlPanel.tsx:701-702` | 待验证(未在Spec中记载) | |
| RDT-C02-043 | 实体翻页键（音量键绑定） | released 0.9.38/0.11.2 | mobile | RN；`PageTurnerSettings.tsx` | 待验证(未在Spec中记载) | |
| RDT-C02-044 | 安全区适配 | released ≤0.12.16 | mobile | `docs/safe-area-insets.md`（开发文档） | 待验证(未在Spec中记载) | |
| RDT-C02-045 | 沉浸式紧凑视图（页眉脚隐藏） | released 0.9.39 | — | RN 0.9.39 | 待验证(未在Spec中记载) | |
| RDT-C02-046 | 阅读保持亮屏 | released 0.9.13（备份 0.12.10） | — | RN；`ControlPanel.tsx:678-679` | 待验证(未在Spec中记载) | |
| RDT-C02-047 | 常显状态栏 | released 0.9.58 | — | RN 0.9.58 | 待验证(未在Spec中记载) | |
| RDT-C02-048 | 启动时打开上次的书 | released 0.9.39 | — | RN；`constants.ts` openLastBooks | 部分（差距：Locator 保存/恢复+滚动定位已交付（RL §5）；「启动即打开上次的书」入口行为未记载） | |
| RDT-C02-049 | 多窗口阅读 | released 0.9.65/0.9.68 | desktop | RN；architecture.md:202（Linux 双窗冻结 0.12.16 修复） | 待验证(未在Spec中记载) | |
| RDT-C02-050 | iPad 分屏+可调侧栏 | released 0.9.58 | iPadOS | RN 0.9.58 | 待验证(未在Spec中记载) | |
| RDT-C02-051 | 边框样式（双线框/框色，直排用） | released 0.9.22 | — | `LayoutPanel.tsx:594-611` | 待验证(未在Spec中记载) | |
| RDT-C02-052 | 阅读标尺（C05-025 跨引主行） | released（0.9.99→0.11.18） | — | RN；`ReadingRuler.tsx`；设计文档 `docs/superpowers/specs/2026-05-29-line-aware-reading-ruler-design.md` | 待验证(未在Spec中记载) | |
| RDT-C02-053 | 逐段阅读模式（C05-026 跨引主行） | released 0.9.99/0.12.10 | — | RN；`src/app/reader/components/paragraph/` 入口在册(实测 Shift+P，ui-study §2) | 部分（差距：段模型为阅读基座（RL §1「按段阅读」）；逐段聚焦/步进模式未记载） | |
| RDT-C02-054 | 速读模式 RSVP（C05-027 跨引主行） | released（0.9.99→0.11.10） | — | RN；`src/services/rsvp/`；docs（WPM/起始延迟/CJK 字模式） 入口在册(实测 Shift+V，ui-study §2) | 待验证(未在Spec中记载) | |
| RDT-C02-055 | 自动滚动（免手/右缘速滑/中键） | released 0.11.18/0.11.20 | — | RN；`AutoScrollControl.tsx`、`AutoScrollSpeedOverlay.tsx` 入口在册(实测，ui-study §2) | 待验证(未在Spec中记载) | |
| RDT-C02-056 | 对话高亮（引语） | released 0.12.12 | 嵌套/长对话为主分支（#6814） | RN 0.12.12 | 待验证(未在Spec中记载) | |
| RDT-C02-057 | 全局/单书视图设置（isGlobal；按设备本地） | released（单书作用域；0.11.12 按设备） | — | RN；`docs/view-settings.md:3,143-149` | 部分（差距：排版偏好随 ReadingState 持久化已交付（RL §5）；全局/单书作用域区分未记载） | |
| RDT-C02-058 | 分面板重置设置 | released 0.9.61 | — | RN；`SettingsDialog.tsx:316-320` | 待验证(未在Spec中记载) | |
| RDT-C02-059 | 章节导航按钮/快捷键 | released（0.9.39→0.9.90） | — | docs /docs/advanced | 待验证(未在Spec中记载)（TOC 数据面已交付（RL/ER）；章节导航控件未记载） | |
| RDT-C02-060 | 移动端手势/返回键处理 | released（0.9.64→0.9.78） | mobile | RN 入口在册(实测 487px 窄屏自动切移动布局+返回键在册，ui-study §7) | 待验证(未在Spec中记载) | |

计数：60 行已发布；服务/账号门 0（全本地）。含 5 行专注辅助（C02-052~055、055 即标尺/逐段/速读/自动滚动）被 C05 跨引。

---

## 3. C03 选区、标注与定位（28 行）

| ID | 能力 | 发布状态 | 平台/服务条件 | Readest 证据 | AutoReader 现状 | 差距与覆盖 |
|---|---|---|---|---|---|---|
| RDT-C03-001 | 选区与复制（保段落断行/吸词/跨页/放大镜） | released（0.9.100→0.12.6） | — | RN；`annotator/SelectionRangeEditor.tsx`；`MagnifierLoupe.tsx` ✓实测（真实拖选逐字命中，ui-study §3） | 缺失（§2 具名差距：无完整划词选区；点段=记位置为现交互（RA）） | |
| RDT-C03-002 | 高亮样式与颜色（3 式×5 色+自定义色/不透明度） | released（0.9.90→0.10.4） | — | `src/types/book.ts:30`；`HighlightOptions.tsx`；`commandRegistry.ts:401` ✓实测（高亮/下划线/波浪线+5 色弹层，ui-study §3） | 部分（差距：高亮为段级标记+chip 承载（具名边界 N-002-A-1，RA）；无行内子串样式；颜色/样式系未记载） | |
| RDT-C03-003 | 批注笔记（纯文本/Markdown/就地编辑） | released 0.9.52/0.9.58 | — | RN；`AnnotationNoteEditor.tsx`、`NoteEditorSheet.tsx` ✓实测（添加笔记→落盘→行尾图标+侧栏，ui-study §3） | 部分（差距：批注（quote+occurrence+comment≤2000+tags）已交付（RA）；锚为段级 quote 而非划词范围） | |
| RDT-C03-004 | 书签（ribbon/命名/侧栏编辑/下拉手势） | released（核心 ≤0.12.16；0.9.78/0.12.1） | — | RN；`BookmarkToggler.tsx`、`BookmarkPullDown.tsx`；`ControlPanel.tsx:561` ✓实测（侧栏添加+落盘+恢复；顶栏按钮未生效待复核，ui-study §3） | 部分（差距：书签为注释 kind+章级书签（para=-1）已交付（RA/RL §5）；命名书签/顶栏开关/下拉手势未记载） | |
| RDT-C03-005 | 摘录（不标内联高亮的引文） | released ≤0.12.16 | — | docs；`book-config.md:39` | 部分（差距：quote 摘录随批注必存已交付（RA）；独立「摘录」类型未记载——kind 仅 bookmark/highlight/comment） | |
| RDT-C03-006 | 全局高亮/全局批注（全部匹配位置） | released 0.11.2/0.12.12 | — | RN；docs ✓实测(入口：弹层「应用到本书所有匹配位置」选项在册，ui-study §3) | 待验证(未在Spec中记载)（段内 occurrence 重叠计数已交付（RA）；跨全书批量应用未记载） | |
| RDT-C03-007 | 即时标注模式（快捷动作/自定义/放大镜） | released（0.9.97→0.10.1） | — | RN；`ControlPanel.tsx:556-595` | 待验证(未在Spec中记载) | |
| RDT-C03-008 | 批注范围编辑 | released 0.9.97 | — | RN；`AnnotationRangeEditor.tsx` | 缺失（设计边界：锚字段不可变，换锚=删除+新建（RA）） | |
| RDT-C03-009 | 批注导航条/最近滚动 | released 0.9.97/0.11.4 | — | RN；`sidebar/AnnotationsToolbar.tsx` | 部分（差距：注释抽屉回访跳转已交付（RA）；导航工具条/最近批注滚动面未记载） | |
| RDT-C03-010 | 笔记本工作区（自动保存/同步/回链/搜索/Markdown/标签页） | released（0.9.52→0.12.6） | — | RN；`notebook/Notebook.tsx`、`notebookDocumentStore.ts` | 缺失（笔记本工作区未交付；注释抽屉+MD 导出为现面（RA）） | |
| RDT-C03-011 | 书内搜索（包含/整词/正则/附近词/大小写/变音符/范围/历史/章节分组） | released（0.9.97→0.12.1） | — | RN；`sidebar/SearchOptions.tsx`、`SearchResults.tsx` ✓实测（重复句 oracle 恰 3 结果+红标+跳转+浮动导航，ui-study §3） | 部分（差距：段粒度精确子串搜索已交付（RA：≤2000 章/≤50 条/truncated 如实标注）；无正则/整词/大小写折叠/附近词/历史/章节分组） | |
| RDT-C03-012 | 批注列表侧栏（页码显示与导出） | released 0.9.101 | — | RN；`sidebar/BooknoteView.tsx`、`BooknoteItem.tsx` ✓实测（侧栏列表+恢复，ui-study §3） | 部分（差距：注释抽屉（回访/编辑/删除/导出/重定位徽标）已交付（RA）；页码口径不适用（段定位）） | |
| RDT-C03-013 | 导出批注（MD/纯文本/JSON 可重导入） | released（MD 0.9.25；纯文本 0.9.99） | — | RN；`ExportMarkdownDialog.tsx`；docs ✓实测（三格式+选项+预览+每条 readest:// 深链，ui-study §3） | 部分（差距：Markdown 本地导出已交付（RA：locator/quote/occurrence/标签/annotation_id）；纯文本/JSON 格式未交付） | |
| RDT-C03-014 | 导出模板与选项（Jinja2 模板/按色过滤/句上下文/Obsidian 形态/封面/页码/日期） | released（0.9.98→0.12.12） | — | RN；docs | 待验证(未在Spec中记载)（MD 导出字段为固定集（RA）；模板/过滤/句上下文未记载） | |
| RDT-C03-015 | 导入批注（文件/ReadEra .bak/Moon+ .mrexpt） | released（0.12.1/0.12.8） | — | RN；`ImportAnnotationsDialog.tsx`；architecture.md:499-501 | 缺失（批注导入未交付；RA 端点面无导入） | |
| RDT-C03-016 | 批注深链（复制带链/readest:// 或 web） | released 0.11.1/0.11.20 | 预览模式回落 | RN；docs ✓实测（导出文件含 `readest://book/<hash>/annotation/<id>?cfi=…` 深链，ui-study §3） | 待验证(未在Spec中记载)（annotation_id 稳定性已交付（RA+005 冷重启驱动）；URI 深链回跳未记载） | |
| RDT-C03-017 | 引文卡片（图片分享 4 版式/主题/二维码回链） | released 0.12.16 | — | RN；`QuoteCardDialog.tsx`；docs | 待验证(未在Spec中记载) | |
| RDT-C03-018 | 手写批注/绘画（笔/马克/橡皮/同步） | released 0.12.16 | README 仍标 planned（表过期） | RN；`src/app/reader/components/handwriting/`；`handwriting/model.ts` | 待验证(未在Spec中记载) | |
| RDT-C03-019 | 选区分享到其他应用 | released 0.11.10 | 移动/桌面分享面板 | RN 0.11.10 | 待验证(未在Spec中记载) | |
| RDT-C03-020 | 定位符（CFI 位置+KOReader xpointer，逐书/逐批注） | released ≤0.12.16 | — | `docs/book-config.md:36-61` ✓实测（booknotes 内 `epubcfi(/6/4!/4/12,/1:7,/1:31)` 字符偏移级落盘，ui-study §3） | 部分（差距：Locator v1=章号+段号+para_text 逐字全文锚已交付（RL §5）；非 EPUB CFI/KOReader xpointer（具名边界，ER「不宣称 EPUB CFI」）） | 迁移设计关键对照：Readest=CFI 字符偏移，AutoReader=章+段+逐字锚 |
| RDT-C03-021 | 位置历史前进/后退 | released ≤0.12.16 | — | docs /docs/advanced | 待验证(未在Spec中记载) | |
| RDT-C03-022 | 校对规则（查找替换/正则/范围/应用面/优先级） | released（0.9.97→0.11.18） | — | RN；`ProofreadPopup.tsx`、`ProofreadRules.tsx`；`proofreadStore.ts`；docs | 待验证(未在Spec中记载) | |
| RDT-C03-023 | 清除全部批注（确认；书签/摘录不动） | released ≤0.12.16 | — | docs | 待验证(未在Spec中记载)（单条删除已交付（RA）；全清未记载） | |
| RDT-C03-024 | 标注工具栏自定义（拖拽动作/逐书或全局） | released 0.11.10/0.11.17 | — | RN；`AnnotationToolbarCustomizer.tsx`；`annotationToolbar.ts` | 待验证(未在Spec中记载) | |
| RDT-C03-025 | 批注渲染修复（侧栏色/列表/ruby 上渲染） | released（0.9.39→0.11.10） | — | RN | 待验证(未在Spec中记载)（并入 C03-002 口径） | |
| RDT-C03-026 | 批注即时渲染；同步删除不复活 | released 0.9.85/0.12.10 | — | RN | 待验证(未在Spec中记载) | |
| RDT-C03-027 | 侧栏批注编辑+选择期翻页提示 | released 0.9.78 | — | `annotator/PageTurnHint.tsx`；`sidebar/BooknoteView.tsx` 入口在册(实测侧栏书签添加/列表，ui-study §3) | 部分（差距：注释抽屉编辑已交付（RA）；PageTurnHint 等选择期 UX 未记载） | |
| RDT-C03-028 | 脚注弹窗内快捷动作/查词 | released ≤0.12.16 | 下一词查词修复为主分支 | `annotator/DictionaryPopup.tsx`；RN 0.12.6 | 待验证(未在Spec中记载) | |

计数：28 行已发布；服务/账号门 0（导出至 Readwise/Notion 计 C07/C05）。

---

## 4. C04 多格式（15 行）

格式面：`SUPPORTED_BOOK_EXTS = epub, mobi, azw, azw3, fb2, zip, cbz, pdf, txt, md, html, htm, mhtml, mht`（`src/services/constants.ts:61-76`）；原生解析器 `src-tauri/src/{epub_parser,mobi_parser,pdf_parser,comic_parser,parser_common}.rs`；渲染 foliate-js + pdfjs-dist（architecture.md:235-250）。

| ID | 能力 | 发布状态 | 平台/服务条件 | Readest 证据 | AutoReader 现状 | 差距与覆盖 |
|---|---|---|---|---|---|---|
| RDT-C04-001 | EPUB（渲染/选区/标注/TTS/媒体叠加/嵌入字体/SVG 封面/可选 JS） | released ≤0.12.16 | 参考格式 | RN 0.7.9；`src-tauri/src/epub_parser.rs` ✓实测（218 页全链：TOC/脚注/图/选区标注/恢复/导出，ui-study §2/§3/§5） | 部分（差距：无 DRM EPUB3 最小 profile 已交付（ER：spine/TOC/图片/内链脚注/结构校验/安全拒绝）；章 XHTML→文本行+图片行，不保留 HTML/CSS/复杂表格/公式/竖排/嵌入字体（ER；§2 具名差距）；无 EPUB JS/媒体叠加） | |
| RDT-C04-002 | MOBI（打开/选区/标注/脚注/大文件） | released ≤0.12.16 | — | RN 0.9.82/0.9.63；`src-tauri/src/mobi_parser.rs` | 缺失（具名边界：导入分派仅 TXT/MD/EPUB（RL §EPUB 分派、ER「非 .epub 不进分派」）） | 真机无语料未测（ui-study §5） |
| RDT-C04-003 | AZW/AZW3（KF8） | released ≤0.12.16（Android 导入 0.9.76；乱码修复 0.12.6） | — | RN；`constants.ts:64-65` ✓实测（中文 AZW3 打开渲染，ui-study §5） | 缺失（同上：分派仅 TXT/MD/EPUB） | |
| RDT-C04-004 | FB2 | released ≤0.12.16 | — | `constants.ts:66`；docs（calibre 插件偏好 FB2） ✓实测（元数据+正文渲染，ui-study §5） | 缺失（同上） | |
| RDT-C04-005 | CBZ 漫画（+CBR 缩略图） | released ≤0.12.16 | ZIP 图片书为主分支（#7078） | `constants.ts:68`；`src-tauri/src/comic_parser.rs` ✓实测（7 页打开；目录=图片文件列表，ui-study §5） | 缺失（同上） | |
| RDT-C04-006 | PDF（渲染/缩放平移/选区标注/TTS/缩略图） | released ≤0.12.16 | pdfjs；扫描件选区 0.12.12；主题色 iOS/macOS/Safari 受限 | `src-tauri/src/pdf_parser.rs`；`public/vendor/pdfjs` ✓实测（69 页打开/缩略图/2-up/翻页/缩放/搜索；标注弹层未验证，ui-study §4） | 缺失（具名边界：无 PDF；§3 对标域） | |
| RDT-C04-007 | TXT（章节检测/嵌套 TOC/分段） | released（0.9.25→0.9.101） | — | RN；`constants.ts:70` ✓实测（「第X章」规则章切分正常，ui-study §5） | 部分（差距：TXT 导入/章切分/段模型/注释全链已交付（RL §3）；嵌套 TOC 未交付（TOC 扁平）） | |
| RDT-C04-008 | Markdown | released（0.11.17→0.12.1） | 数学 $/$$ 为主分支 | RN；`constants.ts:71` | 部分（差距：MD 导入+`#`/`##` 章切分已交付（RL §3）；MD 脚注/标题 TOC/数学未记载） | 真机未单独测（ui-study §5） |
| RDT-C04-009 | HTML/HTM/MHTML/MHT | released 0.12.10 | — | RN；`constants.ts:72-75` | 缺失（具名边界：分派仅 TXT/MD/EPUB） | 真机未单独测（ui-study §5） |
| RDT-C04-010 | DOCX/RTF 导入（静默转 EPUB） | 主分支候选（664b7dc34/#7050） | docs /docs/library 已记载（文档领先 tag） | `git show main` 664b7dc34；docs | 缺失（主分支候选，非发布面；AutoReader 亦未交付） | 不计入发布分母 |
| RDT-C04-011 | 有声书配对（MP3/M4A/M4B；M4B 章节表） | released 0.12.1 | 仅本地配对；EPUB 专属 | RN；`src/services/audiobook/`；`book-config.md:41-44`；docs | 缺失（具名边界：无 TTS/音频面；§3 对标域） | |
| RDT-C04-012 | 播客（Audiobookshelf；播客书架） | released 0.12.6 | ABS 服务器 | RN；`docs/bookshelves.md:9-13` | 缺失（服务面未交付；§3 C06 对标域） | |
| RDT-C04-013 | OPDS-PSE 流式打开 | released 0.11.1 | OPDS 服务器带 PSE | RN；`src/services/opds`（architecture.md:488）；docs | 缺失（§3 C06 对标域，未交付） | |
| RDT-C04-014 | ZIP 作为书籍容器 | released ≤0.12.16 | 无书 ZIP→报错为主分支 | `constants.ts:67`；docs | 待验证(未在Spec中记载)（zip natives 已交付（ER 依赖节）；书籍容器语义未记载） | |
| RDT-C04-015 | 格式能力矩阵（重排/固定/有声三档） | released ≤0.12.16 | — | RN 0.10.1/0.12.10；docs（配对 EPUB 专属） | 部分（差距：TXT/MD/EPUB 三格式能力口径已交付且经验收（RL/ER/SR，R-01..06 门）；PDF/MOBI/AZW/FB2/CBZ/HTML 未收编） | 本行为覆盖核对综合行 |

计数：15 行（1 行主分支候选 C04-010，不计已发布）；直属服务门 0（ABS 离线门记 C06）。

---

## 5. C05 深度与辅助阅读（39 行）

| ID | 能力 | 发布状态 | 平台/服务条件 | Readest 证据 | AutoReader 现状 | 差距与覆盖 |
|---|---|---|---|---|---|---|
| RDT-C05-001 | 词典弹窗查询（多源叠卡/词形还原/发音） | released（核心 ≤0.12.16；0.11.10→0.12.8） | — | RN；`annotator/DictionaryPopup.tsx`、`DictionaryResultsView.tsx`、`DictionarySheet.tsx` 入口在册(实测选区弹层词典入口，ui-study §3/§6) | 缺失（未交付；§3 C05 对标范围列名「查词/百科」） | |
| RDT-C05-002 | 维基百科/维基词典查询 | released ≤0.12.16 | 在线 | README；RN 0.9.100；`CustomDictionaries.tsx:118-121` 入口在册(实测，Wikidata 需网络，ui-study §6) | 缺失（同上；在线服务） | |
| RDT-C05-003 | 系统词典集成（macOS/iOS/Android） | released 0.11.2 | 不含 web/Windows/Linux；锁定其他源 | RN；`CustomDictionaries.tsx:452-457` | 缺失（同上） | |
| RDT-C05-004 | 本地词典导入（StarDict/MDict/DICT/SLOB/BGL） | released（0.11.1/0.11.2） | — | RN；`src/services/dictionaries/`（architecture.md:462-482）；docs | 缺失（同上） | |
| RDT-C05-005 | Yomitan 词典+便携 .rdict | released 0.12.6 | Worker 沙箱 | RN；README；`src/plugins/yomitan`；architecture.md:469-482 | 缺失（同上） | |
| RDT-C05-006 | 网页查词模板（%WORD%） | released ≤0.12.16 | — | `CustomDictionaries.tsx:386`；docs | 缺失（同上） | |
| RDT-C05-007 | AI 上下文词典 | released 0.12.12 | **Plus/Pro/完整自定义**；需自定义翻译端点 | RN；`CustomDictionaries.tsx:120,467-469`；docs | 缺失（未交付；§7 AI 服务依赖独立设计） | 服务门：付费+AI |
| RDT-C05-008 | 词镜（ruby 式注释/CEFR/语言包） | released 0.11.10 | 语言包按对下载；日韩泰不支持 | RN；`WordLensPanel.tsx`；docs | 缺失（未交付；§3 C05 对标范围） | |
| RDT-C05-009 | 多引擎翻译（DeepL/Google/Azure/Yandex） | released（0.9.49→0.12.1） | DeepL 服务端代理；每日配额 | `src/services/translators/providers/`；`src/pages/api/deepl/translate.ts`（architecture.md:325） 失败面实测(「翻译已禁用」态+弹层翻译入口，ui-study §6) | 缺失（未交付；§3 C05 列名「翻译」；§7 远程翻译独立设计） | 服务门：API key/配额 |
| RDT-C05-010 | 划句翻译（Ctrl+T/自动检测/逐书记忆） | released ≤0.12.16 | 配额 | docs；`commandRegistry.ts:595` | 缺失（同上；划词选区亦未交付（§2 具名差距）） | |
| RDT-C05-011 | 全书双语翻译（段内嵌/保留格式/显隐原文/TOC） | released（0.9.49→0.12.1） | DeepL 日配额（0.9.53） | RN；docs | 缺失（同上） | |
| RDT-C05-012 | 自定义翻译服务（OpenAI 兼容/自有 DeepL key） | released 0.12.12 | **Plus/Pro/完整自定义** | RN；`CustomTranslators.tsx`；`translators/custom/`；docs | 缺失（同上） | 服务门：付费 |
| RDT-C05-013 | 翻译提示词库 | released 0.12.12 | 随自定义翻译 | RN；`translators/custom/prompts.ts`；`LangPanel.tsx:213` | 缺失（同上） | |
| RDT-C05-014 | 朗读核心（句/段导航/后台播放/锁屏/车载） | released（0.9.2→0.12.12） | — | RN；`src/services/tts/`、`src/app/reader/components/tts/` ✓实测（本地免费面：朗读启动+播放条+章节时间，无需账号，ui-study §6） | 缺失（具名边界：无 TTS；§2 交付基线无朗读面；§3 对标域） | |
| RDT-C05-015 | 朗读引擎（Web Speech/系统/Edge 云/录音旁白） | released ≤0.12.16（0.9.56→0.12.8） | Edge 句集上送微软；native 仅 Android/iOS | `src/services/tts/{WebSpeechClient,NativeTTSClient,EdgeTTSClient}.ts`（architecture.md:438-444）；docs 入口在册(实测 WebView2 本地语音直读；Edge/自定义未配置缺证，ui-study §6) | 缺失（具名边界：无 TTS） | |
| RDT-C05-016 | Readest 精品语音 | released 0.12.16 | **Plus/Pro**；永不作默认引擎 | RN；`TTSController.ts:270-274,528`；docs | 缺失（具名边界：无 TTS；付费语音） | 服务门：付费 |
| RDT-C05-017 | 自定义语音服务（BYO OpenAI 兼容端点） | released 0.12.16 | **Plus/Pro/完整自定义** | RN；`CustomTTSServices.tsx`、`CustomTTSServiceEditor.tsx`；`TTSPanel.tsx:134,187-190` | 缺失（具名边界：无 TTS） | 服务门：付费（小米 MiMo 为主分支 #6863） |
| RDT-C05-018 | 朗读高亮（词/句级+样式） | released（0.9.91→0.11.2） | 词级计时需 Edge/WebSpeech | RN；`commandRegistry.ts:413`；docs | 缺失（具名边界：无 TTS） | |
| RDT-C05-019 | 朗读控制集（条/倍速/睡眠定时/A-B/逐句/歌词/逐书语音/双语/替换/跳括号） | released（0.9.31→0.12.12） | 配对有声书部分隐藏 | RN；`SpeedRuler.tsx`、`TTSLyricsView.tsx`；`TTSPanel.tsx:210-244`；docs | 缺失（具名边界：无 TTS） | |
| RDT-C05-020 | 离线音频下载（逐章/逐书/跨设备缓存同步） | released（0.11.20/0.12.6） | **Plus/Pro/完整自定义**门 | RN；`ttsDownloadManager`、`ttsDownloadStore`；`TTSPanel.tsx:247-276`；docs | 缺失（具名边界：无 TTS；语音包云同步为主分支 #7177） | 服务门：付费 |
| RDT-C05-021 | 跟读伴读（EPUB 3 媒体叠加） | released 0.12.1 | 需旁白 EPUB；无 seq 跳过 | RN；`src/services/tts/mediaOverlay/`；`docs/read-along-narration.md`；docs | 缺失（具名边界：无 TTS；ER 无媒体叠加记载） | |
| RDT-C05-022 | 有声书配对向导（锚章映射/ABS 源/解配） | released 0.12.1/0.12.16 | 配对仅本机 | RN；`AudiobookPairingDialog.tsx`；docs | 缺失（具名边界：无 TTS/音频面） | |
| RDT-C05-023 | 双书并行阅读（分屏） | released 0.7.9/0.9.62 | — | RN；README；`src/store/parallelViewStore.ts` 入口在册(实测书籍菜单「并排阅读」入口，ui-study §5) | 缺失（§3 对标域「对照阅读」，未交付） | |
| RDT-C05-024 | 阅读统计（时长/页数；跨设备+KOReader；服务端归档） | released 0.11.10 | 同步需账号；仪表盘 UI 为主分支 | RN；`ReadingStatsTracker.tsx`；`docs/stats-archive.md` | 缺失（未交付；§3 C05 列名「统计」） | |
| RDT-C05-025 | 阅读标尺 | released（主行 RDT-C02-052） | — | — | 待验证(未在Spec中记载) | 跨引行：见 C02-052 |
| RDT-C05-026 | 逐段阅读 | released（主行 RDT-C02-053） | — | — | 部分（差距：见 C02-053） | 跨引行：见 C02-053 |
| RDT-C05-027 | 速读 RSVP | released（主行 RDT-C02-054） | — | — | 待验证(未在Spec中记载) | 跨引行：见 C02-054 |
| RDT-C05-028 | 自动滚动 | released（主行 RDT-C02-055） | — | — | 待验证(未在Spec中记载) | 跨引行：见 C02-055 |
| RDT-C05-029 | 无障碍（全键盘/读屏/D-pad/WCAG AA） | released（0.9.80→0.10.4） | — | README；`PRODUCT.md:31-33`；RN；docs ✓实测(入口：全 ARIA 树语义完善——本文驱动即依赖其树；读屏播报未测，ui-study §7) | 缺失（§2 具名差距：辅助功能需调研） | |
| RDT-C05-030 | 界面本地化（34 语言+en=35） | released ≤0.12.16 | — | `i18n-langs.json`；`public/locales/`（35 目录）；RN | 待验证(未在Spec中记载) | |
| RDT-C05-031 | 应用锁（4 位 PIN+生物识别） | released 0.11.1/0.11.10 | PIN 盐化 PBKDF2 无恢复；生物识别仅移动 | RN；`AppLockScreen.tsx`、`AppLockDialog.tsx`；`appLockStore.ts`；docs | 待验证(未在Spec中记载) | |
| RDT-C05-032 | 外部查词应用（重置/URL 查词） | released ≤0.12.16 | — | `CustomDictionaries.tsx:343` | 缺失（查词域未交付） | |
| RDT-C05-033 | Hardcover 日志同步（进度+批注；二维码批准） | released（0.10.2→0.11.10） | 账号；QR 批准 | `src/services/hardcover/`；`HardcoverLinkDialog.tsx`；`src/app/api/hardcover/graphql` 入口在册(实测设置集成页在册，ui-study §6) | 待验证(未在Spec中记载)（第三方账号服务无 Spec 记载） | 服务门：第三方账号；自有 OAuth 为主分支（#7165） |
| RDT-C05-034 | Notion 批注镜像 | released 0.12.8 | 自有 Notion 集成+数据库 | RN；`NotionForm.tsx`；`constants.ts:136-145`（彩色引用为主分支 #7029） | 待验证(未在Spec中记载)（本地 MD 导出已交付（RA）；Notes/Jade 真实交接属 OS 协同、未交付（PD §2/§5）） | |
| RDT-C05-035 | AI 聊天助手（RAG；Ollama/网关/OpenAI 兼容） | code-only（生产禁用） | Settings AI 页生产禁用（`SettingsDialog.tsx:127`）；Notebook AI 页需 `aiSettings.enabled` | `src/app/api/ai/chat`、`src/app/api/ai/embed`；`src/services/ai/`；`AIPanel.tsx`；README 标 🛠 building | 缺失（AI 面未交付；§3 列为相邻功能核实项；§7 AI 服务依赖独立设计） | **不计入发布分母**；可达性未定（见 §7 不确定 2） |
| RDT-C05-036 | 朗读发音替换 | released 0.9.98 | — | RN | 缺失（具名边界：无 TTS；并入校对 TTS 面） | |
| RDT-C05-037 | 翻译跳过规则（pre/code/math 不动） | released 0.9.68 | — | RN | 缺失（翻译域未交付） | |
| RDT-C05-038 | 翻译配额提示 | released 0.9.55 | 账号 | RN | 缺失（翻译域未交付；无配额面） | |
| RDT-C05-039 | e-ink 渲染优化（FOUC 消除/闪屏抑制） | released（0.9.76→0.9.100） | e-ink | RN | 待验证(未在Spec中记载) | |

计数：39 行（4 行为 C02 跨引；C05-035 code-only **不计已发布**）；服务/账号门 6（C05-007、012、016、017、020 付费 + C05-033/034 第三方账号）。

---

## 6. C06 书源与传输（23 行）

| ID | 能力 | 发布状态 | 平台/服务条件 | Readest 证据 | AutoReader 现状 | 差距与覆盖 |
|---|---|---|---|---|---|---|
| RDT-C06-001 | OPDS 浏览/下载目录 | released（0.9.94→0.9.96） | — | RN；`src/app/opds/`、`src/services/opds/`；`src/app/api/opds/proxy` 入口在册(实测导入菜单「在线书库」入口，ui-study §6) | 缺失（§3 C06 对标域「书源」，未交付） | |
| RDT-C06-002 | OPDS 目录管理（增删改/子订阅存目录/同步/凭据加密同步） | released 0.10.6/0.11.1 | — | RN；`customOPDSStore`、`CatalogManager`；docs | 缺失（同上） | |
| RDT-C06-003 | OPDS 认证/自签 SSL/自定义头/HTTP Basic/Komga 兼容 | released（0.9.96→0.10.6） | — | RN；docs | 缺失（同上） | |
| RDT-C06-004 | OPDS 自动下载新书目 | released 0.11.1/0.11.18 | 逐目录开关 | RN；docs | 缺失（同上） | |
| RDT-C06-005 | OPDS-PSE 页流式 | released（主行 RDT-C04-013） | OPDS+PSE | — | 缺失（主行 C04-013） | 跨引行 |
| RDT-C06-006 | 精选 Standard Ebooks 目录 | released 0.9.96 | — | RN；docs | 缺失（同 C06-001） | |
| RDT-C06-007 | calibre 兼容（OPDS/Calibre-Web） | released ≤0.12.16 | — | README；RN 0.9.95/0.9.96 | 缺失（§3 C06 对标域） | |
| RDT-C06-008 | calibre 插件（推书+元数据+自定义列；配额检查） | released 0.11.18 | 插件 zip 从 GitHub Releases；云配额 | RN；docs（插件源位置未定位，见 §7 不确定 9） | 缺失（同上） | |
| RDT-C06-009 | KOReader 进度同步（推拉/策略/LAN 服务器） | released（0.9.71→0.9.86） | KOSync 账号 | RN；`src/services/sync/KOSyncClient.ts`；`src/pages/api/{sync,kosync}.ts`；`KOSyncForm.tsx`；`constants.ts:84-94` 入口在册(实测设置集成页在册，ui-study §6) | 缺失（同步域未交付；§3 C07 对标域） | |
| RDT-C06-010 | KOReader 书签/批注同步 | released（0.10.1→0.12.10） | — | RN；docs /docs/sync | 缺失（同上） | |
| RDT-C06-011 | Readest KOReader 插件（KOReader 内浏览书库/后台同步） | released（0.11.1→0.12.10） | 邮箱+密码登录 | RN；`apps/readest.koplugin/`（自带 gettext i18n，10 语言）；docs 入口在册(实测设置集成页在册，ui-study §6) | 缺失（同上） | QR 登录为主分支（#7186） |
| RDT-C06-012 | KOReader 统计同步 | released 0.11.10 | — | RN；`docs/stats-archive.md` | 缺失（同上） | |
| RDT-C06-013 | CrossPoint 插件（Xteink X3/X4；EPUB 下载/进度/统计） | released 0.12.12 | web.readest.com/link 审批码 | RN；docs /docs/crosspoint | 缺失（同上） | 服务门：Readest 账号 |
| RDT-C06-014 | BookOrbit（自托管 KOReader 协议服务器） | released 0.12.1 | 自托管服务器 | RN；`constants.ts:96-109`；`BookOrbitForm.tsx`；docs | 缺失（同步域未交付） | |
| RDT-C06-015 | Audiobookshelf（流媒体/电子书流/离线下载/配对/web 播放） | released（0.12.6→0.12.16） | ABS 服务器；自签经回环代理 | RN；`absServerStore`；`ABSForm.tsx`；`src-tauri/src/media_proxy.rs`；`absPairing.ts`；docs 入口在册(实测设置集成页在册，ui-study §6) | 缺失（服务面未交付；§3 C06 对标域） | 服务门：离线下载需付费（docs） |
| RDT-C06-016 | 附近书递 BookDrop（LocalSend 协议/可信配对/提示音） | released 0.12.6/0.12.8 | 同 LAN；可信配对 **Plus/Pro/完整自定义**；桌面+移动 | RN；`src/components/localsend/`、`src-tauri/src/localsend/`；`LocalSendForm.tsx`；docs | 缺失（未交付；§3 C06 列名「局域网传书」） | 服务门：可信配对付费 |
| RDT-C06-017 | 网页剪辑 | released（主行 RDT-C01-009） | — | — | 待验证(未在Spec中记载) | 跨引行：见 C01-009 |
| RDT-C06-018 | 网络小说导入 | released（主行 RDT-C01-010） | — | — | 待验证(未在Spec中记载) | 跨引行：见 C01-010 |
| RDT-C06-019 | Send to Readest 四通道 | released（主行 RDT-C01-011/012/013） | 邮件=付费 | — | 待验证(未在Spec中记载) | 跨引行：见 C01 |
| RDT-C06-020 | 书架「发送书文件」/分享面板直发 | released 0.11.4 | — | RN | 待验证(未在Spec中记载) | |
| RDT-C06-021 | 文件管理器/Files app/macOS 打开方式 | released（主行 RDT-C01-053） | — | — | 待验证(未在Spec中记载) | 跨引行：见 C01-053 |
| RDT-C06-022 | 链接抓取 | released（主行 RDT-C01-008） | — | — | 缺失（主行 C01-008） | 跨引行 |
| RDT-C06-023 | 后台传输队列（上传下载/提示音/队列面板） | released 0.9.97/0.12.8 | — | RN；`TransferQueuePanel.tsx`；`src/services/transferManager.ts` | 待验证(未在Spec中记载) | |

计数：23 行（5 行跨引）；服务/账号门 3（C06-015 ABS 离线付费、C06-016 可信配对付费、C06-013 账号；C06-014 自托管条件）。

---

## 7. C07 同步与生态（39 行）

| ID | 能力 | 发布状态 | 平台/服务条件 | Readest 证据 | AutoReader 现状 | 差距与覆盖 |
|---|---|---|---|---|---|---|
| RDT-C07-001 | Readest 云账号同步（书/进度/笔记/书签） | released（0.8.5/0.9.8） | Readest 账号 | RN；`src/services/cloudService.ts`；`src/pages/api/storage/*` 失败面实测(未登录态「登录以同步书库」；共享 profile 会话继承实证云下载确会发生，ui-study §6/§0) | 缺失（§3 C07 对标域「同步」，交付基线无云面（§2）） | 服务门：账号 |
| RDT-C07-002 | 副本同步（增量/口令加密/逐类适配器） | released ≤0.12.16 | 口令门；无恢复 | `src/services/sync/`（architecture.md:386-396）；`SyncPassphraseSection.tsx` | 缺失（同上） | |
| RDT-C07-003 | 同步分类开关 | released ≤0.12.16 | 凭据选入+E2E 加密 | docs；`SyncCategoriesSection.tsx` | 缺失（同上） | |
| RDT-C07-004 | WebDAV 同步 | released 0.11.17（0.12.10/0.12.16 可靠性） | **第三方同步=Plus/Pro/完整自定义** | RN；`WebDAVForm.tsx`；`constants.ts:147-159`；docs 入口在册(实测设置集成页在册，ui-study §6) | 缺失（同上） | 服务门：付费 |
| RDT-C07-005 | Google Drive 同步 | released 0.11.17 | 同上 | RN；`IntegrationsPanel.tsx:539+`；docs | 缺失（同上） | 服务门：付费 |
| RDT-C07-006 | OneDrive 同步 | released 0.11.20 | 同上；自有 MS client id | RN；`OneDriveForm.tsx`、`buildOneDriveProvider` | 缺失（同上） | 服务门：付费 |
| RDT-C07-007 | S3 兼容同步（S3/R2/MinIO） | released 0.11.18 | 同上；web 需 CORS | RN；`S3Form.tsx`；docs | 缺失（同上） | 服务门：付费 |
| RDT-C07-008 | iCloud Drive 同步 | released 0.12.1 | Apple 平台+entitlement | RN；`ICloudForm`（IntegrationsPanel 子页） | 缺失（同上） | |
| RDT-C07-009 | 多供应商并行/策略/立即同步/同步信息对话框 | released（0.11.20→0.12.8） | — | RN；`IntegrationsPanel.tsx:539-560`；`FileSyncReport.tsx`、`SyncInfoDialog.tsx` | 缺失（同上） | |
| RDT-C07-010 | 第三方同步付费门槛（Premium 徽章/配额暂停） | released ≤0.12.16 | **Plus/Pro/一次性完整自定义 $19.99** | docs /pricing；`resolveCloudSyncGate`（`IntegrationsPanel.tsx:543+`）；`src/app/user/utils/plan.ts:47` | 排除（需裁定来源）（付费云服务需独立界定（设计文档 §1）；本地优先） | 服务门本身即本行对象 |
| RDT-C07-011 | KOSync 进度同步 | released（主行 RDT-C06-009） | — | — | 缺失（主行 C06-009） | 跨引行 |
| RDT-C07-012 | Hardcover 同步 | released（主行 RDT-C05-033） | — | — | 待验证(未在Spec中记载) | 跨引行：见 C05-033 |
| RDT-C07-013 | Readwise 导出（含书签；自托管 URL） | released（0.9.101→0.12.10） | 自有 Readwise token | RN；`constants.ts:111-118`；`ReadwiseForm.tsx`；docs | 待验证(未在Spec中记载)（本地 MD 导出已交付（RA）；第三方导出无 Spec 记载） | |
| RDT-C07-014 | Pagebound 同步（进度+状态） | released 0.12.12 | Pagebound 账号；桌面/移动 | RN；`constants.ts:127-134`；`PageboundForm.tsx`；`PageboundLinkDialog.tsx`；docs 入口在册(实测设置集成页在册，ui-study §6) | 缺失（同步域未交付） | 服务门：第三方账号；笔记不同步 |
| RDT-C07-015 | Audiobookshelf 集成 | released（主行 RDT-C06-015） | — | — | 缺失（主行 C06-015） | 跨引行 |
| RDT-C07-016 | CrossPoint 插件 | released（主行 RDT-C06-013） | — | — | 缺失（主行 C06-013） | 跨引行 |
| RDT-C07-017 | 书架+分组同步 | released 0.12.6/0.12.10 | 账号 | RN；`docs/bookshelves.md:121-161` | 缺失（无云面） | |
| RDT-C07-018 | 自定义字体同步+云端按需下载 | released 0.11.1/0.12.16 | 账号 | RN 0.12.16 | 缺失（无云面） | |
| RDT-C07-019 | 自定义主题同步（含编辑） | released 0.9.37/0.12.16 | 账号 | RN | 缺失（无云面） | |
| RDT-C07-020 | 词典/纹理/OPDS 目录同步 | released 0.11.1 | 账号 | RN | 缺失（无云面） | |
| RDT-C07-021 | 阅读统计同步+服务端归档分层 | released ≤0.12.16 | 账号；服务端子系统 | `docs/stats-archive.md`；`src/pages/api/sync.ts` type=stats | 缺失（统计域+云面均未交付） | |
| RDT-C07-022 | 冲突处理（逐字段 LWW 戳/tombstone/单向自动进度/笔记合并/游标增量） | released ≤0.12.16（0.12.12/0.12.16 修复） | — | RN；`docs/bookshelves.md:145-160`；docs | 缺失（多端冲突合并未交付；本地写完整性协议（verified_write/refuse-to-load，RL §2）不构成冲突合并） | 共享合并规则重构为主分支（#6843） |
| RDT-C07-023 | 离线 Web 应用（PWA+service worker） | released 0.9.7 | web 应用 | RN；`src/sw.ts`（architecture.md:252-256）；`public/manifest.json` | 待验证(未在Spec中记载)（本地优先已记载（SR/设计文档 §7）；PWA 面未记载） | |
| RDT-C07-024 | 自托管 Docker 镜像+运行时配置重品牌+固定配额 | released 0.9.17/0.9.30 | 自托管 | RN；`docker/`；`src/app/runtime-config.js/route.ts`（architecture.md:363-371,605-611） | 待验证(未在Spec中记载) | |
| RDT-C07-025 | 自托管 KOSync 兼容服务端 | released ≤0.12.16 | 自托管 | `src/pages/api/sync.ts`、`src/pages/api/kosync.ts`（architecture.md:309-311） | 待验证(未在Spec中记载) | |
| RDT-C07-026 | 账户体系（邮箱+Google/GitHub/Apple/Discord OAuth；改邮箱/重置/注销含存储清除） | released（0.8.9→0.12.16） | Supabase auth | RN；`src/app/auth/`；`src/pages/api/user/delete.ts`；`src/app/api/auth` | 缺失（无账号体系；同步域未交付） | |
| RDT-C07-027 | 订阅分层（Free/Plus $4.99/Pro $9.99；存储/AI 翻译/DeepL 配额/精品语音） | released ≤0.12.16（0.9.62 订阅管理） | Stripe+IAP | docs /pricing；`src/app/user/`；`src/app/api/stripe/*`；`src/app/api/{google,apple}/iap-verify` | 排除（需裁定来源）（付费云体系需独立界定，设计文档 §1） | |
| RDT-C07-028 | 一次性买断（存储包/完整自定义 $19.99） | released ≤0.12.16（0.9.90 存储 IAP） | 移动 IAP/web Stripe | docs；`src/app/user/utils/plan.ts`；`Quota.tsx` | 排除（需裁定来源）（同上） | |
| RDT-C07-029 | 配额体系（存储/翻译/token/自定义） | released ≤0.12.16 | 账号 | `src/types/quota.ts:20` | 排除（需裁定来源）（随付费云体系裁定） | |
| RDT-C07-030 | 应用自更新（桌面/Android/AppImage/nightly 通道） | released（0.8.2→0.11.10） | deb/rpm/Flatpak 除外 | RN；`UpdaterWindow.tsx`；`src/app/updater/`；`src-tauri/src/nightly_update.rs` | 待验证(未在Spec中记载) | |
| RDT-C07-031 | 遥测与崩溃上报（匿名统计+Sentry；同意对话框+可退） | released 0.9.49 | 文档称默认关；代码默认 `telemetryEnabled: true`（矛盾） | `TelemetryConsentDialog.tsx`；`src/utils/telemetry`；`src-tauri/src/sentry_config.rs`；`docs/sentry-symbolication.md` | 待验证(未在Spec中记载)（Readest 侧默认值矛盾见 §7 不确定 1） | |
| RDT-C07-032 | Discord Rich Presence | released 0.9.98 | desktop；选入 | RN；`src-tauri/src/discord_rpc.rs`；`constants.ts` | 待验证(未在Spec中记载) | |
| RDT-C07-033 | 分享落地页+匿名只读 web 渲染 | released ≤0.12.16 | — | `src/app/s/`、`src/app/o/`；`src/app/api/share/*`（architecture.md:353） | 待验证(未在Spec中记载) | |
| RDT-C07-034 | 网页版（web.readest.com+PWA 安装） | released 0.8.2 | — | RN；README | 待验证(未在Spec中记载)（双 profile 本地启动已交付（SR）；公开网页托管面未记载） | |
| RDT-C07-035 | 按设备视图设置不同步 | released 0.11.12 | — | RN | 待验证(未在Spec中记载) | |
| RDT-C07-036 | 云端清理（查看/删除云文件；删全部；注销清除） | released（0.9.95→注销路径） | 账号 | `docs/stats-archive.md:311-327`；`user/delete.ts` | 缺失（无云面；本地可恢复移除/备份读回已交付（RL §4/§2）） | |
| RDT-C07-037 | 回前台进度刷新；续读上次页面（iOS 后台恢复） | released 0.12.10/0.9.90 | — | RN | 部分（差距：本地恢复（锚核验+滚动定位，RL §5）已交付；跨端刷新未交付） | |
| RDT-C07-038 | 移动端缓存管理 | released（主行 RDT-C01-044） | — | — | 待验证(未在Spec中记载) | 跨引行：见 C01-044 |
| RDT-C07-039 | 文件 provider 同步布局（library.json+封面+配置入 WebDAV/GDrive/S3/OneDrive/iCloud） | released ≤0.12.16 | — | architecture.md:396-403；`src/services/sync/file/` | 缺失（同步域未交付） | 朗读包经此同步为主分支（#7177） |

计数：39 行（5 行跨引）；服务/账号门约 12（C07-004~010 第三方同步付费门、C07-027/028 付费层、C07-001/002/017~021 账号、C07-024/025 自托管条件）。

---

## 8. C08 AutoOS 知识流（1 行，不计入 Readest 分母）

Readest 无此域；本行是 AutoReader 侧的输出面对照，**不计入发布分母**。

| ID | 能力 | 发布状态 | 平台/服务条件 | Readest 证据 | AutoReader 现状 | 差距与覆盖 |
|---|---|---|---|---|---|---|
| RDT-C08-001 | Notes/Jade 交接（带原文、稳定来源与附件的知识流写入） | —（非 Readest 对标项） | AutoOS 公共通信/DevTools（RFC 落地状态执行时核验） | —（Readest 以 Readwise/Notion 等第三方导出替代，见 C05-034/C07-013） | 缺失（未交付：Notes 真实交接/离线待发/幂等回执属 B 阶段，尚未实现且不在 Spec 宣称（RA 头部）；交接属 OS 协同（设计文档 §2/§5）） | 本地 Markdown 导出已交付（RA）作为独立离线能力；不把未交付系统服务作为本地读书前置 |

---

## 9. 主分支候选（NOT in published v0.12.16，不计入分母）

经 `git -C D:/autostack/readest log v0.12.16..main`（183 提交，以修复为主）核实的功能级条目：

| 候选能力 | 提交（#PR） | 证据/备注 |
|---|---|---|
| DOCX/RTF 导入（静默转 EPUB） | 664b7dc34（#7050） | docs /docs/library 已记载——文档领先 tag |
| 阅读统计仪表盘 | c416bf537（#6986） | README 仍标 🛠 building |
| `.rbooks` 集合打包导出/导入 | 411c29159（#6945） | 新文件格式 |
| 粘贴文本导入书库 | 5da26ee82（#6992） | |
| 原生纸感翻页卷曲（iOS #7046；Android #7001） | f-curls | tag 内仅有 JS 卷曲动画 |
| 「Page Flip」翻页样式（全平台） | 145e3318d（#7160） | 新动画类型 |
| 进度滑杆拖动时的页面预览 | da0a1c328（#7110） | |
| 按真实屏幕计数校准页码读出 | af07e0f1c（#7060） | |
| 书架逐书架「标题下页数」选项 | df5070af0（#7142） | |
| iPhone Duo 内屏书本模式 | 454ae3cbb（#7137） | |
| 自定义 TTS：音频格式+语音清单配置 | a8efa756d（#7155） | |
| 小米 MiMo chat-completions 语音 | ce1e5f1d7（#6863） | |
| 朗读离线包云同步+文件同步后端 | a952e082a（#7177）、bc7a5bfa5（#7190）、71058528e（#7176） | |
| 自签证书逐服务器开关 | aa92eb1b9（#6822） | |
| KOReader 插件 QR 登录+登出修复 | 314a62d11（#7186） | |
| Hardcover：经 Readest 自有 OAuth 登录；日志去重 | ad42d7c4f（#7165）、02f5f5509（#7162） | |
| Notion：彩色高亮引用+批注 callout+模板 | 5b379836f（#7029）、4eb992a44（#7031） | |
| 桌面端缓存管理 | 032a292e8（#7066） | |
| 缩放后 PDF 页缘滑动翻页 | 3e912625c（#7175） | |
| 图片 ZIP 作为漫画打开 | f1e1836d0（#7078） | |
| Markdown 书内数学（$, $$） | 81c76a4ae（#6887） | |
| PDF TTS：按页语言朗读；跨行/连字符断词 | f1602f1ea（#6944）、87071ccc3（#6955） | |
| KOSync xpointer 修复（crengine 形态；MOBI/FB2/ABS id） | fc624e838（#7172）、8005ff9af（#6951）、2d37bbfc2（#6905）、cf2fdf0cb（#7161） | |
| 书库悬停显示完整题名/分组题名 | ac68bf83b（#6785） | |
| e-ink 覆盖层总遮罩开关 | 87a217025（#6922） | |
| e-ink 设备身份白名单收紧（+CI 守卫） | d66e11071（#6833）、61ef15e0 | |
| 嵌套/长引语对话高亮 | e82f0c0f4（#6814） | |
| 笔记本/文档+同步引擎重构（笔记合并跨 provider 共享） | f06483d24（#6843） | |
| 网络小说章节检测：传统单元「第N頁」 | d4c630419（#7107） | |
| 书籍标记净化后于应用窗口渲染 | 10eef9764（#6815） | 安全加固 |
| 自签服务器深链/重定向加固 | 23b8dd5b5?（#6931）、2cb8c0df2（#6821） | 安全 |

（`git show main:apps/readest-app/release-notes.json` 无新于 0.12.16 的条目；main README Planned 表未变。以上一律不得计为已发布。）

---

## 10. 初始清单之外的新发现（24 项）

1. **浏览器扩展面**（Send to Readest）——独立交付物 `apps/readest-app/extension/send-to-readest`（architecture.md:21）。
2. **Windows 缩略图 shell 扩展**——`apps/readest-app/extensions/windows-thumbnail`（architecture.md:23）。
3. **CLI 调用**——Tauri `cli` 插件；0.8.8 "readest binary name for better CLI interface"（RN 0.8.8；architecture.md:557）。
4. **深链** `readest://` + 分享落地路由 `/s`、`/o`（RDT-C01-052、C07-033）。
5. **自托管 KOSync 服务端端点**——跑 Readest 后端即得 KOReader 兼容同步服务器（C07-025）。
6. **统计归档子系统**——服务端把阅读统计压缩到 R2，含恢复工具与注销 tombstone（`docs/stats-archive.md`）。
7. **AI 子系统在库、生产隐藏**——`/api/ai/chat`、`/api/ai/embed`（RAG 嵌入，书域），`aiChatStore`，Notebook AI 页由 `settings.aiSettings.enabled` 门控；Settings AI 页生产禁用（`SettingsDialog.tsx:127`）。README 标 🛠。按未发布处理（C05-035）。
8. **氛围彩蛋**——视频叠加+环境音主题模式（RN 0.10.2；`AtmosphereOverlay.tsx`）。
9. **示例书**——首启按语言自动导入示例书库（web）（`useDemoBooks.ts`）。
10. **回环媒体代理**——`src-tauri/src/media_proxy.rs`：经本地代理播放 Audiobookshelf/自签音频（read-along 文档 #6216）。
11. **jieba-wasm 中文分词**与 **simplecc-wasm** 变体转换为引擎级能力（architecture.md:248-250）。
12. **e-ink 设备身份白名单**——原生 `eink_identity.rs` 决定自动 e-ink 模式；漂移守卫 CI 为主分支。
13. **词典插件 Worker 沙箱**——宿主中介 SQL/词源访问、完整性校验分代、`.rdict` 便携格式+转换 CLI `pnpm dictionary:yomitan:convert`（architecture.md:469-482）。
14. **KOReader 伴生插件作为在树应用**——`apps/readest.koplugin`，自带 gettext `.po` i18n 管线（10 语言）。
15. **Google Play MANAGE_EXTERNAL_STORAGE 声明**——全存储访问作为已发布权限（`docs/google-play-all-files-access.md`）。
16. **TTS 音频缓存+跨设备缓存同步+存储上限**——`TTSPanel.tsx:247-276`。
17. **minisign 签名发布校验**（每下载配 .sig；docs /docs/advanced）——分发信任能力。
18. **Nightly 更新通道**——选入早期构建（RN 0.11.10；`nightly_update.rs`）。
19. **Windows 资源管理器预览面板 Alt+P**（docs /docs/advanced）。
20. **语言覆盖徽章**——README「53% of world population」宣传口径。
21. **i18n 广度**：34 UI 语言 + en = 35（`i18n-langs.json`、`public/locales/`）；键即内容的 i18n 体系（`docs/i18n.md`）。
22. **口令门副本同步零恢复**——有意的数据损失权衡且有文档（docs /docs/sync）。
23. **`docs/superpowers/specs|plans`**——仓内设计文档（阅读标尺、nightly 通道、KOReader 统计、Hardcover 自动同步、批注分享工具栏、TTS-RSVP 同步、手势亮度）——其描述的已交付能力均计入域表。
24. **沙箱加固**——`src-tauri/src/lib.rs` 的 `allow_paths_in_scopes` 门（仅用户挑路径；architecture.md:567-573）；网络小说导入/捕获拒私有 IP 的 URL 守卫（architecture.md:545-551）。

---

## 11. 计数与目标建议

### 11.1 分域发布计数（承 T-01 清单 §10）

| 域 | 行数 | 其中服务/账号门 | 备注 |
|---|---|---|---|
| C01 文件与书库 | 55 | 4（邮件地址通道、分享配额、在线元数据、Goodreads） | |
| C02 阅读与排版 | 60 | 0 | 含 5 行专注辅助，被 C05 跨引 |
| C03 选区、标注与定位 | 28 | 0 | |
| C04 多格式 | 15 | 0 直属（ABS 离线门记 C06） | 含 1 主分支行（C04-010），不计已发布 |
| C05 深度与辅助阅读 | 39 | 6（上下文词典、自定义翻译、Readest Voice、自定义 TTS、离线音频 + 第三方账号 Hardcover/Notion） | 4 行为 C02 跨引（不重复计入总数）；C05-035 code-only 不计已发布 |
| C06 书源与传输 | 23 | 3（ABS 离线下载、BookDrop 可信配对、CrossPoint 账号） | 5 行跨引 |
| C07 同步与生态 | 39 | ~12（第三方 provider 多在 Plus/Pro/完整自定义之后；分层/IAP；账号同步类） | 5 行跨引 |
| **合计** | **259 行** | **~25（≈10%）** | |

### 11.2 分母数学

- 全部行 259（含 1 行主分支候选 C04-010、1 行 code-only C05-035）。
- **已发布分母：257** = 259 − 2，逐行点名：C04-010（DOCX/RTF，主分支候选 664b7dc34/#7050）、C05-035（AI 助手，code-only 生产禁用）。全表其余 257 行均为 released ≤0.12.16 状态（T-08 复审 RV-D03 修正：起草期建议的 255 系清单阶段宽估，未获逐行支撑，废止）。
- 主分支候选（§9，31 条功能级条目）与 C08 永不进入分母。
- **本文件不宣称任何覆盖百分比**：计数分母/权重/目标阈值在调研收口提出依据（设计文档 §1），不预先宣称比例，不靠拆细或删难项改成绩。

### 11.3 AutoReader 现状分布（本矩阵映射结果，非覆盖率）

| 域 | 完整 | 部分 | 缺失 | 待验证 | 排除 |
|---|---|---|---|---|---|
| C01 | 1 | 9 | 22 | 23 | 0 |
| C02 | 0 | 11 | 10 | 39 | 0 |
| C03 | 0 | 10 | 4 | 14 | 0 |
| C04 | 0 | 4 | 10 | 1 | 0 |
| C05 | 0 | 1 | 31 | 7 | 0 |
| C06 | 0 | 0 | 17 | 6 | 0 |
| C07 | 0 | 1 | 22 | 12 | 4 |
| **合计** | **1** | **36** | **116** | **102** | **4** |

说明：`待验证` 密集区（C02 手势/平台面、C05 服务面外围、C06/C07 跨引与平台运维面）即 Spec 静默区，是后续 AutoReader 侧盘点（而非 Readest 侧调研）的输入。

### 11.4 核心任务验证状态

- **核心日用链路已在真机跑通（Readest 侧）**：导入→阅读→选区标注→搜索→关闭重开恢复→导出 全链实测通过，定位/标注以 EPUB CFI 字符偏移为锚（[ui-study](ui-study.md) §3「核心任务全绿」；AutoReader 对照锚 = 章+段+逐字全文锚）。
- **服务门面缺证具名**：翻译成功面（DeepL/Yandex 需服务端 key）、Readest Voice/自定义语音（付费+未配置）、云同步成功面（需账号；仅未登录失败面实测）、OPDS 目录（未配置）、KOReader/WebDAV/Audiobookshelf/Pagebound/Hardcover（集成页在册，缺账号/缺服务）——一律以「入口在册/失败面实测」登记，不冒充成功面证据。
- **AutoReader 侧对应核心任务**：三格式导入→注释/搜索/导出/恢复全流程已有双端验收门（verify_local vue 50/50、verify_standalone vue 28/vm 27、原生驱动 37 records；Spec RA/SR 永久入口）。

---

## 12. 不确定与待验证

**承 T-01 清单 §11（上游侧）**：

1. **遥测默认值矛盾**：docs 称默认关；代码 `constants.ts:234` `telemetryEnabled: true` + 同意对话框。全新安装实际时序需运行期核实。
2. **AI 助手可达性**：AIPanel 生产禁用；Notebook AI 页需 `aiSettings.enabled`；tag 内未见翻转 UI。可能远程配置或仅自托管。已排除出发布计数。
3. **README Planned 表过期**：「Handwriting 🔄 planned」与 RN 0.12.16 手写交付矛盾；「Advanced Reading Stats 🛠」与 0.11.10 统计交付矛盾。以 RN+代码为准。
4. **文档站领先 tag**：/docs/library 已载 DOCX/RTF（主分支 #7050）；FBZ 直提未在 tag `SUPPORTED_BOOK_EXTS`。
5. **`docs/page-curl.md` 在该 tag 不存在**（13 篇 md，非 15）；page-curl 证据改用 RN 0.11.18 + `ControlPanel.tsx`。
6. **Word Lens 付费门未核实**：定价页未列；语言包是否部分 Pro-only 未验证。
7. **逐格式标注证据**：MOBI/AZW3/FB2 选区标注由共享 foliate-js 引擎+RN 笼统表述支撑，属「按架构核实」，非逐格式明文。
8. **「≤0.12.16」引入版本不可考**：早于 0.7.9 或从未入 RN 的能力无法定版本。
9. **calibre 插件源位置未定位**：docs 说从 GitHub Releases 下载 zip；本检出只找到 koplugin。
10. **PDF 主题色平台限制**仅来自 docs（iOS/macOS/Safari），未在代码核实。
11. **TTS 高亮样式集**：docs 列 5 式；`types/book.ts:30` HighlightStyle 为 3 式（批注用）；TTS 专属样式未单独核实。
12. **付费门逐调用点执行细节**：门逻辑在 IntegrationsPanel 核实；逐特性强制（如 ABS 离线免费拒）取自 docs/pricing。
13. **示例书范围**：web 平台 URL 导入核实；原生构建是否亦播种未验证。
14. **App Store/Play 商店页、wiki、GitHub Releases 页未查**（仓内清单范围外）。
15. **`docs/testing.md`、`safe-area-insets.md`** 仅作基础设施文档读，未提能力行。
16. **Webtoon/RTL/逐段模式的精确格式矩阵**未逐格式核实（RN 仅言「comics and fixed-layout books」）。

**承 [ui-study](ui-study.md)（真机侧未验证项）**：

17. **PDF 标注弹层未触发成功**（CDP 拖选路径；PDF 文本层在 shadow-DOM 内）——PDF 标注链路缺真机证。
18. **书签顶栏按钮点击未生效**（侧栏路径正常）——待复核。
19. **移除确认对话复验一次未生效**（疑确认层拦截）——复审须重验。
20. **MOBI/MD/HTML 未入语料实测**（MOBI 无可生成语料；MD/HTML 同文本管线家族未单独打开）——代码证据在 [code-map](code-map.md)。

---

*本文件为 READER-006 耐久交付物；行 ID、证据与计数承 T-01 清单（仓外 `plan-artifacts/plan-006/notes/t01-inventory.md`），真机标记承 ui-study。AutoReader 现状列以四份 reader Spec 与设计文档 §2 为唯一来源，未记载处一律记待验证，不做推断。*
