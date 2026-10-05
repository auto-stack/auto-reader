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
| 模块单测 | `auto test` | hashx 1 + pathx 2（importers 单测因「use 进 VM 测试装置编译失败」缺陷迁至脚本规格 t03 面，随 HTTP/规格覆盖） |
| 后端规格（脚本） | `auto tests/spec/t01_library_spec.as`（34）/ `t02_reading_spec.as`（28）/ `t04_library_spec.as`（14）/ `t05_collision_spec.as`（23）/ `t06_integrity_spec.as`（42） | 导入事务/去重碰撞/索引完整性/阅读状态 schema/边界；日志在 `%TEMP%/tNN-spec.log`，FAIL 时进程非零退出 |
| HTTP 驱动 | `python tests/spec/t01_http_verify.py`（39）/ `t02_http_verify.py`（21）/ `t04_http_verify.py`（10） | 先按上表以隔离目录启动 `auto run --server=vm`，同一 `AUTO_READER_DATA` 顺序执行 |
| 复审回归 | `python tests/review/reader001_repro.py` | F-02/03/04/06 负例 8 检查；要求数据目录名以 `reader001-review-` 开头 |
| UI（Playwright） | `cd tests && npx playwright test` | `smoke.spec.ts`（demo 链路）+ `real-book.spec.ts`（真实书链路 7 例）；需同一 `AUTO_READER_DATA` 与 `BOOK_URL=http://localhost:17824` |

测试纪律：夹具只进隔离目录；失败检查「输出与退出码」同时成立（`auto test`
对单文件编译失败曾退出 0——CLI 缺陷已登记，脚本规格以日志 `fails=0` 与
退出码双重判据）。

## 来源与组合

来源提交、路径与文件 hash 见 `SOURCE-IMPORT.json`。首次导入提交保留在 `source-sync` 分支；完整 v0.5 恢复后从该基线导入差异，再与产品开发线合并。

AutoOS 通过 [`apps/018-book-reader`](https://github.com/auto-stack/auto-os/tree/v0.6-dev/apps/018-book-reader) submodule 固定本仓版本；教学 Demo 保留在来源仓。

## 产品规划（2026-10-04）

[需求与设计、首版 roadmap、业界调研及前三个实施计划](docs/README.md)。

文档是设计基线；实现与验收状态以各计划证据为准（READER-001 Phase 2 修复见
`docs/plans/001-real-library.md` §5/§9）。
