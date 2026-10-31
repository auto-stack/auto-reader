# auto-reader

图书阅读器，使用 AutoLang / AutoUI 开发的独立应用。

更新：2026-10-31。001真实TXT/Markdown书库与定位已交付；003的最小EPUB数据面已落地；002 r4以本地A（搜索、注释、Markdown导出）收尾；004验收驱动归属迁移已交付。图片目前仍以标记呈现，原生注释门和真实UI保存链仍有覆盖缺口，不能据框架夹具通过声称实际阅读全流程已验。

当前后续 [READER-005：EPUB实际阅读与本地能力双端验收收口](docs/plans/005-standalone-epub-and-ui-acceptance.md) 为 drafting/r1、0/9，**尚未实施**。先核验现有image组件/媒体链与当前CLI＋tool，补图像缓存、书内链接/脚注和真实Vue/原生任务；Notes交接继续留AutoOS TODO。

## 运行

安装对应版本的 `auto` CLI 后，从本仓根执行（READER-001 Phase 2 起的可用入口，实测）：

```sh
# Vue 前端 + AutoVM HTTP 后端（真实书库数据面）
auto run --server=vm

# VM 全轨（VM 前端 + VM 后端，分离模式）
auto run -r vm --server=vm
```

前端端口：`17824`（vite 监听 IPv6 回环 `localhost` 可达）。后端端口：`17825`。

数据目录：`AUTO_READER_DATA` 环境变量优先，缺省 `~/.autoreader`。测试/复现请用
隔离目录：`bash tests/spec/run_fresh_server.sh`。

**登记中的启动限制**（跨仓框架差距，见 `docs/research/20261005-t00-runtime-capability.md` §12，不以本仓修复顶替）：

- 缺省 `auto run`（Vue 前端 + a2r Rust 后端）构建失败（动态 JSON 字段访问等
  a2r 映射未落地），120s 内后端不就绪；`pac.at` 已按 014-weather 先例不声明
  `api: "rust"`。
- 裸 `auto run -r vm` 会进入 VM+VM **merged** 模式；本应用前端数据面走
  HTTP（PLAN-043 裁定），merged 无 HTTP 服务器可达，必须带 `--server=vm`
  走分离模式。
- ≥1MiB 长文导入超 AutoVM 指令预算缺省上限——PLAN-781 交付宿主可配
  `AUTO_HTTP_STEP_BUDGET`（1..=4e9）后已解阻：`tests/spec/run_fresh_server.sh`
  统一注入 1e9 步 + `AUTO_HTTP_REQUEST_TIMEOUT_MS=300000`，10MiB 成功导入
  见测试表 t04；缺省 10M 语义不变。

共享 StyleKit 已固定在 `vendor/stylekit`，无需相邻 auto-lang 示例目录。

## 测试

