# reader/epub-reflow（SD-01，READER-003 交付）

状态：candidate（复审/merge 后落地）· 2026-10-31
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
- 图片：`img:` 行由后端 `zip.extract_entry`（12MiB 闸）落盘 +
  `image.thumb` 媒体 URI，章 JSON `images[]` 字段承载；**显示面 N-003-7
  具名缺口**（AutoUI 无 image widget）——img: 行以标记文本诚实显示。
- 解析/解压失败 → 「内容缺失/章节不存在」占位（不冒充、不回落 Demo）。

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
- 内链接/脚注跳转：归 READER-002-A（v1 段级粒度接缝已留：links 表设计
  在 capability-decision §CAP-02，未在本轮交付）。
