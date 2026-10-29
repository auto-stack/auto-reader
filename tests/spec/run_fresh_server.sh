#!/usr/bin/env bash
# run_fresh_server.sh — READER-001 干净数据目录启动方式（T-04 交付）。
# 用隔离的临时数据目录启动 auto-reader（Vue 前端 17824 + AutoVM HTTP 后端
# 17825），不接触用户真实知识库；数据目录路径回显，便于测试/复现。
# 用法：bash tests/spec/run_fresh_server.sh [数据目录] [--vm-full]
#   数据目录   默认 $(cygpath -u "$TEMP")/autoreader-fresh-<uuid>
#   --vm-full  以 VM 前端全轨启动（默认 Vue 前端 + VM 后端）
set -e
cd "$(dirname "$0")/../.."

TMP_U="${TEMP:-/tmp}"
if command -v cygpath >/dev/null 2>&1; then TMP_U=$(cygpath -u "$TEMP" 2>/dev/null || echo "$TMP_U"); fi
DATA_DIR="${1:-$TMP_U/autoreader-fresh-$(uuidgen 2>/dev/null || echo $RANDOM$$)}"
FLAG=""
if [ "$2" = "--vm-full" ] || [ "$1" = "--vm-full" ]; then FLAG="-r vm"; fi

mkdir -p "$DATA_DIR"
# T-26 导入预算 profile（PLAN-781 交付的宿主可信配置）：HTTP dispatch 累计
# 指令上限可配——10MiB 成功导入最坏 ~420M 步，默认 10M 必然预算错误。测试/
# 开发实例统一 1e9 步 + 5min 请求超时（已设置时尊重外部值）。上限语义见
# auto-lang docs/specs/auto-lang/vm/design/handler-execution-budget.md。
if [ -z "$AUTO_HTTP_STEP_BUDGET" ]; then
  export AUTO_HTTP_STEP_BUDGET=1000000000
fi
if [ -z "$AUTO_HTTP_REQUEST_TIMEOUT_MS" ]; then
  export AUTO_HTTP_REQUEST_TIMEOUT_MS=300000
fi
echo "AUTO_READER_DATA=$DATA_DIR"
echo "front: http://localhost:17824  back: http://localhost:17825"
echo "AUTO_HTTP_STEP_BUDGET=$AUTO_HTTP_STEP_BUDGET AUTO_HTTP_REQUEST_TIMEOUT_MS=$AUTO_HTTP_REQUEST_TIMEOUT_MS"

AUTO_READER_DATA="$DATA_DIR" auto run --server=vm $FLAG
