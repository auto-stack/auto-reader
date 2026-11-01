# Readest 调研基线（READER-006 T-00）

状态：fixed · 2026-11-01。本文件固定 READER-006 全部研究的上游发布、源码、文档与实际 UI 身份。后续报告（capability-matrix / code-map / ui-study / decisions / report）引用本基线；证据原文在仓外 `D:/autostack/plan-artifacts/plan-006/`。

## 1. 开发位（本 app）

| 项 | 值 |
|---|---|
| 检出 | `D:/autostack/auto-reader`（独立 clone，main；计划 §2 指定开发位，无 app worktree） |
| 基线提交 | 计划 base = `0a296b39f84ce1d741511413a5eec9d3cd0225f0`；T-00 执行时 HEAD = `d39c255806ae31af41b1fcda362f9bacc83cdd88`（006 计划提交） |
| 工作区状态 | `git status --short --branch` → `## main...origin/main [ahead 1]`、无文件改动（clean；ahead 1 即 006 计划本身，未推送属正常） |

## 2. 上游源码基线（Readest）

| 项 | 值 |
|---|---|
| clone 前检查 | `D:/autostack/readest` **不存在**（2026-11-01 实查），按计划从官方源新建 |
| clone 命令 | `git clone https://github.com/readest/readest.git D:/autostack/readest` → exit 0，4563 文件 |
| main HEAD（克隆时点） | `9907b1dd5221f288d37ad70ba290f34a57bbc7ad`（2026-11-01 08:30 +0100） |
| 工作区状态 | `git status --short` → 空（clean，exit 0） |
| **发布基线（主分母）** | tag **v0.12.16** = commit `3cc39ad7a558e6612e1a8135058fbd6f3c90b3e3`（2026-10-14 00:33 +0200，"release: version 0.12.16 (#6779)"） |
| main 相对发布基线 | v0.12.16 是 main 祖先；`git rev-list --count v0.12.16..main` = **183**（主分支新增能力另列候选，不混入已发布分母） |
| GitHub latest release | v0.12.16（API `releases/latest` 实查 2026-11-01，published 2026-10-13T22:34Z，非 prerelease） |

### 子模块（**以发布 tag v0.12.16 的 gitlink 为准**；已按固定提交检出，标 ✅；未检出不标）

研究检出已切到 tag：`git checkout --detach v0.12.16` → HEAD `3cc39ad7`（exit 0）；随后 `git submodule update --init <同下表 7 项>` → exit 0，`git status` clean。**tag 与 main 的 gitlink 差异实证**：foliate-js tag=`3d79419` ≠ main=`0c7a0edc`；webview-upgrade tag=`c7f9774b` ≠ main=`c861233a`（主分支差异另列，不混入发布证据）。

| 路径 | tag v0.12.16 固定提交 | 备注 |
|---|---|---|
| packages/foliate-js | `3d7941954a98b136316a795e8200d60c9643b141` | ✅ 已检出（文档引擎，code-map 必需；Readest fork） |
| packages/js-mdict | `d01bf62af872b1fbeacb2f18446460960e7400de` | ✅ 已检出（MDict 词典；tag 与 main 同值） |
| packages/simplecc-wasm | `5e5b56f5b82394e7df07f9171ac70f4578b24a32` | ✅ 已检出（CJK 转换；其内嵌 OpenCC 子模块 `e0d41d7f…` 未检出，分析不需要） |
| packages/qcms | `fc23a407f1ed9ccfea15875d27e0936dcc798a1f` | ✅ 已检出（pdf.js qcms 色彩管理） |
| packages/tauri | `382ea858bdd29458a5447e49c401b3ac64f0c3c0` (readest 分支) | ✅ 已检出（**Readest fork 的 Tauri**，平台桥分析必需） |
| apps/readest-app/src-tauri/plugins/tauri-plugin-turso | `3c4be4fd92fbe11e8e374b6e8e85dbf9a3b1b4ac` | ✅ 已检出 |
| apps/readest-app/src-tauri/plugins/tauri-plugin-webview-upgrade | `c7f9774b0396e32280108fa6c8ee3b1a971df5fc` | ✅ 已检出（tag 值；main 已前移至 `c861233a`） |
| apps/readest-app/.claude/skills/gstack | `e3259400…`（- 前缀） | ❌ 未检出（Claude 技能目录，非产品/构建必需，依计划"分析/构建所需"条款排除并在此登记） |

