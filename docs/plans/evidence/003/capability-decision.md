# READER-003 T-00 能力决策（capability-decision）

日期：2026-10-31 · 状态：已冻结（T-01..T-04 按本决策执行；偏离须回写本文件并记账）
CLI：`D:/autostack/auto-man/target/debug/auto.exe`，`auto 0.1.0+v0.0.20-118-ge6cc06f`
（较计划基线 -117-g873fa23 新一个补丁集；本文件全部探针在 -118 上实跑，即证据所用构建）

方法：与 001 T-00 同纪律——只信实跑探针，不信文档注释。探针脚本
`tests/probe/t00_epub_cap_probe{,2..10}.as`（本仓提交）；原始日志
`%TEMP%/t00-epub-cap*.log`（本地留存）。

## CAP-01 二进制/ZIP/XML/图像能力裁定

| 能力 | 裁定 | 证据（实测） |
|---|---|---|
| 真实 SHA-256 | **可用**（升级 001 的 ph1 局限） | `hash.sha256("abc")` 已知向量 PASS；`hash.file_sha256(path)` 对文本/二进制文件 PASS（probe/1、2、6、10） |
| 字节读 | **可用，带纪律** | `file.read_bytes(path) -> []int` 对 416B 真实 ZIP 逐字节精确（Python hex dump 对照，probe/9 X2 CRC 跨界读与落盘字节完全一致） |
| 字节写 | **可用，带规避** | `file.write_bytes(path, list)` rc=0 落盘；**种子字面量列表**（`List<int>.new([0])` 后 push）64KB 规模 PASS（probe/5 T1/T3）；`List<int>.new([])` 后 push 必 raise（probe/5 T2 最小复现 → 框架缺陷 N-003-1） |
| 整文件拷贝 | **可用** | `file.copy` 二进制 sha256 逐字节一致（probe/10）——受管原件拷贝首选，不经字节列表 |
| 追加写 | 不提供 | `write_bytes` 两次调用=截断（size=2 非 4，probe/4 S3）；一次性组装后单次写 |
| base64 | 可用（str 域） | `base64.encode("Hi")` = `SGk=`；仅用于文本域，二进制不走此路径 |
| ZIP native | **不存在** | 源码级：auto-lang VM native 目录（1064 项）无 zip/archive/inflate；`zip.open`/`Zip.open` 触发编译错 `Undefined variable: zip`（probe/1 首轮实跑 exit 1）；auto-man 的 `zip` crate 仅用于工具链安装（up.rs），不对 .at 暴露 |
| XML native | **不存在** | 同上目录无 xml/dom（仅 csv/json/autodown-markdown） |
| inflate（DEFLATE/RFC1951） | **本计划纯 .at 实现** | 无 native 可用；VM List<int> push 1M PASS、循环算术吞吐实测（probe/2 Q4 ≈ 4M 除法/取模循环 72s 量级）；预算见 CAP-03 |
| 图像解码 | **宿主侧管线可用** | stdlib `auto/image.at`（Plan 547）：`image.thumb(path,size) -> "/api/__auto/media/{id}/{rev}"` 媒体 URI，jpg/jpeg/png/webp；两条 UI 轨均按路径/URI 引用（无需 .at 层像素访问） |
| 图像 UI widget | 可用 | `image` 在 AutoUI DSL widget 名单（VM codegen expr_ident.rs:193 实证）；iced image feature 在 vendor patch 中启用 |

**读字节纪律（本轮冻结，违反即毒化）**：元素先类型化提取 `let b int = bs[k]`
再做算术（probe/8 W1-W3 全对）；**禁止** `(""+x).to_int()` 链与 var 累加混合
（probe/6 U1、probe/7 V1/V2 复现字符串拼接毒化——001 T-00 报告 §VM 轨缺陷
同族，脚本上下文已知形态）。`file.read_bytes` 返回列表的 `len()` 不可信
（实测 5 字节文件报 7）；真实长度以 `fs.file_size(path)` 为准，越界索引
raise（probe/4 S1）。

**结论**：EPUB 所需能力全部可在本仓内以「现有 native + 纯 .at 实现」闭合，
**无需另立框架前置 Plan**。ZIP 读取器（中央目录+本地头）、DEFLATE 解压、
最小 XML 词法/结构解析为 T-01 交付物。框架缺口不阻塞但必须登记：
N-003-1（write_bytes 空列表+push raise）、N-003-2（read_bytes len() 虚报）、
N-003-3（to_int/var 累加拼接毒化在脚本上下文）——证据即上列探针，
由复审/merge 阶段决定是否入框架仓跟踪；本计划以已验证规避法交付。

## CAP-02 内容/图片/定位展示路线（两端）

- **共用内容模型（冻结）**：EPUB spine 顺序 = chapter_number（1 基）。
  导入时一次解析并转换：每章产出纯文本行文件（段落行 + 两类标记行），
  存 `<data>/books/<hashdir>/chapters/<n>.txt`（受管、不可变），章级
  `File.read_text_range` 窗读（复用 001 meta-index 架构）。
  - 段落行：XHTML 块级文本（p/h1-h6/li 的文本，trim 后非空行）；
  - 图片标记行：`img:<受管相对路径>`（该章引用的本地图片）；
  - 锚点标记行：`epub-anchor:<id>`（XHTML 内部锚点，供内链寻址）。
  - 链接表：每章 `links: [{para, to_chapter, to_para}]`（**段级粒度**，
    v1 冻结；行内多链接的段以首目标为代表——能力表如实记录）。
- **Locator**：完全复用 001 Locator v1 语义（chapter_number + paragraph_index
  + para_text 逐字锚点）；EPUB 的资源身份 = 书级 source_sha256（真 SHA-256）
  + 章 = spine 索引。不引入百分比/像素定位；不自称 EPUB CFI。
