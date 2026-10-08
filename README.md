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
- ≥1MiB 长文导入超 AutoVM 指令预算硬上限（显式失败或连接中断，不以降标顶替）。

共享 StyleKit 已固定在 `vendor/stylekit`，无需相邻 auto-lang 示例目录。

## 测试

| 入口 | 命令 | 覆盖 |
|---|---|---|
| 模块单测 | `auto test` | hashx 1 + jsonx 3 + pathx 2 = 6（importers 另由脚本 t03 与 HTTP 覆盖） |
| 后端规格（脚本） | `auto tests/spec/t01_library_spec.as`（34）/ `t02_reading_spec.as`（38）/ `t03_importers_spec.as`（26）/ `t04_library_spec.as`（14）/ `t05_collision_spec.as`（23）/ `t06_integrity_spec.as`（91） | 226 检查；读取 `%TEMP%/tNN-spec.log` 的 PASS/FAIL 与进程退出码 |
| HTTP 驱动 | `python tests/spec/t01_http_verify.py`（39）/ `t02_http_verify.py`（26，额外 emoji 用例可能 SKIP）/ `t04_http_verify.py`（12） | 套件使用新实例及隔离目录，驱动与服务器共享 `AUTO_READER_DATA`；10MiB 项仅证明错误保护 |
| 复审回归 | `python tests/review/reader001_repro.py` / `reader001_r3_repro.py` / `reader001_r4_repro.py` / `reader001_r5_repro.py` / `reader001_r6_repro.py`（同目录） | 8/12/8/5/24 检查全部 PASS（r6 恢复准入 24 项含 i32 边界/小数/未知键正负对照）；目录名须以 `reader001-review-` 开头；旧r2缺参400不代表语义校验 |
| UI（Playwright） | `cd tests && npx playwright test` | smoke 10；real-book 10已过+1混排fixme未验收。需同一隔离 `AUTO_READER_DATA`、`BOOK_URL=http://localhost:17824` 与 `PW_CHROMIUM`（指向 ms-playwright 已装全量 chrome——1.62.1 对应 headless_shell-1234 本机缺失且 CDN 不可达，T-09 修订门）；每套件前确认实例为全新启动（长跑实例有在册 N-2 劣化） |

测试纪律：夹具只进隔离目录；失败检查「输出与退出码」同时成立（`auto test`
对单文件编译失败曾退出 0——CLI 缺陷已登记，脚本规格以日志 `fails=0` 与
退出码双重判据）。

2026-10-08 Phase 6 修复恢复消费者准入（F-18）并通过 T-31 独立终审确认（14 项独立
新向量 + r6 驱动 24 项全 PASS）：移除日志行在解析/改写前过
`jsonx.valid_removed_entry` 准入、身份核对与发布前 `valid_index` 候选验证。
计划终审裁决=blocked（保持 executing）：混排视口恢复（F-12/T-25，等待
auto-lang child-anchor 前置）、10MiB 成功导入与原生 VM 恢复（T-26 前置）
仍为具名跨仓框架前置，等待用户授权/移交决策。完整事实见
[复审报告](docs/reviews/reader-001-r6-20261007.md)、[r7 终审报告](docs/reviews/reader-001-r7-20261008.md)
与计划 §9，不能将上表已过回归等同于全计划通过。

## 来源与组合

来源提交、路径与文件 hash 见 `SOURCE-IMPORT.json`。首次导入提交保留在 `source-sync` 分支；完整 v0.5 恢复后从该基线导入差异，再与产品开发线合并。

AutoOS 通过 [`apps/018-book-reader`](https://github.com/auto-stack/auto-os/tree/v0.6-dev/apps/018-book-reader) submodule 固定本仓版本；教学 Demo 保留在来源仓。

## 产品规划（2026-10-04）

[需求与设计、首版 roadmap、业界调研及前三个实施计划](docs/README.md)。

实现与验收状态以各计划证据为准；[READER-001](docs/plans/001-real-library.md)
已重新激活 executing/r7，Phase 6 问题与修复方案见 §5/§9。