## 3. 文档固定源与访问日期

| 源 | 访问日期 | 固定方式 |
|---|---|---|
| 仓库内文档（权威源码快照） | 2026-11-01 | 按 tag v0.12.16 检出读取：`README.md`（Features/Planned 表）、`apps/readest-app/PRODUCT.md`、`apps/readest-app/docs/*.md`（architecture/code-layout/view-settings/bookshelves/book-config/read-along-narration 等 15 篇）、`apps/readest-app/release-notes.json`（版本历史一手源） |
| 官方文档站 readest.com/docs | 2026-11-01 | Web 快照（capability-matrix 记录具体页与日期）；与仓库内文档冲突时以 tag 内文档为准并记差异 |
| GitHub Releases API | 2026-11-01 | `releases/latest` JSON（asset 名单/大小）+ `release-notes.json`（tag 内，随源码 hash 固定） |

## 4. 实际 UI 构建身份

| 项 | 值 |
|---|---|
| 版本/平台 | **Readest 0.12.16，Windows x64**（与源码基线同一 tag v0.12.16 —— 版本对应关系成立，见 §6 边界） |
| 来源 | 官方 GitHub Release 资产 `Readest_0.12.16_x64-portable.exe`（browser_download_url 实录于 plan-artifacts） |
| SHA256 | `683a620d4ee883c2d15c500cbe0ca82e42900510276e557df33289e3b7265f74` |
| 大小 | 92,852,224 字节 |
| 隔离运行目录 | `D:/autostack/plan-artifacts/plan-006/ui/readest-portable/`（exe 拷贝 + 同目录空 `Settings.json` 触发 portable 模式） |
| 隔离机制（源码证据） | `apps/readest-app/src/services/nativeAppService.ts:162-215`（v0.12.16 tag 内）：exe 目录存在 `Settings.json` → Settings/Data/Books/Fonts/Images/Dictionaries/Log 全部以 exe 目录为根（baseDir=0），不落用户 AppData |
| 自动化面 | Windows 标准构建为 WebView2（本机既有 `%LOCALAPPDATA%/com.bilingify.readest/EBWebView` 佐证）；`READEST_CDP_PORT` 仅 CEF 构建（`src-tauri/src/lib.rs:635`）；WebView2 观察可用 `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port`（T-03 实证后记录） |

### 隔离边界与既有数据保护（重要）

本机存在**真实用户 Readest 数据**，研究全程不触碰：

- `%APPDATA%/com.bilingify.readest/`：3295 文件 / **3.8 GB**（`Readest/Books`、`localsend`；2026-11-01 运行前快照）。
- `%LOCALAPPDATA%/com.bilingify.readest/`：1695 文件 / 139 MB（EBWebView 即 WebView2 配置）。

portable 模式隔离上述两者的 Settings/Data/Books/Log 写入；**已知残留边界**：`Cache` base 仍指向 `BaseDirectory.AppCache`（`nativeAppService.ts:200-204`），即缓存类写入仍落 `%LOCALAPPDATA%` 既有目录——T-03 运行后按快照核对增量并在 ui-study.md 登记实际差异；不清理、不回滚用户目录。

## 5. 构建路线裁定

**不执行源码构建**：官方发布二进制与源码基线同为 v0.12.16，已满足"可核验的桌面官方发布版"（计划 §2 优先项）。Tauri/Rust/pnpm 全链构建仅在发布二进制无法覆盖某观察面时按需补做，届时另记命令与环境。Web（web.readest.com）只作补充证据，不替代桌面结论。

## 6. 版本对应关系与无法建立的对应

- **可建立**：UI 二进制 = 官方 release v0.12.16 资产；源码分析基线 = 同 tag 提交 `3cc39ad7`。两者由发布 tag 对应，源码结论适用于该二进制的可信度较高；仍保留"二进制为官方 CI 产物、本地未重建"的边界，不宣称逐字节同源。
- **无法建立（如实登记）**：① 二进制与 tag 的构建可重复性未验证（无官方 reproducible-build 声明）；② main 领先 183 提交中的能力一律标"主分支候选"，不与 v0.12.16 混计；③ 子模块 foliate-js 的上游（johnfactotum/foliate-js）与 fork 的分叉历史在 code-map 内另证，不在本文件展开。
