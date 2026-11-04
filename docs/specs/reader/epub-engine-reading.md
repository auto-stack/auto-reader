# reader/epub-engine-reading（SD-01，READER-007 交付）

状态：current-state · 2026-11-04（READER-007 work T-01～T-09 沉淀；final
review 待 T-11）。范围：正式 EPUB 阅读表面（doc-surface 引擎）的入口、
支持边界、资源/安全边界、会话与 Locator v2 契约。设计冻结契约见
docs/design/02-epub-engine-reading.md。

## 正式入口与表面

- 正式书架/路由 → reading_page 对 EPUB 书自动装载应用自有固定资产与受管
  原件（doc-surface 组件 + engine-adapter）；不依赖 tests/probe、
  D:/autostack/readest、PROBE_* env、驱动注入或旁路服务（P-02 离线 +
  资产独立实证）。
- 引擎 = foliate-js fork@3d794195（MIT，readest 扁平化 flat 重写为应用
  自有受管资产，manifest 记录 hash）+ 应用自有 engine-adapter（T-03）。
- TXT/MD 保持 scroll-pane 文本面；EPUB 走引擎面（T-03 起为正式面，
  旧文本面不再用于 EPUB——SD-05 表面变更随附）。

## 支持边界

- 支持：无 DRM EPUB3 重排版的正文结构 + 基本出版物 CSS、内置/受管图、
  目录/跨章/脚注往返、单列分页/连续滚动、字号/列宽/主题、精确选区/
  高亮/批注/恢复。
- 非本期：复杂版式/竖排/公式/任意 CSS、PDF/漫画/Kindle、TTS、同步、
  系统深链、Linux/移动——不静默丢内容而显示已支持。

## 受管资源与安全边界（T-08 实证）

- 资产服务仅两源：本书受管内容（原件/章缓存/媒体）+ 固定引擎资产
  （root 钉应用自有资产目录，`AUTO_READER_ENGINE_ASSETS` 可覆盖）；
  未知名/越界/跨书路径具名 404（P-09.resource-gate）。
- 书内活动脚本拒绝（T-08 交付）：受管 adapter 为唯一转换接缝——
  ①`loadContent()` 数据面剥内联 `<script>`/`on*` 处理器（srcdoc 写入
  前置剥除）；②`load()` URL 面对冲（blob 重写）；③离屏面
  （createDocument）剥除；④loader `transformTarget` allow=false 拒独立
  脚本资源。门腿实证：crafted 脚本 EPUB 装载后 `window.__pwned` 缺席。
- 引擎预算：导入 30MiB/spine≤4096/单资源 12MiB（继承不变）+ 装载 ≤15s
  + 选区回传 ≤5s + 冷恢复 ≤30s + 清理 ≤10s + 驱动 ≤600s。

## 会话与命令

- `POST/GET /api/reader/session`（书存在 + source_hash 一致 + engine
  非空；sessions.json 备份协议）；`GET /api/reader/surface-url`（最近
  会话装载 URL）；`POST/GET /api/reader/command`（goto/settings/flow
  命令队列，seq 单调递增）；`POST /api/reader/locator`（选区录入环）。
- 选区录入环（服务器权威）：会话/书/源版本/资源（spine + 权威 href）/
  逐字 quote/occurrence 书界在界/CFI 形状七级校验；canonical context 由
  服务器从章缓存正文计算（不信任引擎自述）；产出 canonical
  reader-locator v1 提案（locator-proposals/<sid>.json，非用户数据）。

## Locator v2（方案甲，SD-02/03 协同）

- 定位锚 = canonical reader-locator v1：`schema/version/kind(epub_range)/
  book_id/source_hash/resource{spine_index,href}/engine{...}/
  range{start[,end]}/quote/context{before,after}/occurrence{scope,index}/
  created_at`。主键纪律 = CFI + 逐字 quote/context + 显式作用域
  occurrence；百分比/裸偏移不作主键。
- 版本管理：annotations 文件 1→2（仅因存在 v2 锚升 2，末枚删除回落 1
  字节兼容）；ReadingState 无全局版本（可选顶层 locator 键）；书
  import_version 不变。
- 三环核验（全部不信任引擎自述）：录入环（七级校验 + context 重算）、
  恢复环（readback 比对，失配 → needs_relocate 不跳第一处）、回访环
  （verify-ann oracle 匹配才 goto）。
