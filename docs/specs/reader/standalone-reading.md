# reader/standalone-reading（SD-04，READER-005 交付）

状态：current-state · 2026-11-01（READER-005 r1 merge 沉淀；final review
pass 4efdccf）。范围：本仓独立启动的真实 EPUB 阅读双端验收面——支持
profile、工具身份、应用自有媒体/链接契约与永久用户任务门。

## 启动 profile 与工具身份

- 双 profile（README 同源，R-01 实测）：`auto run --server=vm`（Vue 前端
  + VM HTTP 后端，缺省交付面）与 `auto run -r vm --server=vm`（VM 全轨
  分离模式）。均不要求 Rust 后端（pac.at 不声明 `api: "rust"`）。
- 数据目录 `AUTO_READER_DATA` env 优先；测试/复现用隔离目录。
- 工具身份（2026-11-01 冻结）：`auto`
  `0.1.0+plan-890-verified-r7-t19-2-gbe740b6`
  （sha256 `e7dd7df1be8f4d341a4f356e59dd887efe374245dacff92570e4c63c5246dcf8`）、
  `auto-ui-tool`（sha256 `4d2198b8bceba015c9f46157691fac2380cce720d0a5914fdec03c1cb39db47d`）。
  发现序 `AUTO_UI_TOOL_BIN` → 已安装 tool → 开发解析；缺失路径 = 具名
  失败 exit 1（无静默回落）。
- 长文导入预算 profile：`AUTO_HTTP_STEP_BUDGET=1e9` +
  `AUTO_HTTP_REQUEST_TIMEOUT_MS=300000`（001 交付的宿主可信配置）。

## 应用自有媒体契约（章图）

- URI：`GET /api/reader/media/<book_id>/res_<双射扁平名>` —— 首读/缓存
  命中/冷重启逐字稳定；Vue `<img>`（vite 代理）与原生 `image`
  （AUTO_HTTP_BASE HTTP 展开）同源消费。
- 扁平名：`_`→`__`、`/`→`_`、URL 不安全字符具名转义（`_s_` 等）、其余
  字符诚实拒绝（`img_name_unsupported`）——双射，无碰撞错图面。
- 预算/拒绝：单资源提取 12MiB 闸（`img_too_large`）；提取失败
  `img_extract_failed`（缺条目；`img_missing` 为存在性后守卫）；扩展名
  profile png/jpg/jpeg/gif/bmp/webp（`img_unsupported_type`）——浏览器
  与 iced 公共分母；err 项 UI 可见错误行，书与位置不受损，无半写残留。
- 服务层：`http.file_response`（VM 缺省 HTTP transport：GET/HEAD/单区间
  /条件请求/root 越界 403）；root 钉在目标书受管章节缓存目录，
  `res_` 前缀 + `[A-Za-z0-9._-]` 形状白名单双保险；端点分层
  api.at → db.at → library.at（codegen db.rs 一致性门）。

## 书内链接/脚注契约

- 解析：`xhtml_links` 与正文转换逐 tag 同步进（行号对齐由目标段逐字
  oracle 钉死）；`<n>.links.json` 边车缓存，正文行字节零变更（注释锚/
  Locator v1 兼容）。
- 目标：资源相对 href 以自章 ZIP 目录为基准；spine 全表精确匹配 →
  (章号， 行号)；fragment = 块级元素 id → 收束行号（跨章经目标章 ids
  表）；无 fragment → 章首。
- 拒绝（ch=0，UI 可见提示不跳转）：外部 scheme、越界/缺章、未知
  fragment、非 spine 资源、非 ASCII 文件名（继承 003 边界）。
- UI：链接 chips（可点击 col 外兄弟面，不冒泡点段）+ JumpLink；Vue
  目标段 V-20 正面积入 pane + 原文逐字；原生 chips 渲染 + 抽屉跳转。

## 永久用户任务门（R-01..06）

- 入口：`python tests/basic/verify_standalone.py --profile vue|vm`
  （自管生命周期；端口预检；`--auto-bin`/`AUTO_BIN` 绑定 CLI）。
  基线：vue 28 checks / vm 27 checks，0 FAIL（2026-11-01，上述工具身份）。
- 覆盖：R-01 启动+失败控制（错误 tool 非零、占口失败且既有实例不受
  影响）；R-02 图像（HTTP 字节身份 + UI 真解码：Vue naturalWidth、原生
  截图像素）；R-03 链接（解析全形 + V-20 入 pane 逐字 + 诚实拒绝）；
  R-04 注释/搜索/导出/恢复（verify_local 全量 + 原生驱动
  `tests/native/test_native_standalone_ui.py` 37 records）；R-05 负例
  （预算/缺条目/不支持类型 + verify_epub 22 checks）；R-06 受控反例
  （毁损图片 → oracle 必须真实失败非零 → 还原对照通过——双 profile）。
- 纪律：不以 `img:` 标记、API 预导入或框架夹具替代必需 UI 操作；HTTP/
  磁盘仅作独立读回 oracle；原生 UI 写传输缺口（N-005-A-1/A-2，见
  reading-annotations.md）为具名跨仓债——修复后重跑驱动即转正，不以
  历史 skip 顶替。
