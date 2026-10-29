# auto-reader

图书阅读器，使用 AutoLang / AutoUI 开发的独立应用。

READER-001已交付归档（r9，32/32）：真实TXT/Markdown书库、受管原件、内容锚点与重启恢复。最小EPUB和本地增强/Notes联动分别由003、002 r3规划，尚未实现。

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
| 10MiB deep oracle | `python D:/autostack/auto-lang/scripts/tools/test_reader_import_budget.py --reader-dir <本仓>`（auto-lang 仓 PLAN-781 交付） | TXT/MD 全章逐字 + 冷重启复扫 + 低预算拒写 + 双实例；自管实例与端口 |
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

## 产品规划（2026-10-04）

[需求与设计、首版 roadmap、业界调研及前三个实施计划](docs/README.md)。

当前顺序为 **001（已归档）→003最小EPUB→002-A本地增强与摘录→002-B Notes交接**。003不等待完整002；002-A可独立验收/阶段交付，B等Notes-002真实接收，B未完成不把002整Plan归档。

- [READER-001（archive/r9，32/32）](docs/plans/archive/001-real-library.md)
- [READER-003：最小重排版EPUB导入与阅读（drafting/r3）](docs/plans/003-epub-reflow.md)
- [READER-002：本地阅读体验、摘录与分阶段Notes联动（drafting/r3）](docs/plans/002-reading-annotations.md)

本轮仅修订计划、路线与状态，不启动实现。003所需的基本内容/字号/位置适配在003自身交付；原003高亮恢复要求归入002-A，需求保留。开发使用 `D:/autostack/auto-reader` 独立clone的main，AutoOS子模块仅固定交付版本；先push应用再更新组合pin，独立clone不切detached。Linux支持仍等待Nix＋COSMIC发行版基础。
