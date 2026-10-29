# auto-reader

图书阅读器，使用 AutoLang / AutoUI 开发的独立应用。

本仓是首批产品源码基线；当前能力以导入版本为准，仓库描述中的产品方向不表示全部已实现。

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

2026-10-12 用户路由决策后，auto-lang **PLAN-781**（Reader 框架前置：原生验收、
段落锚点与 10MiB 导入）已交付并归档（final pass r11）：child-anchor 段落锚点、
`AUTO_HTTP_STEP_BUDGET` 导入预算、AutoUI MCP 原生验收通道、章 meta 索引
（reader 侧分支 plan-781e-meta-index，已随 r8 落地）。2026-10-29 r8：恢复定位
切换 scroll-anchor 元素级锚点（Vue 轨 T-R10 混排几何门转正通过）；10MiB 成功
导入达成（t04 成功门 + 781 deep 全章 oracle）；原生 VM 轨恢复行为验收因
CLI 更换后 reading 页面在 `-r vm` outlet 无法挂载（跨仓缺陷 N-r8-2，登记
计划 §10）保持具名未验收。完整事实见计划 §9/§10，不能将上表已过回归
等同于全计划通过。

## 来源与组合

来源提交、路径与文件 hash 见 `SOURCE-IMPORT.json`。首次导入提交保留在 `source-sync` 分支；完整 v0.5 恢复后从该基线导入差异，再与产品开发线合并。

AutoOS 通过 [`apps/018-book-reader`](https://github.com/auto-stack/auto-os/tree/v0.6-dev/apps/018-book-reader) submodule 固定本仓版本；教学 Demo 保留在来源仓。

## 产品规划（2026-10-04）

[需求与设计、首版 roadmap、业界调研及前三个实施计划](docs/README.md)。

实现与验收状态以各计划证据为准；[READER-001](docs/plans/001-real-library.md)
处于 executing/r8（PLAN-781 前置落地后的业务接入阶段），r8 问题与修复方案见 §5/§9/§10。