| 入口 | 命令 | 覆盖 |
|---|---|---|
| 模块单测 | `auto test` | hashx 1 + jsonx 3 + pathx 2 = 6（importers 另由脚本 t03 与 HTTP 覆盖） |
| 后端规格（脚本） | `auto tests/spec/t01_library_spec.as`（34）/ `t02_reading_spec.as`（38）/ `t03_importers_spec.as`（26）/ `t04_library_spec.as`（14）/ `t05_collision_spec.as`（23）/ `t06_integrity_spec.as`（91）/ `t07_meta_index_spec.as`（67，PLAN-781 阶段 E 章 meta 索引 parity） | 293 检查；读取 `%TEMP%/tNN-spec.log` 的 PASS/FAIL 与进程退出码 |
| HTTP 驱动 | `python tests/spec/t01_http_verify.py`（39）/ `t02_http_verify.py`（26，额外 emoji 用例可能 SKIP；须在 t01 之后同实例跑——需 ≥1 本书）/ `t04_http_verify.py`（17，10MiB 成功导入 + 2001 章对账 + 首/中/末章逐字） | 套件使用新实例及隔离目录，驱动与服务器共享 `AUTO_READER_DATA`；10MiB 断言=成功门（r8，预算 profile 下） |
| 10MiB deep oracle | `python tests/spec/test_reader_import_budget.py --auto-bin <auto.exe>`（或 `AUTO_BIN` 环境变量；READER-004 自 auto-lang 迁入，原 PLAN-781 交付；`--reader-dir` 缺省=本仓根） | TXT/MD 全章逐字 + 冷重启复扫 + 低预算拒写 + 双实例 + 坏编码/boot fail-fast + 损坏章负例；自管实例与端口 |
| 原生验收（框架正对照） | `python tests/native/test_native_reader_acceptance.py --auto-bin <auto.exe> --app-dir <本仓> --data-dir <隔离父目录> --out-dir <证据目录>`（READER-004 自 auto-lang 迁入；`--case` 可选，缺省 required 集不含 `v12_injected_fail` 反控） | 真实窗口几何（scroll-geometry 夹具）：假几何负例/裁剪/锚点互操作/原生锚点；save-restore 夹具真实保存/冷恢复；双实例隔离/启动失败/端口占用/超时故障控制；pid↔端口身份与进程收割 |
| 复审回归 | `python tests/review/reader001_repro.py` / `reader001_r3_repro.py` / `reader001_r4_repro.py` / `reader001_r5_repro.py` / `reader001_r6_repro.py` / `reader001_r7_repro.py`（同目录） | 8/12/8/5/24/14 检查全部 PASS（r6 恢复准入 24 项含 i32 边界/小数/未知键正负对照）；目录名须以 `reader001-review-` 开头；旧r2缺参400不代表语义校验 |
| 原生 VM 验收 | `python tests/review/reader001_r8_native_vm_restore.py` | `-r vm --no-merge` 原生 iced 窗口（AutoUI MCP 通道）：冷重启后恢复定位 ¶50 可见（autoui_visibility 正面积交集）+ pane offset 深位置 + ¶100 反差 |
| UI（Playwright） | `cd tests && npx playwright test real-book.spec.ts`（11，含 T-R10 V-20 几何门）/ `smoke.spec.ts`（10） | 需同一隔离 `AUTO_READER_DATA`、`PW_CHROMIUM`（指向 ms-playwright 已装全量 chrome——1.62.1 对应 headless_shell-1234 本机缺失且 CDN 不可达，T-09 修订门）；每套件前确认实例为全新启动（长跑实例有在册 N-2 劣化） |

测试纪律：夹具只进隔离目录；失败检查「输出与退出码」同时成立（`auto test`
对单文件编译失败曾退出 0——CLI 缺陷已登记，脚本规格以日志 `fails=0` 与
退出码双重判据）。

2026-10-29：READER-001 r9已完成最终复审并归档，N-r8-2根因已定案为app的 `let pr` 非法重赋值及框架静默诊断可见性，应用修复与语言886均已有交付记录。原生恢复驱动16/16、Vue混排几何门、10MiB成功导入和main landing证据见[归档001](docs/plans/archive/001-real-library.md)。早期r7/r8的needs_fix或未验收描述保留为历史，不作为当前状态；这不抹去上列其他运行栈/导入驱动限制。

## 来源与组合

来源提交、路径与文件 hash 见 `SOURCE-IMPORT.json`。首次导入提交保留在 `source-sync` 分支；完整 v0.5 恢复后从该基线导入差异，再与产品开发线合并。

AutoOS 通过 [`apps/auto-reader`](https://github.com/auto-stack/auto-os/tree/main/apps/auto-reader) submodule 固定本仓版本；教学 Demo 保留在来源仓。

## 当前计划与开发

- [001：真实书库与定位](docs/plans/archive/001-real-library.md)：archive/r9、32/32，保持历史。
- [003：最小EPUB数据面](docs/plans/archive/003-epub-reflow.md)：merge 24c9838已有交付回执；图片显示/书内链接与完整UI门留005。
- [002：本地阅读、注释与导出](docs/plans/archive/002-reading-annotations.md)：r4按用户裁决仅本地A收尾；Notes联动已移OS TODO，不再作为本地交付前置。
- [004：验收驱动与夹具归属迁移](docs/plans/archive/004-reader-test-ownership-migration.md)：已交付；夹具与HTTP保存链覆盖有明确边界。
- [005：EPUB实际阅读与双端验收收口](docs/plans/005-standalone-epub-and-ui-acceptance.md)：drafting/r1、0/9，当前下一步为T-00，未开始实现。

[路线图](docs/roadmap-v0.6.md) · [规划入口](docs/README.md)。003旧frontmatter和002历史任务计数存在滞后，以实际交付回执及Spec区分范围，本轮不修改归档。

开发/计划/顺序复审使用 `D:/autostack/auto-reader` 独立clone main，一app一写入者；AutoOS `apps/auto-reader`仅保留组合pin。本轮只准备并推送计划/README/roadmap，不实现，不更新OS子模块。应用单独运行与验证后由统一集成计划装配；Linux仍等待Nix＋COSMIC发行版基础。