- **图片显示**：受管图片文件 → `image.thumb(path, size)` 媒体 URI →
  Vue `image` widget（style 尺寸）/ VM `image` widget 同源 URI。
  `image.thumb` 在应用 VM HTTP 服务上下文中的可用性是 T-02 首个探针；
  若不可用，回退路线 = reading_page 文本占位行 + 诚实提示（不静默降级），
  并升级为必需缺口路由。
- **字号**：沿用 001 font_size(small/medium/large) 存储与 body_style 映射，
  无新机制。

## CAP-03 资源/提交预算（依赖实现前冻结）

| 预算 | 值 | 语义 |
|---|---|---|
| 输入文件大小 | ≤ 30 MiB | 超出拒绝，错误可见，不入库 |
| ZIP 条目数 | ≤ 4096 | 中央目录计数，超出拒绝 |
| 单条目解压后 | ≤ 12 MiB | inflate 流式中计数（不信 ZIP 头声明），超出中止该条目并整体拒绝 |
| 累计解压输出 | ≤ 64 MiB | 同上，全局计数 |
| 单条目压缩比 | ≤ 200× | 声明压缩比超出即拒（防高压缩炸弹），实际输出仍以流式计数兜底 |
| 嵌套压缩包 | 拒绝 | manifest 中 application/zip 等容器类型不解析不引用 |
| 图片资源 | 文件 ≤ 12 MiB；解码 ≤ 32 MP | 超出拒绝该书导入（明确提示哪项） |
| 解压步数 | 沿用 HTTP profile（AUTO_HTTP_STEP_BUDGET=1e9 / 超时 300s） | 单请求内完成；超预算=失败可重试，不部分发布 |
| 提交语义 | 全有或全无 | 解析/预算任一失败：无 library 记录、无 meta、受管目录不留可读假书；已落盘临时文件留在诊断路径可重试（沿用 001 事务纪律；写侧均读回校验） |

### 架构修订（2026-10-31，本文件冻结权限内）：惰性按章解压

吞吐实测（probe/2 Q4 + PLAN-781 旧路径 ~170s/10MiB 记录）表明纯 .at
inflate 约 60-90 VM ops/输出字节、有效 100-300k ops/s——整书导入期解压
（数 MiB 文本）将超 300s 单请求预算。据此：

- **导入期**：只做不依赖批量解压的全部校验——ZIP 结构（EOCD/中央目录/
  本地头逐条目核对）、声明大小与压缩比对照 CAP-03 上限、manifest 闭合、
  container/OPF/nav XML 解析、spine/nav 目标存在性。这些是「全部必需资源
  和索引」。通过即发布书目。不产生空书假成功（结构性损坏导入期即拒）。
- **首读期**：章 XHTML 首次被读时解压+XHTML→文本块转换，产出落盘
  `chapters/<n>.txt` 永久缓存。**条目完整性 = inflate 结构完成性**（块
  结构/哈夫曼合法性/流终止自校验）——CRC-32 在无位运算的纯 .at 上需
  逐位模拟异或（实测算子集无 AND/XOR/SHL），~60-180 ops/字节将使 100KB
  章增加 20-60s，不成比例；字节级损坏几乎必然破坏 deflate 结构被 inflate
  拒绝。该弱化在 SD-01 如实记录（不宣称 CRC 级校验）。坏数据章以
  「内容缺失」诚实占位（既有占位语义），其余章节不受影响。
- E-04/E-05 边界相应细化：导入期拒绝=结构/预算/必需文档类；章体数据类
  损坏=首读诚实失败。该分工在 Spec 增量（SD-01）中如实记录。

## CAP-04 真实用户入口

- 导入 UI = 路径输入对话框（001 形态，双端同一 back 端点
  `POST /api/library/import`，无 OS 文件选择器依赖）。
- N-r8-1（原生轨 Http.post 缺参）/N-r8-3（原生导航驱动）在 -118 上的实际
  影响由 E-06（T-04）以现有原生 MCP 驱动
  `tests/review/reader001_r8_native_vm_restore.py` 方法实测；若原生导入
  仍不可驱动，按计划「必需缺口按 owner 关闭」路由，不以 fixture 注入或
  后台成功替代 UI 导入证据。
- 分派规则（冻结）：`format_of` 现有逻辑扩展——路径扩展名 `.epub`
  （不分大小写）→ EPUB 分派；TXT/MD 路径行为逐字节不变（t01-t07 全量回归
  兜底）。

## 依赖与许可

本计划**不新增任何外部依赖**：ZIP/inflate/XML/链表全为纯 .at；使用的
native（file.read_bytes/write_bytes/copy、hash.file_sha256、image.thumb、
既有 fs/str/json 集）随运行时 CLI 交付，无独立许可义务。运行时版本漂移
（-117→-118）按「假设变更即重跑」处理：本文件探针即 -118 新证。

## 对 T-01..T-04 的输入（速查）

1. 纯 .at ZIP 读取：中央目录定位（EOCD→CD offset）→ 本地头核对 →
   stored 直取 / deflate 经纯 .at inflate（位流用 List<int>，纪律见上）。
2. XML 最小解析：字节级词法（find/substr 渐进切片，001 T-01 修正后形态），
   仅取 OPF/container/nav/XHTML 所需子集；实体仅解码五预定义；DTD/外部
   实体直接拒绝（CAP-03）。
3. XHTML→文本块转换：块级元素边界、img/锚点/链接提取、实体解码、
   script/style 剥离。
4. 导入事务接入 `import_book_json` 同款协议（去重按 sha256、槽位、读回
   校验、meta 先写、索引后写）。
5. T-02 首探针：`image.thumb` 在应用服务上下文可用性。
