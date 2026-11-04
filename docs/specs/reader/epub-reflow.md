# reader/epub-reflow（SD-01，READER-003 交付；READER-005 图像/链接扩展）

状态：current-state · 2026-11-01（READER-005 r1 merge 沉淀）
范围：EPUB3 无 DRM 重排版最小 profile 的导入与阅读能力边界。

## 容器与身份

- 合法入口 = `.epub` 扩展名 + 可读 `META-INF/container.xml` + 有效 rootfile。
- 书版本身份 = `sha256:<hex>`（整文件 `hash.file_sha256`，密码学摘要即内容
  证明）；TXT/MD 的 `ph1` 语义不变（SD-02）。
- 输入 ≤ 30 MiB（超出 `epub_too_large` 拒绝）；spine 条目 ≤ 4096。

## 导入事务（全有或全无）

1. 身份计算 → sha256 去重（同摘要=duplicate，force 独立副本）。
2. 受管副本 `books/<hashdir>/original.epub`（`file.copy` + sha256 读回对账）。
3. 导入期结构性校验：container/OPF/nav 解析 + spine→manifest 闭合 +
   href 安全检查；**不批量解压**（惰性按章，预算实证裁定）。
4. epubmeta 边车 `<data>/<book_id>.epubmeta.json`（spine/hrefs/toc/
   opf_dir/标题作者）；先 meta 后索引，索引失败孤儿=可诊断可重试。

## 章读取（惰性 + 缓存）

- 章 XHTML 首读解压（`zip.read_text`，单章 12MiB 硬闸）→ 文本行
  （段落/标题行 + `img:<zip 路径>` 标记行）→ `<managed>.chapters/<n>.txt`
  永久缓存；缓存写失败不阻塞阅读。
- 条目完整性 = inflate 结构完成性（zip native 内部）；**不宣称 CRC-32 级
  校验**（运行时无位运算，逐位模拟成本不成比例——能力边界如实记录）。
- 图片（READER-005 T-02 交付）：`img:` 行由后端 `zip.extract_entry`
  （12MiB 闸，rc=-2 超闸/-1 一般失败——读全后单次写，失败无半写残留）
  提取到 `<managed>.chapters/res_<双射扁平名>`；章 JSON `images[]` 恒全量
  （首读/缓存命中/冷重启同 URI），每项 `{k, uri, err}`。URI =
  `/api/reader/media/<book_id>/res_<扁平名>`（应用自有稳定服务面，
  http.file_response 承载 GET/HEAD/区间/root 越界 403；`image.thumb`
  票据面进程局所且 VM HTTP 不服务 `/api/__auto/media/*`——已弃用）。
  扁平名双射转义（`_`→`__`、`/`→`_`、URL 不安全字符具名转义、其余诚实
  拒绝）——`a/b_c.png` 与 `a_b/c.png` 不同槽不错图。拒绝码：
  `img_too_large`/`img_extract_failed`（缺条目）`img_missing`（存在性
  后守卫）/`img_unsupported_type`（png/jpg/jpeg/gif/bmp/webp 之外）/
  `img_name_unsupported`（非 ASCII 等未收编名——003 诚实失败边界延续）。
  err 项前端渲染可见错误行，不静默丢；字节级损坏由渲染端错误显示承载
  （无应用侧解码承诺）。显示面 N-003-7 归因作废（Vue `image`→`<img>`、
  原生 `View::Image` 双端在案）。
- 章标题：nav 目录标签（titles 管道围栏 `|t1|t2|`）——005 修复双管道
  缺陷（此前章标题恒回落"第 N 章"）。
- 解析/解压失败 → 「内容缺失/章节不存在」占位（不冒充、不回落 Demo）。
- 书内链接/脚注（READER-005 T-03 交付）：`xhtml_links` 与正文转换逐 tag
  同步进（含 img 行占位）产出 `{links:[{line,href,label}],ids:{id:line}}`
  → `<managed>.chapters/<n>.links.json` 边车缓存（正文行字节零变更——
  注释锚/Locator 兼容）。章内容相对 href 以**自章 ZIP 目录**为基准；
  目标 = spine 全表精确匹配 → (章号, 行号)；fragment = 块级元素 id →
  收束行号（跨章经目标章 ids 表）。无 fragment → 章首（para=-1）。
  诚实拒绝（ch=0，UI 可见提示不跳转）：外部 scheme（epub_href_ok 的
  `:` 拒绝覆盖 http:/mailto: 等）、越界/缺章、未知 fragment、非 spine
  资源。前端以链接 chips（可点击 col 外兄弟面）+ JumpLink 承载；
  Vue 目标段入 pane 正面积（V-20 同源）+ 原文逐字 oracle 实测。

## 安全与拒绝

- href 安装全检查：拒绝 `..`、绝对路径、盘符冒号、反斜杠、`//`、百分号
  编码（v1 能力边界：非 ASCII 文件名场景诚实失败）、反引号/管道。
- 无 DTD/外部实体/脚本执行/远程加载（XML 仅取 container/OPF/nav/XHTML
  目标子集；实体解码限五预定义）。
- 拒绝形态：`epub_invalid`（结构/引用/安全）、`epub_too_large`（输入/
  条目预算）、`epub_too_many`（spine 上限）；非 `.epub` 扩展名不进 EPUB
  分派（TXT/MD 语义不变）。

## 依赖与运行形态

- ZIP/解压 = PLAN-897 zip natives（`zip.list_json/read_text/extract_entry`，
  max_bytes 硬闸，错误形态见 docs/specs/auto-vm/zip-natives.md）。
- 定位复用 Locator v1（chapter_number=spine 序 + paragraph_index +
  para_text 逐字锚）；不宣称 EPUB CFI。
- 内链接/脚注跳转：READER-005 已交付（见上"书内链接/脚注"）；
  v1 段级粒度接缝延续（空 label（纯图链接）不收录——能力边界）。

## 正式引擎表面与文本面关系（READER-007 T-03/T-08 交付，SD-01 链接）

- 本文件的最小文本 profile 保留兼容与诊断用途：`chapter_json` 文本行
  （含 `img:` 标记行）仍是章缓存/搜索/注释 v1 段锚/Locator v2 逐字核验的
  正文事实源（服务器权威）；EPUB 阅读表面自 READER-007 T-03 起经
  doc-surface 引擎渲染（SD-01），文本面不再用于 EPUB 阅读显示。
- 扫描复杂度边界（T-08 修复登记）：`xhtml_to_lines`/`xhtml_links`/
  图片扫描为 O(正文长)（split 一次+逐段局部处理）；长章（12000 块）
  一次性转换 ~19s（缓存后 2s）——曾为 O(块数×正文长) 不终止缺陷
  （pristine main 既有，T-05 全书扫描首次暴露后修复）。4096 行静默
  上限已移除（超限行丢图与「不静默丢内容」相悖）。
- 图片提取边界：章图由后端 `zip.extract_entry` 提取（12MiB 闸）——
  引擎渲染路径的图像字节流 = 受管原件 zip 条目经 foliate loader 解析
  （不 чтению章缓存提取文件）；R-06 变异控制已随 SD-05 更新至受管原件
  条目（变异红→还原绿实证）。
