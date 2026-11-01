# Readest 代码地图（READER-006 · code-map）

状态：drafted · 2026-11-01。
证据基线：**tag `v0.12.16` = commit `3cc39ad7a558e6612e1a8135058fbd6f3c90b3e3`**（发布身份与子模块固定见 [baseline](baseline.md) §2；研究检出 detached 于该 tag，工作区 clean）。子模块：`packages/foliate-js` @ `3d7941954a98b136316a795e8200d60c9643b141`；`packages/tauri` @ `382ea858bdd29458a5447e49c401b3ac64f0c3c0`（readest 分支）。

**固定引用格式（permalink）**：

- readest 仓库：`https://github.com/readest/readest/blob/v0.12.16/<path>#L<n>`（等价固定提交形式 `.../blob/3cc39ad7/<path>#L<n>`）
- foliate-js fork：`https://github.com/readest/foliate-js/blob/3d7941954a98b136316a795e8200d60c9643b141/<path>#L<n>`
- tauri fork：`https://github.com/readest/tauri/blob/382ea858bdd29458a5447e49c401b3ac64f0c3c0/<path>#L<n>`

本文每条结论均附 `path:line` 引用，行号在 tag `v0.12.16`（foliate-js / tauri 在各自固定提交）处有效；凡属推断而非直接读码或实测的结论，一律以 **[推断]** 标注。运行时实测交叉验证引自 [ui-study](ui-study.md)（0.12.16 Windows x64 官方 portable，SHA256 见 baseline §4）；能力对照另见 [capability-matrix](capability-matrix.md)。

---

## 2. 总览

**技术栈**：Next.js 16 + React 前端（`apps/readest-app/src`）运行于 Tauri v2 壳（**Readest fork，仅 5 个 fork 提交**，§7.4）；WebView 内核按平台分派——Windows = WebView2、Linux = **CEF**（经上游 tauri `feat/cef` + `[patch.crates-io]` 重定向，§7.3/§7.4）、macOS/iOS = WKWebView、Android = Chromium（[ui-study](ui-study.md) §0：Windows 标准构建为 WebView2）。文档引擎为 foliate-js 的 Readest fork：**包含上游历史至 `c49ded0`（John Factotum 最后一次提交，2025-09-24），并领先 254 个提交**（`git rev-list --count c49ded0..HEAD`；上游此后是否有未合并提交离线不可证，见 §10）。

**组件图（文本）**：

```
┌─ Tauri v2 壳（fork 382ea858，5 commits）
│   Rust 命令层 src-tauri/src/lib.rs:661-722：
│   transfer_file（HTTP 下/上传）· localsend（LocalSend v2.2 Wi-Fi 传输）· nightly_update
│   epub/mobi/pdf/comic 原生解析 · backup_zip · dir_scanner · media_proxy · rangefile://
│   deep-link · updater · single-instance · eink 检测 · sentry
│   一方插件：native-bridge · native-tts · turso(嵌入式 SQLite) · webview-upgrade
▼
Next.js + React 前端（apps/readest-app/src）
├─ app 路由层：app/reader/page.tsx:39 → Reader.tsx → ReaderContent.tsx:145-162（initViewState）
├─ 阅读宿主：FoliateViewer.tsx:125 —— 自行创建并托管 <foliate-view> 元素
▼
foliate-js fork（packages/foliate-js @ 3d7941954）
    <foliate-view> view.js:224（格式嗅探/进度对象/注释·搜索·TTS 门面）
    ├─ <foliate-paginator> paginator.js:1500（重排：每 section 一 iframe，CSS 多栏分页）
    └─ <foliate-fxl> fixed-layout.js:292（固定版式：EPUB FXL / PDF）
▼
services 层（cloudService · sync/* · bookService · tts · translators · ai · opds · audiobookshelf · statistics …）
▼
存储：Books/library.json + Books/<hash>/{书文件,cover.png,config.json,nav.json}
      Settings/settings.json（双写 .bak）· Data/statistics.db(SQLite) · Cache/Fonts/Dictionaries
```

运行时交叉验证：[ui-study](ui-study.md) §2 只读观察到完全一致的结构——`<foliate-view>`(shadow) → `<foliate-paginator>`(shadow) → 每 spine 一 iframe，相邻章预停靠屏外，**超长章 iframe 宽达 133,280 px**（1200 段分栏布局）；[ui-study](ui-study.md) §8 据此判定该应用为"WebView2 + React/Next + foliate-js fork（iframe 分节 + 分栏 paginator）"的 DOM 重度形态。

---

## 3. 文档引擎（foliate-js fork）

### 3.1 模块清单（`packages/foliate-js`）

| 模块 | 行数 | 职责 | 关键导出/符号（含引用） |
|---|---|---|---|
| view.js | 717 | `<foliate-view>` 宿主元素：格式嗅探、渲染器选择、进度对象、注释/搜索/TTS 门面、在读历史 | `makeBook` (view.js:82)、`View` (view.js:224)、`View.open` (243)、`View.init` (326)、`View.goTo` (530)、`resolveNavigation` (516)、`addAnnotation` (390)、`search` (633)、`initTTS` (697)、`getCFI` (501)、`resolveCFI` (506)、错误类 `ResponseError/NotFoundError/UnsupportedTypeError` (71-73) |
| paginator.js | 4343 | `<foliate-paginator>` 重排渲染器：每 section 一 iframe（内部 `View` 类 722），CSS 多栏分页 + 滚动流，View-Transitions 滑动/卷页翻页，超长章分块，页眉/页脚槽 | `Paginator` (1500)、内部 `View` (722)、`columnize` (975)、`scrolled` (912)、`#display` (3798)、`goTo` (4152)、`#goTo` (4043)、`#scrollTo` (3329)、relocate 发射 (3793)、`getContents` (4261)、`setStyles` (4295)、observedAttributes (1501-1504) |
| fixed-layout.js | 2148 | `<foliate-fxl>` 预分页渲染器（EPUB FXL + PDF）：跨页拼版、捏合缩放、平移、webtoon 纵向条漫、逐拼版生命周期 | `FixedLayout` (292)、observedAttributes `zoom,scale-factor,spread,flow,scroll-gap,scroll-direction,lock-pan-x` (293)、`panX` 属性（fork bc73267）、`customElements.define` (2148) |
| epub.js | 1463 | EPUB 容器→OPF→spine/资源/TOC/nav/ncx；加密；资源加载器 blob 替换；media overlays | `EPUB` (1260)、`EPUB.init` (1284)、`Encryption` (813)、`deobfuscators` (796)、`Resources`/`Loader`（文件上部）、`getEpubMetadata` (1459)、`parseEpubMetadataFromXML` (1460)、`MediaOverlay` 经 `getMediaOverlay` (1393) |
| epubcfi.js | 392 | EPUB CFI 子集：解析/序列化、区间↔CFI、比较、伪 section CFI、Calibre 导入 | `parse` (107)、`fromRange` (325)、`toRange` (333)、`joinIndir` (16)、`buildRange` (139)、`compare` (163)、`collapse` (134)、`fake` (376)、`fromCalibrePos` (383)、`fromCalibreHighlight` (389)、`isCFI` 正则 (9)；fork：`cfi-inert`/`cfi-skip` 节点过滤 (194-195) |
| progress.js | 228 | 进度计算器：TOC 项查找、按 section 的分数/LOC/时间、CFI→分数 | `TOCProgress` (18)、`SectionProgress` (173；以 `sizePerLoc=1500, sizePerTimeUnit=1600` 构造于 view.js:252)、`PageProgress` (62) |
| overlayer.js | 520 | 每文档 SVG 覆盖层：高亮/搜索命中/笔记渲染、命中测试、绘制样式 | `Overlayer` (51)、`add` (203)、`remove` (211)、`hitTest` (227)、静态 `highlight/underline/strikethrough/squiggly/outline/bubble/copyImage` (246-508)；fork：`mergeLineRects` 每行一条 (25)、`pageOf` (9) |
| footnotes.js | 223 | 识别脚注链接、抽取注释正文到弹层文档 | `FootnoteHandler` (114；`handle` 205)、`getExtractMapping` (72)、`extractToBody` (104) |
| search.js | 317 | 文档内文本搜索：包含/全词/邻近词/正则 | `search` (281)、`searchMatcher` (292；选项 `matchCase, matchDiacritics, mode, nearbyWords, acceptNode`)、邻近词双指针窗口 (240-280) 产出 `{range, excerpt, subRanges}` |
| tts.js | 519 | 文档内 TTS 标记源：`Intl.Segmenter` 词/句切分、SSML 块、高亮回调 | `TTS` 类（被 view.js:704 / TTSController.ts:918 导入）；fork：PDF 文本层句级分块 (163-188)、缩写处理 (24-29) |
| text-walker.js | 77 | DOM 文本节点遍历器，带可选节点过滤器（fork 新增 filter 参数，上游 PR #77） | `textWalker` |
| section-chunks.js | 235 | **fork 新增**。切分 >512 KB 的 section（`CHUNK_THRESHOLD` paginator.js:7）为可渲染块文档，用保持索引的占位符保证 CFI 有效 | `CHUNK_ATTRIBUTE` (13)、`splitSection`，commit 1a8bd29 (#126)（行号经 T-08 复审校正：18→13） |
| pdf.js | 1078 | PDF 书适配器（基于内嵌 PDF.js legacy 构建）：range transport、outline TOC、页标签、文本层、缩略图、重着色 | `makePDF` (861)、`book.resolveHref` (1016)、`book.splitTOCHref` (1024)、`book.getTOCFragment` (1038)、`book.isExternal` (1013) |
| mobi.js | 1306 | PalmDOC/MOBI6 + KF8 (AZW3) 解析 | `isMOBI` (481)、`MOBI extends PDB` (511)、`MOBI6` (689)、`KF8` (963)、`readMobiMetadata` (1300) |
| fb2.js | 356 | FictionBook 2（XML 或 zip 的 .fb2/.fbz） | `makeFB2` |
| comic-book.js | 154 | CBZ 页 + ComicInfo/zip 注释元数据 | `makeComicBook` |
| opds.js | 410 | OPDS 1/2 目录 feed 解析（fork：OPDS 2.0 WebPub 对齐、OPDS-PSE、混合 feed） | feed 解析器，被 `src/services/opds` 使用 |
| uri-template.js | 52 | RFC 6570 URI 模板（OPDS 搜索） | 模板展开 |
| dict.js | 241 | .dsl 词典解析器（上游 demo；**Readest 应用未使用**——应用有自己的词典栈，§5.8） | — |
| quote-image.js | 86 | 上游引文图生成器；**Readest 应用未使用**（应用自带 canvas 渲染，§5.3） | — |
| reader.js / reader.html | — | 上游 demo 阅读器；应用未使用 | — |
| vendor/ | — | zip.js、fflate.js、pdfjs（legacy 构建）——按 fork 提交 f087826 内嵌（WebKit 兼容第 4 项） | — |

应用侧导入统计（grep `apps/readest-app/src`）：epubcfi.js 30 处、fixed-layout.js 12、opds.js 9、overlayer.js 7、epub.js 6、progress.js 5、pdf.js 5、paginator.js 5、tts.js 4、text-walker.js 4、footnotes.js 4、section-chunks.js 3、search.js 2、uri-template.js 1、comic-book.js 1；mobi.js/fb2.js 在 `DocumentLoader` 内动态加载（document.ts:612-630）；dict.js 与 quote-image.js 零导入。

### 3.2 fork 增量（相对上游 johnfactotum/foliate-js）

方法：仅本地 git 历史（未联网）。作者边界：John Factotum（上游作者）262 个提交，最后为 `c49ded0` "Fix indentation"（2025-09-24）；Huang Xin（Readest, chrox）242 个；另有社区贡献者。`git rev-list --count c49ded0..HEAD` = **领先 254 提交**；无 merge 提交（上游经 cherry-pick/rebase 式吸收）。Readest 专项工作实际始于 2024-10-18（`f24e611` "Lazy loading of PDF documents (#37)(#38)"）与 WebKit 兼容大压缩提交 `f087826`（2024-10-30，29 项 enumerated patches：legacy pdfjs 构建、iframe 背景、TTS prev/next 同步、overlayer 缩放兼容等）。即 fork 实际于 2024-10 分化，同时持续吸收上游至 2025-09。[推断：c49ded0 是 fork 历史中最后一个 John Factotum 作者提交；上游是否有更晚未合并提交离线不可证（§10）。]

主要 fork 增量（据 log + 读码）：

- **fixed-layout.js**：上游文件（261 行，5fc72d1，2022）增长至 2148 行。Readest 增量：捏合缩放带锚点恢复、`panX` 横向平移 + iOS `lock-pan-x` 惯性锁（b1fe9d3, 1f77f38）、宽页载入时拼版重组（07a7e2d）、缩放滚动零缝隙（db0540b）、视口条带修剪（97e44bf）、`primaryIndex` 命名与侧跟随（08db610）、拼版页列上报（9f5736b）、非数值视口取页尺寸（5249046）、经典滚动条适配（073f044）。
- **paginator.js**：View Transitions API 分层翻页——`slide`/`curl` 翻页风格带拖拽擦洗暂停、Apple Books 式编排（readest#555；常量 paginator.js:194-259、`VIEW_TRANSITION_CLASSES` 202、`#viewTransitionTurn` 3469）；超长章分块渲染经 section-chunks.js（#126）；拼版 `column-gap` 属性（c7948fe）；拖拽跟随滑动机制（`RELEASE_VELOCITY_WINDOW_MS` 等 210-267）；eink 属性路径；`gpu-composite` 宿主属性（iOS ProMotion，paginator.js 注释，应用于 FoliateViewer.tsx:830）；竖排书写列序处理（paginator.js:616, 949-908）；书级页进方向（444be90）。
- **section-chunks.js**：新模块（#126，见 3.1 清单行）。
- **pdf.js**：页缩略图（#113）、保留嵌入照片的平滑重着色（#112）、移动端解码尺寸上限 + 按页取解码数据（#110）、文本层间隙保持选区（#115）、缩略图渲染失败释放页（#114）、按位置定位嵌入图（#117）。
- **epub.js**：未闭合 void 标签 → 闭合 + XML 重解析并回退 HTML（cb3896f）、archive 缺失的 spine 项按空文档（bb2b1da）、未声明封面回退（getCover, epub.js:1417-1430）、Duokan `~slim` 封面变体（1731485）、有界并发 `loadReplaced`（f48400d）、未声明音视频解析（c319c90）、`<meta name="cover">` href 形式（a1913ac）。
- **overlayer.js**：每行一条高亮条带（OCR 文本层）`mergeLineRects` (25)；高亮帽保持在矩形所在页（9e05bf2）。
- **epubcfi.js**：保留结束于子节点之间的 range（ac528ac）；`cfi-inert`/`cfi-skip` 属性过滤 (194-195)。
- **tts.js**：短词后即断句（3e8d6fd）、块遍历从自身起点开始（#127）、PDF 文本层句级切分（162-188, ec7e16a）。
- **search.js**：nearby-words 模式 + 逐词 `subRanges`（view.js:609-616 消费）。
- **opds.js**：OPDS 2.0 WebPub 对齐 + OPDS-PSE（#14）、Atom id/updated 提取（#10）、混合导航/出版物 feed（348a64a，历史首个 conventional commit）、Dublin Core 日期优先（#88）。
- **view.js**：CursorAutohider 带选区保护（128-166）、按 CFI 的搜索结果去重（662-670）、块感知 overlayer 选择（443-458）。

Tauri fork 在应用侧的可见面：前端经 `@tauri-apps/api` invoke 消费（如 Rust EPUB 预取桥 `tryNativePrefetchEpub`，document.ts:572-577，及 `@/utils/tauriEpubBridge`）；fork 内部见 §7.4。

### 3.3 定位模型（CFI 子集 + 字符偏移）

- 引擎定位主干为 **EPUB CFI 子集**：`epubcfi.js` 提供 `parse` (107) / `fromRange` (325) / `toRange` (333) / `buildRange` (139) / `compare` (163) / `collapse` (134) / `joinIndir` (16)；非 EPUB 格式用 `fake` (376) 伪 section CFI（view.js:502 路径）；Calibre 互转 `fromCalibrePos` (383) / `fromCalibreHighlight` (389)；`isCFI` 正则 (9)。fork 另加 `cfi-inert`/`cfi-skip` 节点过滤 (194-195)。
- 进度层将 CFI 映射为分数/LOC/时间：`SectionProgress`（progress.js:173，`sizePerLoc=1500, sizePerTimeUnit=1600` 构造于 view.js:252）、`TOCProgress` (18)、`PageProgress` (62)。
- 运行时实证（[ui-study](ui-study.md) §3）：0.12.16 Windows 实测高亮落盘 config.json 的 booknotes 形如 `{id, type:annotation, color:yellow, style:highlight, text, cfi:"epubcfi(/6/4!/4/12,/1:7,/1:31)"}`——即 **EPUB CFI + 字符偏移级区间锚定**（`/1:7` 至 `/1:31`），与上述 `fromRange`/`buildRange` 链路吻合。这是与"章+段+逐字全文锚"型阅读器迁移设计时的关键对照（[ui-study](ui-study.md) §8）。
- relocate 事件负载：`{reason, range, index, fraction, size}`（paginator.js:3746-3793）→ `View.#onRelocate`（view.js:341-350）算 `progress`/`tocItem`/`pageItem`/`cfi`，存 `lastLocation` 并 `history.replaceState(cfi)`。
- PDF 定位为页索引 href（pdf.js:1016-1038），经 view.js:501-514 路径映射为 fake/section CFI；TXT/MD/HTML 为转换后书的 section CFI（§4 矩阵）。

### 3.4 阅读入口 → 开书链路（含格式分发与进度恢复）

1. 入口：`apps/readest-app/src/app/reader/page.tsx:39` 渲染 `Reader`；Tauri 专属路由（"This is only used for the Tauri app in the app router"，page.tsx:35-36）。书 id 自 pathname 解析于 `ReaderContent.tsx:116`（`ids || searchParams?.get('ids') || pathname.split('/reader/')[1]`），多书键以 `BOOK_IDS_SEPARATOR` 分隔（services/constants.ts；消费于 FoliateViewer.tsx:861-862）。
2. `ReaderContent.tsx:145-162`：逐键 `readerStore.initViewState(envConfig, id, key, isPrimary)`；失败 → `setErrorLoading(true)` + `eventDispatcher.dispatch('toast', {message: 'Unable to open book', type: 'error'})` → `closeReaderWindowOrGoToLibrary`（ReaderContent.tsx:147-160）。
3. `FoliateViewer.tsx` 挂载 `BrightnessOverlay` + 容器 div，托管自建的 `<foliate-view>`；组件定义于 FoliateViewer.tsx:125。应用无 "BookView" 组件——foliate 宿主即 `FoliateViewer.tsx`，外裹 `ReaderContent.tsx`、再外裹 `Reader.tsx`。
4. 书库侧导入/管理经 `services/bookService.ts`（`importBook` bookService.ts:500；页数 `getBookDocPageCount` bookService.ts:736）。书库点击导航至 `/reader/{hash}`（路由消费于 ReaderContent.tsx:116）。[推断：导航触发点——`src/app/library` 的 BooksGrid 点击处理函数未读。]
5. `readerStore.initViewState`（readerStore.ts:180）：自 `libraryStore` 解析 book，触发 `appService.loadBookConfig`（readerStore.ts:232，每书 `{hash}/config.json`——文件名 utils/book.ts:68），触发 `services/annotation` 导入（readerStore.ts:237）。
6. 内容获取：`appService.loadBookContent(book)` 与 `appService.resolveNativeBookFilePath(book)` 并行竞速（readerStore.ts:264-270）。文件解析：`resolveBookContentSource`（bookService.ts:51，用于 1061/1065/1085）→ `managed | external | url | missing`；`openBookFileContent`（bookService.ts:1078）为 URL 源传 `fetcher`。Tauri 上 `nativeAppService.openFile` 返回 `NativeFile`（Tauri IPC 分片读）或 `RemoteFile`（自定义协议/URL fetch）——nativeAppService.ts:318-369，含 asset-scope 回退 NativeFile（348-354）与 iOS picker-Inbox NativeFile 说明（357-359）。Feed 书（RSS）走 `openFeedBookDoc`（readerStore.ts:254-259）；OPDS-PSE 流式 `openPseStreamBook`（249-253）。
7. 格式分发：`new DocumentLoader(file, {nativeFilePath, widePages}).open()`（readerStore.ts:273-276）——完整矩阵见 §4。Tauri 上 loader 将 zip 中央目录读取（document.ts:273-278）与 Rust EPUB 预取 RPC `tryNativePrefetchEpub`（document.ts:571-577，预膨胀 OPF/nav/ncx 文本 + 尺寸；"~1.5s → ~0.3s on iOS"，document.ts:196-199）重叠执行。
8. 解析后：第三方注释导入 `getAnnotationProviders()`（readerStore.ts:286-301）；过滤非法 booknotes（303）；EPUB nav 缓存载入/计算/持久化（`loadBookNav`/`computeBookNav`/`saveBookNav`，services/nav；readerStore.ts:306-321）；`updateToc` 做 TOC 排序/中文变体转换（322-326）；元数据规范化（327-353）；`setBookData(bookKey, ...)` 写入 `bookDataStore`。
9. 视图创建：`bookData.bookDoc && viewSettings` 就绪后 `ReaderContent` 渲染 `FoliateViewer`（ReaderContent.tsx:446）。`FoliateViewer.openBook` 副作用（FoliateViewer.tsx:729-891）：
   - `await import('foliate-js/view.js')`；`document.createElement('foliate-view')` 包以 `wrappedFoliateView`（738）；append 到容器（740）。
   - Writing-mode → 书方向覆盖自每书 `viewSettings`（742-752，helper `getBookDirFromWritingMode/getBookDirFromLanguage` 于 utils/book）。
   - FXL：按设置置 `rendition.spread` + `setCoverSpread`（754-757，utils/spread）。
   - `await view.open(bookDoc)`（759）→ `View.open`（view.js:243）构建 `SectionProgress`/`TOCProgress`/`PageProgress`（view.js:252-262），选渲染器：`rendition.layout === 'pre-paginated'` → 动态导入 fixed-layout.js + `<foliate-fxl>`（264-267），否则 paginator.js + `<foliate-paginator>`（268-271）；绑定 `load`/`relocate`/`create-overlayer` 渲染事件（273-276）；`book.sections[].mediaOverlay` 存在时接线 media-overlay 高亮（280-306）。
   - `book.transformTarget` 监听：逐书脚本白名单（`viewSettings.allowScript`，766-776）、`fonts/` href 自定义字体 blob 替换（777-791）、`getDocTransformHandler`（797，transformService/transformers 管线）。
   - 初始样式：`view.renderer.setStyles?.(getStyles(viewSettings, undefined, getLoadedFonts()))`（798）；`applyTranslationStyle`（799）。
   - 渲染器属性：`animated`、`autohide-cursor`、翻页属性（`applyPageTurnAttributes`，823）、`gpu-composite`（iOS，829-831）、`eink`（832-836）；FXL：`zoom/spread/scale-factor/scroll-gap/lock-pan-x` + 恢复 `panX`（838-846）；重排：`max-column-count`、`max-inline-size`、`max-block-size`（848-851）；`applyMarginAndGap()`（852）。
10. 进度恢复：`lastLocation = overrideLocation ?? config.location`（865；`?cfi=` 深链覆盖 854-863，仅主书）；`await view.init({ lastLocation })`（867）→ `View.init`（view.js:326）→ `resolveNavigation` → `renderer.goTo`。无存档位置 → `view.goToFraction(0)`（869）。深链视图标记 `previewMode`，进度写入方跳过（871-879，readerStore `setPreviewMode`）。
11. 持续进度：渲染器 `relocate` → paginator 发射 `{reason, range, index, fraction, size}`（paginator.js:3746-3793）→ `View.#onRelocate`（view.js:341-350）→ view `relocate` → `useFoliateEvents`（hooks/useFoliateEvents.ts:31-38）→ `FoliateViewer.docRelocateHandler`（FoliateViewer.tsx:612）→ `readerProgressStore.setProgress`（store/readerProgressStore.ts:78；独立 store 以避免重绘卡顿，见其头注 1-63）。
12. 持久化端点：`useProgressAutoSave`（hooks/useProgressAutoSave.ts:9）防抖约 1.5s（1000ms debounce + 500ms timeout，56-63）→ `persistProgress`（31-48；跳过 previewMode、跳过未变化位置以保护云同步顺序 #4222）→ `bookDataStore.saveConfig`（store/bookDataStore.ts:147-179：急切每书写 `appService.saveBookConfig` 于 179 + 节流 `library.json` 汇总写）→ `BookSvc.saveBookConfig`（bookService.ts:1142-1160）→ `fs.writeFile('{hash}/config.json', 'Books', serializeConfig(...))`。`visibilitychange`/`pagehide` 立即冲刷（Android WebView 杀进程 #5859，83-106）。云端：`useProgressSync` 推/拉压缩配置（`pushConfig` → `syncConfigs([...], bookHash, metaHash, 'push')`，useProgressSync.ts:81-97），首拉带退避重试（23-25）；KOReader 同步经 `useKOSync`/kosyncProgress；ABS 同步经 `useABSProgressSync`。存储位置：app 数据目录 `Books/` 前缀下每书 JSON（Tauri fs 前缀解析在 src-tauri；`NativeFile`/fs 抽象在 services/nativeAppService.ts）。

离线/失败分支：空文件 → `Error('File is empty')`（document.ts:527）；损坏 zip → 重抛 "Unsupported or corrupted book file"（document.ts:634-636）；`resolveBookContentSource` 缺失 → `BookFileNotFoundError`（bookService.ts:1087）；打开失败 → "Unable to open book" toast + 回书库（ReaderContent.tsx:147-160）；Rust 预取失败不致命（`.catch(() => undefined)` document.ts:569，null 回退 266-270）；nav 缓存写失败仅记日志（317）。

### 3.5 视图设置管线（设置 store → foliate view）

- 每书 `ViewSettings` 存于 `readerStore.viewStates[key].viewSettings`（`getViewSettings`/`setViewSettings`，readerStore.ts:424-425），开书时由 `config.viewSettings` 合并 `settings.globalViewSettings`（FXL 格式再叠加 `DEFAULT_FIXED_LAYOUT_VIEW_SETTINGS`）播种（bookService.ts:1124-1134）。
- 设置 UI：`src/components/settings/` 各面板——LayoutPanel.tsx、ControlPanel.tsx（字体/段落）、ThemePanel.tsx、MiscPanel.tsx；底栏快捷控制在 `app/reader/components/footerbar/`（FontLayoutPanel.tsx、ColorPanel.tsx、NavigationPanel.tsx）。
- 流程两阶段（均在 LayoutPanel.tsx 有证）：
  1. 持久化：`setViewSettings(bookKey, viewSettings)`（LayoutPanel.tsx:510, 523）→ readerStore → 稍后经 `saveConfig` 落 config.json。
  2. 即时应用：直写渲染器属性——`view?.renderer.setAttribute('gap', ...)`（294）、`'flow' = 'scrolled'`（296）、`'column-gap'`（305）、`'max-column-count'`（316）、`'max-inline-size'`（317/325）、`'max-block-size'`（332）；样式重算 `view.renderer.setStyles(getStyles(...))`（FoliateViewer.tsx:1019 设置变更副作用）。
- `getStyles`（utils/style.ts:1115-1186）合成单条 CSS：`@namespace epub`（1184，排序修复 #4438 于 1179-1183）+ 自定义 `@font-face`（1163, 1194-1204）+ 页面布局（边距 px、书写模式/竖排，1123-1131）+ 段落布局（lineHeight/wordSpacing/letterSpacing/textIndent/justification/hyphenation——仅 `!useBookLayout` 时，1132-1144）+ 字体样式（serif/sans/mono/default/CJK、基础字号、最小字号、字重、overrideFont，1145-1155）+ 颜色样式（overrideColor、图片反色、themeCode、背景纹理、eink，1164-1170）+ 翻译/warichu/ruby/CJK 行流/对话高亮/用户样式表（1171-1178, 1185）。主题码来自 `getThemeCode()`/themeStore。
- 书籍 CSS 透传：`transformStylesheet`（utils/style.ts:1221）为移动端字号缩放重标定作者 CSS、钉住居中文本缩进等；固定版式 CSS 不动（1228-1231，#5649）。`paginator.setStyles`（paginator.js:4295）注入每个已渲染 section 的 iframe `<style>` 并重展开视图；paginator 在 iframe `load` 前注入使首帧即用正确字体（style.ts:1156-1162 注释）。
- 书内容变换：`transformContent`（services/transformService.ts）+ transformers `services/transformers/`——style.ts、punctuation.ts、simplecc.ts（中文变体）、footnote.ts、whitespace.ts、warichu.ts、sanitizer.ts、epubSwitch.ts、language.ts；经 `book.transformTarget` 的 `data` 事件挂接（FoliateViewer.tsx:797）。

### 3.6 渲染 / 分页模型（引擎）

- 重排：`<foliate-paginator>` shadow root = grid（`#top > #background/#header/#container/#footer`，paginator.js:1577-1607）。每 section 独立 iframe（`View` 类 paginator.js:722；载入期间隐藏但参与布局，760-762）。分页 = CSS 多栏：`columnize`（975）在 iframe 文档上设 `column-width/column-gap/column-fill:auto`，再靠滚动栏带翻页（`#scrollToPage` 3516、`#scrollTo` 3329）；页数 = 内容尺寸 ÷ 栏尺寸（1226-1232）。滚动模式：`#container` 变滚动盒（`:host([flow="scrolled"])` CSS 1681-1700）、`scrolled()` 布局（912）、跨 section 连续填充带预载；`no-continuous-scroll` 单节渲染（observedAttributes 1504）。超长节按块渲染（`#units`，paginator.js:1507-1513；section-chunks.js）。[ui-study](ui-study.md) §2 实测：长章 iframe 宽 133,280 px、相邻章屏外预停靠——与该模型一致。
- 翻页动画：`none` 用原生滚动/transform；View Transitions 分层 `slide`/`curl`（194-208, 3469）；竖向翻页两段式 slide（`slideTurnAnimation`，160-192）；`animated`/`eink`/`gpu-composite` 属性开关。
- 固定版式：`<foliate-fxl>`（fixed-layout.js:292）——逐拼版页瓦片、拼版自动重组、缩放（`zoom`、`scale-factor`）、平移（`panX`、`lock-pan-x`）、webtoon 纵向条带（`scroll-gap`、`scroll-direction`）。
- 选区（引擎侧）：iframe 内标准 DOM Selection；应用经 `useTextSelector` 监听（跨块/跨页选区，基于 `getContents()`；CFI 经 `view.getCFI(index, range)`，useTextSelector.ts:261/501）。
- 覆盖层：每文档 `Overlayer` 由 `View.#createOverlayer`（view.js:459-490）经渲染器 `create-overlayer` 事件（275-276）创建；`hitTest` 点击 → `show-annotation`（461-466）；悬停指针光标（472-483）。锚为 CFI，按文档解析为 DOM Range——`addAnnotation`（view.js:390）解析 value → `{index, anchor}` → `overlayer.add(value, range, drawFn)`，绘制函数由应用经 `draw-annotation` 监听提供（Annotator 接 `getHighlighterStyle` → `Overlayer.highlight/underline/squiggly/bubble` 按样式分派，utils/annotatorUtil.ts:395-425）。搜索命中预渲染为 `Overlayer.outline`（view.js:403）。
- 脚注弹层（引擎部分）：`FootnoteHandler.handle`（footnotes.js:205）以 `isFootnoteReference(a)` 是/疑似启发式判定；创建**第二个一次性 `<foliate-view>`**，`view.open(book)`、`renderer.goTo({index, anchor})`，`load` 后抽取注释（`getExtractMapping`/`extractToBody` footnotes.js:72/104）并派发 `render`（116-203）。
- TTS 标记源（引擎部分）：`View.initTTS`（view.js:697-707）自主渲染节构建 `new TTS(doc, textWalker, nodeFilter, highlighter, granularity)`；高亮默认 `renderer.scrollToAnchor(range, true)`。`startMediaOverlay`（708）服务 EPUB media overlays。（应用路径实际用 TTSController 自建引擎 TTS，见 §5.6；`View.initTTS` 疑为 API/演示兼容保留 [推断]。）

### 3.7 引擎内失败 / 离线分支汇总

- 书打开："File is empty"（document.ts:527-529）；"Unsupported or corrupted book file"（632-637）；引擎嗅探 `UnsupportedTypeError`（view.js:124）；内容源缺失 → `BookFileNotFoundError`（bookService.ts:1087）；UI toast "Unable to open book" + 自动回书库（ReaderContent.tsx:147-160）。
- Rust 预取尽力而为，与中央目录读并行；失败绝不阻塞打开（document.ts:565-578）。
- 进度保存：防无变化写入以保护服务端同步顺序（#4222，useProgressAutoSave.ts:17-48）；visibilitychange/pagehide 冲刷防后台杀进程（#5859，83-106）；退出时 library.json 冲刷失败可容忍（113-120）。
- 云同步首拉退避重试"survives server timeouts"（useProgressSync.ts:23-25）；预览/深链视图永不写进度（FoliateViewer.tsx:871-879、useProgressAutoSave.ts:34）。
- EPUB 引擎内健壮性：XML 解析错误带 URI 抛出（epub.js:1279-1282）；空 TOC nav → NCX 回退含无 href nav 列表（1353-1367）；spine 项缺失 → 过滤 null section（1313-1341）/载入时空文档（loadDocument 1388-1392）；未声明封面回退（1417-1430）。
- 搜索：逐节进度增量产出；重叠 CFI 去重（view.js:660-670）；`clearSearch` 幂等。
- TTS：引擎失败重试——同文本重读连续失败 3 次即停（TTSController.ts:68-93 注释）；narration 节空 SMIL 跳过并警告（899-908）；任何 await 前先做 WebKit 音频解锁（useTTSControl.ts:968-977）；Edge wss→https 代理回退（providers/edge.ts:23-27）；未登录仅获未鉴权目录（readest.ts:315-316）。
- 脚注抽取失败拒绝并报 'Failed to locate footnote content'（footnotes.js:160/185）；弹层启发式避免误导航（iframeEventHandlers.ts:564-588、footnoteHeuristics.ts）。
- PDF：WebKit 16 worker polyfill `transferToFixedLength` 否则白页（#6015，document.ts:224-232）；移动端 GPU 杀进程防护——缩小解码图（#6521，229-253）；LRU 页缓存带清理（940-958）。
- View Transitions 不支持/失败 → 跳过 transition 清理路径（paginator.js destroy 4333-4342）；过期动画防护（`isStale()` 174/183）。

---

## 4. 解析与资源

### 4.1 格式分发矩阵

解析分发发生两次：`makeBook`（view.js:82-126，引擎对裸文件的回退）与 `DocumentLoader.open`（document.ts:524-641，应用路径——权威；叠加 TXT→EPUB 转换、MD、HTML、原生预取、宽页漫画）。渲染器按 `rendition.layout` 选择：`pre-paginated` → `<foliate-fxl>`，否则 `<foliate-paginator>`（view.js:264-271）。应用格式枚举 `EXTS`（document.ts:150-169）。

| 格式 | 解析模块 | 渲染器 | 定位 | 选区 | 搜索 | TTS | 标注 | 备注 |
|---|---|---|---|---|---|---|---|---|
| EPUB | `foliate-js/epub.js` `new EPUB(loader).init()`（document.ts:603-605；引擎孪生 view.js:105-106）；zip.js loader；Rust 预取桥（document.ts:571-577） | paginator（或 `rendition.layout==='pre-paginated'` 时 fxl，view.js:264） | 真 spine CFI：`sections[index].cfi`（epub.js:1333）+ `CFI.fromRange` | 是 | 是 | 是 + media overlays（view.js:280-306，MediaOverlayTTS） | 是 | 加密 IDPF/Adobe（epub.js:796-813）；nav/ncx TOC 回退（epub.js:1343-1367） |
| PDF | `foliate-js/pdf.js` `makePDF`（document.ts:607-611）；pdfjs-dist **legacy** 构建自 foliate-js node_modules 拷入 `public/vendor/pdfjs`（package.json scripts 55-64）；worker blob 带 WebKit `transferToFixedLength` polyfill + 移动端图片缩小（document.ts:224-266） | fxl（makePDF 置 `rendition.layout='pre-paginated'`，pdf.js:886-891） | 页索引 href；`resolveHref`/`splitTOCHref`/`getTOCFragment`（pdf.js:1016-1038）；CFI fake/section（view.js:501-514 路径） | 是——文本层，跨间隙选区为 fork 修复（#115） | 是 | 是——fork 句级分块适配 PDF 文本层（tts.js:162-188） | 是 | outline TOC、页标签 → pageList（pdf.js:914-924）；RTL ViewerPreferences → `book.dir='rtl'`（pdf.js:904-909） |
| MOBI / AZW | `foliate-js/mobi.js` `isMOBI` + `new MOBI({unzlib: fflate.unzlibSync}).open`（document.ts:612-615） | paginator | `CFI.fake.fromIndex` 式 section CFI（view.js:502） | 是 | 是 | 是 | 是 | MOBI6；PDB 容器（mobi.js:486） |
| AZW3 (KF8) | 同 MOBI 模块；`KF8` 类（mobi.js:963）；格式按扩展名标注（document.ts:616-626） | paginator | section CFI（KF8 每 spine 带 `cfi`——fork 317051e "Add cfi for section fragments"） | 是 | 是 | 是 | 是 | KF8 transform target（fork f2d3215） |
| CBZ | `foliate-js/comic-book.js` `makeComicBook`（document.ts:581-595）；宽页拼版测量经 `utils/spread`（document.ts:583-591） | paginator 或 fxl（按书 rendition）；图片页 | section 索引定位 | 有限（图片） | 否（图片页——`createDocument` 产出图片文档） | 否 | 有限（可经 section CFI 做页级标注）[推断] | ComicInfo/zip 注释元数据（fork f087826 第 18 项） |
| FB2（裸文件） | `foliate-js/fb2.js` `makeFB2`（document.ts:627-630） | paginator | section CFI | 是 | 是 | 是 | 是 | — |
| FBZ（.fb2.zip） | fb2.js 作用于解压 blob（document.ts:596-601；引擎孪生 view.js:97-103） | paginator | section CFI | 是 | 是 | 是 | 是 | — |
| TXT | 应用转换器 → 内存 EPUB：`TxtToEpubConverter`（utils/txt）后递归 `DocumentLoader.open()`（document.ts:549-553）；导入路径存转换后 EPUB（document.ts:531-535 注释） | paginator | 转换后书的 EPUB CFI | 是 | 是 | 是 | 是 | — |
| MD / markdown | `makeMarkdownBook`（utils/md）→ HTML book doc（document.ts:539-542） | paginator | section CFI | 是 | 是 | 是 | 是 | 运行时渲染，不做 EPUB 转换 |
| HTML / .mht | `makeHtmlBook`（utils/html，Readability 式）（document.ts:545-548） | paginator | section CFI | 是 | 是 | 是 | 是 | 保存网页支持 |
| ABS（audiobookshelf 电子书流）/ OPDS 音频 / BOOKORBIT / OPDS-PSE 流 | `openPseStreamBook` / `openFeedBookDoc`（readerStore.ts:249-259）；EXTS 内合成格式（document.ts:162-168） | paginator（流式 sections） | feed/stream 定位 | 是 | 是 | 是 | 是 | AUDBOOK 有声书另走 `services/audiobookshelf`（播放路由 `app/player`） |
| 目录（解包 EPUB） | 仅引擎：`makeDirectoryLoader`+EPUB（view.js:85-89） | paginator | EPUB CFI | 是 | 是 | 是 | 是 | demo/边缘路径 |

运行时矩阵交叉验证：[ui-study](ui-study.md) §5 逐格式实开——EPUB/PDF/TXT/CBZ/AZW3/FB2 全部打开成功（CBZ 目录=图片文件列表、AZW3 中文经 Kindle 管线正常）；MOBI 无语料未测；MD/HTML 同文本管线家族未单独打开。

### 4.2 资源 / CSS / 字体处理

- 资源加载（EPUB）：epub.js `Resources`/`Loader` 做 blob 替换式资源加载（§3.1 清单行）；未闭合 void 标签修复与 XML 重解析（fork cb3896f）；未声明音视频解析（fork c319c90）；有界并发 `loadReplaced`（fork f48400d）。
- 自定义字体：`book.transformTarget` 上对 `fonts/` href 做 blob 替换（FoliateViewer.tsx:777-791）；`getStyles` 注入自定义 `@font-face`（utils/style.ts:1163, 1194-1204）；桌面系统字体清单为各 OS 硬编码表（WINDOWS_FONTS/MACOS_FONTS/LINUX_FONTS/IOS_FONTS/ANDROID_FONTS，src/services/constants.ts:645-906）[推断：桌面清单静态，未发现运行时枚举]；移动端经 native-bridge `get_sys_fonts_list()`（plugins/tauri-plugin-native-bridge/src/desktop.rs:110）。
- 样式合成与注入：`getStyles`（utils/style.ts:1115-1186，详见 §3.5）；书作者 CSS 经 `transformStylesheet`（1221）重标定，FXL CSS 不动（1228-1231）；`paginator.setStyles`（paginator.js:4295）注入各 section iframe 并在 `load` 前注入保证首帧字体正确（style.ts:1156-1162）。
- 内容变换管线：`transformContent` + transformers（style/punctuation/simplecc/footnote/whitespace/warichu/sanitizer/epubSwitch/language，services/transformers/），经 `book.transformTarget` `data` 事件挂接（FoliateViewer.tsx:797）。
- PDF 资源：legacy pdfjs 构建内嵌于 `public/vendor/pdfjs`（package.json scripts 55-64）；worker blob + WebKit polyfill（document.ts:224-266）；fork 增量：缩略图/重着色/解码上限（§3.2）。

---

## 5. 选区 / 定位 / 注释链路

### 5.1 链路一：选区 → 标注 → 持久化

1. 选区：`useTextSelector`（挂载于 FoliateViewer）监听 iframe 选区事件；构建 `{text, index, range, cfi (view.getCFI), segments (跨页分段), popup?}`（useTextSelector.ts:244-261, 501）。注入式 UI 事件经 `iframeEventHandlers.ts`（`handleClick` 等，FoliateViewer.tsx:69-83 导入）。
2. 弹层：`Annotator.tsx` 在选区上渲染 `AnnotationPopup`（annotator/AnnotationPopup.tsx）；快捷操作含高亮、笔记、词典、翻译、引文卡、校对（Annotator.tsx:1191-1211 switch，'quotecard' case 在 2586）。
3. 创建/更新：`handleHighlight(update?, highlightStyle?)`（Annotator.tsx:1577）——逐跨页分段构建 `BookNote` `{id: uniqueId(), type:'annotation', cfi, style, color, text, note:'', page, createdAt, updatedAt}`（BookNote 字面量 1607-1617，T-08 复审校正：1596-1604 为相邻 toggle 逻辑）；切换/改样式合并或墓碑化（`deletedAt`）既有记录（1608-1652 区段内）；**立即渲染** `views.forEach(view => view.addAnnotation(annotation))`（1626/1640/1653）——调 `View.addAnnotation`（view.js:390）解析 CFI 并发 `draw-annotation`；FoliateViewer/Annotator 的绘制监听执行 `draw(Overlayer.highlight|underline|squiggly|bubble, {color, writingMode, vertical...})`（annotatorUtil.ts:409-425）。笔记渲染为 `NOTE_PREFIX + cfi` 气泡覆盖层（`NOTE_PREFIX` view.js:9；Annotator.tsx:1353）。
4. 持久化：`updateBooknotes(bookKey, annotations)`（bookDataStore 汇流 `config.booknotes` 全部写入——bookDataStore.ts:95 注释 "Every write to config.booknotes funnels through this store"）→ `saveConfig(envConfig, bookKey, config, settings)`（Annotator.tsx:1666-1668）→ config.json（与 §3.4 第 12 步同端点）。云端笔记同步：`useNotesSync`、`useReadwiseSync`、`useNotionSync`、`useBookOrbitNotesSync`、`usePageboundSync`、hardcover（hooks 目录）。
5. 运行时实证：[ui-study](ui-study.md) §3 全绿——精确拖选逐字命中、弹层全操作（笔刷/复制/笔记/搜索/词典/翻译/朗读/校对 + 高亮·下划线·波浪线 + 5 色 + 「应用到本书所有匹配位置」）、批注落盘（note 字段 + 行尾批注图标 + 侧栏列表）、关闭重开全量恢复（位置 CFI + 黄色高亮 + 批注图标 + 书签 + 深色主题，u03-restored-page.png）。落盘 booknotes 形状（config.json 实读）：`{id, type:annotation, color, style, text, cfi:"epubcfi(/6/4!/4/12,/1:7,/1:31)"}`；书签同数组存 `{type:bookmark}`。

### 5.2 链路二：重开恢复

开书后 Annotator 副作用重加全部注释：`Promise.all(annotations.map(a => view.addAnnotation(a)))` + 笔记带 `NOTE_PREFIX`（Annotator.tsx:1351-1353）；memoized `buildAnnotationIndex(config.booknotes)`（1325-1338，`app/reader/utils/annotationIndex.ts`）避免逐次翻页过滤；section 渲染时 overlayer 重建由 `View.#createOverlayer` 重跑 `addAnnotation`（搜索结果，view.js:485-486）+ 应用在 `create-overlay`/load 时重加注释承接。

### 5.3 链路三：导出与引文卡

- 导出：`ExportMarkdownDialog.tsx` + `app/reader/utils/noteMarkdown.ts`（`parseNoteMarkdown` noteMarkdown.ts:27）——markdown/txt 导出注释；导入经 `ImportAnnotationsDialog.tsx` + `services/annotation/` providers。运行时实证：[ui-study](ui-study.md) §3 实测导出 Markdown/纯文本/JSON 三格式 + 字段选项 + 预览，导出文件含摘录/笔记全文 + **每条 `readest://book/<hash>/annotation/<id>?cfi=…` 深链**（跨应用回跳锚）。
- 引文卡：foliate `quote-image.js` **不使用**；应用自渲染 DOM 卡并以 `quoteCardToPng`/`renderQuoteCard` 栅格化（utils/quoteCardRenderer.ts；QuoteCardDialog.tsx:13-18），样式来自 `utils/quoteCard.ts`，自 Annotator 'quotecard' 触发（Annotator.tsx:2586）。

### 5.4 链路四：书内搜索

`sidebar/SearchBar.tsx`——选项存于每书 `config.searchConfig: BookSearchConfig`（types/book.ts:588-600）：`scope: 'book'|'section'`、`mode`（contains/whole-words/nearby-words/regex）、`matchCase`、`matchDiacritics`、`nearbyWords`。执行：`currentView.search({...searchConfig, query: term, results})` 异步迭代（SearchBar.tsx:293）→ `View.search`（view.js:633）建 `searchMatcher(textWalker, opts)`（search.js:292）→ 逐节 `createDocument()` 遍历文本节点（`#searchBook` view.js:622）；每命中 → `getCFI`（nearby-words 另产 `subRanges` CFI，611-616）→ 以 `SEARCH_PREFIX + cfi` 加 `Overlayer.outline` 覆盖层（view.js:392-404, 662-670）；逐节进度事件产出 `{progress}`（628-630）。清除：`clearSearch` 移除全部 `SEARCH_PREFIX` 覆盖层（692-696）。结果间导航：`useSearchNav` hook + `SearchResults`/`SearchResultsNav` 组件。运行时实证：[ui-study](ui-study.md) §3——oracle（重复句恰 3 处）**恰 3 结果**，摘录红标、点击跳转、页内全命中红框 + 底部浮动导航（u03-jump-result2.png）。

### 5.5 链路五：跨库搜索（SQLite）

`services/librarySearchService.ts` `createLibrarySearchSession`（300）维护每书 SQLite 索引库（`indexDbs` map，304-370），由 `librarySearchIndex.ts` + `librarySearchWorker.ts`（worker）构建；UI 在书库 `BooksGrid`/命令面板。阅读器侧深链：搜索结果打开 `/reader/{id}?cfi=...&highlight=search`，FoliateViewer 显示瞬态高亮（`showTransientHighlight`，FoliateViewer.tsx:881-886，utils/transientHighlight.ts:107）。

### 5.6 链路六：TTS

1. 入口：ViewMenu/TTSControl 派发 `tts-speak` → `useTTSControl.handleTTSSpeak`（useTTSControl.ts:207）。启动（useTTSControl.ts:940-1050）：解锁音频（手势上下文 AudioContext unlock，968-977）、`new TTSController(appService, view, !!user.id, preprocessSSMLForTTS, handleSectionChange)`（989-994）、设 skip-inline-annotations、自定义 TTS 服务、bookKey、配对有声书；认领 `ttsSessionManager`（后台/媒体会话，1001-1011）；`useNarration` 偏好（1024）；`await ttsController.init()`（1025）后 `initViewTTS(ttsFromIndex)`（1031）；高亮选项 + 粒度（1036-1041）。
2. 逐节源：`TTSController.#initTTSForSection`（TTSController.ts:837）：narration（EPUB media-overlay）节 → `MediaOverlayTTS`（889-898）；否则直构引擎源——`const {TTS} = await import('foliate-js/tts.js')`、`new TTS(doc, textWalker, createTTSNodeFilter(), this.#getHighlighter(), granularity)`（918-928；CJK 默认 'sentence' 粒度，921）。注意：controller **不调用** `view.initTTS`，而是自建引擎 TTS 并赋 `this.view.tts`（928）。文档源优先取当前渲染节文档保证高亮同一性，否则经变换管线重放（871-880）。高亮器 = `Overlayer.highlight` 式绘制（TTSController.ts:158）在 iframe 内画句/词标记。
3. 音源/引擎（`services/tts/`，详见 §8）：`EdgeTTSClient`（Microsoft Edge wss，https-proxy 回退策略——providers/edge.ts:23-27）、`WebSpeechClient`（系统语音）、`NativeTTSClient`（OS 原生 TTS 经 Tauri）、Readest Voice 付费（providers/readest.ts：GPU worker 走 `/api/tts/readest/stream` + 任务队列 `/api/tts/readest/jobs`，目录缓存 localStorage `readest-voice-catalog` 117-131；登录门控 `token ? fetchWithAuth : fetch` 316——token 为 Readest 账户 auth token，来自 `useAuth`/cloudService，非本地 key 文件）、`openaiCompatible.ts`（用户自配 OpenAI 兼容端点；`customTTSStore.ts`）。音频输出：`WebAudioPlayer`/`NativeAudioPlayer`；缓存 `BufferedTTSClient` + sqlite/opfs 缓存仓（providers/sqliteCacheStore.ts、opfsPackFs.ts）；下载 `TTSDownloader`/`ttsDownloadManager` + `ttsDownloadStore` 供离线章节。
4. 播放面：`tts/TTSControl.tsx` 条 + `TTSMiniPlayer`/`TTSPlayerSheet`/`TTSLyricsView`（歌词经 `useTTSLyrics` + `SectionTimeline` 仅 Edge 的分块时钟，TTSController.ts:960-965 附近）；句子着色 `sentenceTint`（useTTSControl.ts:1037）；后台播放经 media session（`ttsSessionManager`/carPlaySession.ts）；睡眠定时 + 章末停止（990-1000 区域）。
5. 运行时实证：[ui-study](ui-study.md) §6——本地免费面（WebView2 系统语音）实测 ✓：「朗读」→「正在朗读」+ 播放条（上一句/暂停/下一句/停止 + 章节时间），**无需账号**（u06-tts-start.png）；Readest Voice/自定义端点未配置，成功面缺证（见 §8）。

### 5.7 链路七：脚注弹层

`FootnotePopup.tsx` 持有一个应用级 `FootnoteHandler`（FootnotePopup.tsx:113）；iframe 点击处理调 `footnoteHandler.handle(bookDoc, e)`（306），启发式来自 `utils/footnoteHeuristics.ts` + `shouldCheckAsFootnote`；handler `render` 事件后弹层挂载返回的一次性视图文档（`footnoteViewRef`，79）并经 `getStyles` 应用阅读器样式；进入注释的深链经 `utils/footnoteCfi.ts` 跟踪。引擎侧机制见 §3.6（第二个一次性 `<foliate-view>`，footnotes.js:205/72/104）。运行时实证：[ui-study](ui-study.md) §2——noteref 上标点击弹层显示脚注原文 ✓（u02-footnote-popover.png）。应用另调厂商脚注类 `.zhangyue-footnote/.duokan-footnote/.qqreader-footnote`（iframeEventHandlers.ts:564-588）。

### 5.8 链路八：词典 / 翻译 / Wikipedia

- 触发：选区 → Annotator popup 'dictionary'/'translate'（Annotator.tsx:1191-1211）→ `DictionarySheet`/`DictionaryPopup` + `TranslatorPopup`（Annotator.tsx:2671+）。查询期间保持选区存活（注释 1735-1736, 2597-2608）。
- 词典栈（`services/dictionaries/`）：`registry.ts` `getEnabledProviders`（143）+ `isSystemDictionaryEnabled`（190）；providers：`mdictProvider.ts`（包装 fork 的 `js-mdict` `MDX.create/MDD.create`——头注 mdictProvider.ts:1-14；init 只读 header+key 索引；`<img src>` 经 `mdd.locateBytes` → object URL，`dispose()` 撤销；加密 MDX → `unsupported`）、`starDictProvider.ts`、`slobReader.ts`、`bglReader.ts`、`wikipediaProvider.ts`（Wikipedia REST）、`webSearchProvider.ts`（模板 URL，`webSearchTemplates.ts`）、`systemDictionary.ts`（macOS）与插件运行时（`plugins/lookupRuntime.ts`）。候选形经 `lookupCandidates.ts` + `lemmatize/`。设置/存储：`customDictionaryStore.ts`；同步 `services/sync/adapters/dictionary.ts`。
- 翻译：`useTranslator`（hooks/useTranslator.ts）——providers `services/translators/providers/`：`deepl.ts`、`google.ts`、`azure.ts`(+azureShared)、`yandex.ts`(+yandexShared)、`custom/` 用户自定义（`customTranslatorStore.ts`）。默认 provider 'deepl'（useTranslator.ts:24）；key 为用户设置（token 在 useTranslator 状态；DeepL free-api helper `utils/deepl.ts:61 query`）。azure/yandex 有服务端代理路由（`src/app/api/azure-translate/route.ts`、`src/app/api/yandex-translate/`）。页内翻译模式：`useTextTranslation`（app/reader/hooks/useTextTranslation.ts）在 iframe 内注入段落级译文包装（DOM 索引映射，110-124）；样式 `applyTranslationStyle`（utils/style.ts:1206）。
- 运行时实证：[ui-study](ui-study.md) §6——翻译「已禁用」态 + 选区弹层翻译入口在册（无配置失败面）；词典入口在册（js-mdict 需自备 .mdx；Wikidata 需网络）。成功面缺证（DeepL/Yandex 需服务端 key，见 §8）。

### 5.9 链路九：TOC / 内链导航

- TOC 数据：`bookDoc.toc`（引擎 TOCProgress 供数据或裸结构）；nav 缓存 `{hash}/nav.json`（bookService.ts:1161-1177），由 `computeBookNav`（services/nav）计算并对 EPUB 重排水合（readerStore.ts:306-321）；`updateToc` 应用排序 TOC/中文变体（322-326）。UI：`sidebar/Content.tsx` 标签页（TOCView.tsx、BooknoteView、SearchBar、PageThumbnails、ChatHistoryView；Content.tsx:116-123）；树展开/扁平化在 `sidebar/tocTree.ts`；点击 → `eventDispatcher.dispatch('navigate', {bookKey, href})` + `getView(bookKey)?.goTo(item.href)`（TOCView.tsx:255-257）；页列表目标 `goTo(page)`（266）。
- 正文内链：引擎 `View.#handleLinks`（view.js:362-389）拦截点击：外部 → `external-link` 事件（可取消；应用经 `ExternalLinkConfirm.tsx` 确认），内部 → `link` 事件 + `goTo(href)`；hash-only href 对 section 重解析（376-383）。应用在 `iframeEventHandlers.ts` 附加调优（媒体目标、厂商脚注类，564-588）。
- 运行时实证：[ui-study](ui-study.md) §2——侧栏 treeitem 点击即跳章，显示各章页数与「当前位置」高亮 ✓。

---

## 6. 书库与迁移

### 6.1 存储布局

**基础目录（前端 `BaseDir` union → 解析器）**。解析器 `getPathResolver` `src/services/nativeAppService.ts:170-292`（web/node 镜像逻辑在 `src/services/appService.ts`）。Tauri 默认映射：

| BaseDir | 位置 | 引用 |
|---|---|---|
| `Settings` | `BaseDirectory.AppConfig`（portable 模式：exe 目录，baseDir 0） | nativeAppService.ts:199-205 |
| `Cache` | `BaseDirectory.AppCache` | nativeAppService.ts:206-212 |
| `Log` | `BaseDirectory.AppLog`（自定义根时 `<root>/Log`） | nativeAppService.ts:213-219 |
| `Data` | `AppData/Readest/...`——`DATA_SUBDIR='Readest'` | constants.ts:51；nativeAppService.ts:220-228 |
| `Books` | `AppData/Readest/Books`（`LOCAL_BOOKS_SUBDIR`） | constants.ts:52；nativeAppService.ts:229-237 |
| `Fonts` / `Images` / `Dictionaries` | `AppData/Readest/{Fonts,Images,Dictionaries}` | constants.ts:55-57；nativeAppService.ts:238-264 |
| `None` | 绝对路径（baseDir 0） | nativeAppService.ts:265-271 |
| `Temp` | `BaseDirectory.Temp`（Android：改 AppCache，因旧 Android 将 Temp 映射到不可写的 `/data/local/tmp`） | nativeAppService.ts:272-289 |

**各目录内容**：

- `Settings/settings.json`（+`.bak` 原子双写，`safeLoadJSON`/`safeSaveJSON`，src/services/persistence.ts:28-76）；读写方 `src/services/settingsService.ts:122,223-228`。`SETTINGS_FILENAME='settings.json'` constants.ts:59。
- `Books/library.json`——书库索引，节流 30s 写（src/store/bookDataStore.ts:19-40；文件名 src/utils/book.ts:46-47；写入方 src/services/appService.ts:660-662）。
- `Books/<hash>/` 每书：书文件、`cover.png`、`config.json`（进度+注释）、`nav.json`（删除语义：src/services/cloudService.ts:28-70；config 路径 src/utils/book.ts:69）。
- `Books/<hash>/` ABS 离线音频子目录（`getAbsOfflineDir`，排除出备份：src/services/backupService.ts:32-34,384-386）。
- `Cache/tts-cache/<hash>/` 每书 TTS 音频缓存（刻意不放 Books 下以免同步/备份误收：src/services/cloudService.ts:53-60）。
- `Data/statistics.db`——KOReader 兼容 SQLite（books + 页事件表），经 `appService.openDatabase('statistics','statistics.db','Data')` 打开（src/services/statistics/statisticsDb.ts:46-61）；单连接每源约束（statisticsDb.ts:25）。同一引擎（tauri-plugin-turso）还承载 Reedy 指标（`reedy_metrics` 表，src/services/reedy/instrumentation.ts:1-14）、BookOrbit 水位、Hardcover 同步映射、Notion 同步仓、OPDS 源映射、书库搜索索引（grep 命中：services/bookorbit/BookOrbitSyncStore.ts、services/hardcover/HardcoverSyncMapStore.ts、services/notion/NotionSyncStore.ts、services/opds/sourceMap.ts）。Web 构建走 `webAppService.openDatabase`（src/services/webAppService.ts:421）；native 走 `nativeAppService.openDatabase`（nativeAppService.ts:1015）；关闭时 WAL checkpoint(TRUNCATE)（src/services/database/nativeDatabaseService.ts:44-50）。
- Fonts/Images/Dictionaries 子树为可副本同步的二进制（§8）。

**Portable 模式 + 自定义根**：解析规则——自定义根优先于 portable；两者均把全部 base dir 收拢为 `<root>/`，叶目录 `Settings/Data/Books/Fonts/Images/Dictionaries`（nativeAppService.ts:162-193）；portable 判定 = exe 目录存在 `Settings.json`（或 Settings 目录）+ `get_executable_dir` IPC（nativeAppService.ts:643；命令 lib.rs:264-271）。自定义数据位置恒保持文件在 `Readest` 文件夹下——Rust 下载/上传范围规则 `is_within_data_dir` 授权任何含 `Readest` 路径组件的路径（src-tauri/src/transfer_file.rs:135-140,436-463）。[baseline](baseline.md) §4 即利用该机制以 exe 旁 `Settings.json` 建立隔离运行目录。

**备份（backupService.ts）**：备份 zip 内容 = `settings.json` 快照（设备本地/同步游标点路径黑名单，src/services/backupService.ts:66-107）、`statistics.json`（全量统计导出，:349-360）、以及每本在架书的 `Books/<hash>/` 目录（文件+封面+config；软删/孤儿目录排除；ABS 离线音频与 `.part` 排除，:362-389）。凭据仅在 `includeCredentials` 勾选时包含（zip 不加密，:37-45）。桌面：经 Rust `write_backup_zip`/`extract_backup_zip` 流式写入用户选定文件 + 进度 Channel（:430-439,472-484）；web：zip.js 内存 zip（:451-465）。恢复 = `extract_backup_zip` 落 Books + 重新导入（:632-693,762-782）。

### 6.2 导入路径

导入入口实测 6 种（[ui-study](ui-study.md) §1）：本地文件/文件夹/网页浏览器/网络小说/订阅源链接/在线书库（u01-import-click.png）。代码侧路径：

- **对话框导入**：原生「打开」对话框（过滤器 `*.epub;*.mobi;*.azw…`），入口逻辑落在 `bookService.importBook`（bookService.ts:500）；导入期预解析页数 `getBookDocPageCount`（bookService.ts:736）（[ui-study](ui-study.md) §1：导入即出 pageCount=218）。
- **argv / 文件关联**：argv 文件 → `allow_file_in_scopes` + `window.OPEN_WITH_FILES`（window-ready 后，lib.rs:229-247,827-838）；macOS `RunEvent::Opened` 同路（lib.rs:1116-1129）；前端 `hasCli()` 读注入旗标（src/services/environment.ts:14；`window.__READEST_CLI_ACCESS` lib.rs:867-870,910）。
- **文件夹扫描**：`read_dir` 命令（lib.rs:675）由 `nativeAppService.ts:505` 调用。
- **URL / 网页 / 订阅源**：`openBookFileContent` 为 URL 源传 fetcher（bookService.ts:1078）；in-app 浏览器作书源（web_browser.rs:1-6；`clip_url` lib.rs:700 剪藏入书）；RSS feed 书 `openFeedBookDoc`（readerStore.ts:254-259）。
- **OPDS / 在线书库**：`src/services/opds/*` 目录浏览 + 下载经 `download_file`（§8）。
- **拖放**：空书库空态页含拖放提示（[ui-study](ui-study.md) §1 launch-01.png；拖放落点处理未逐行追踪，落入 importBook 同栈 [推断]）。

### 6.3 0.12.16 Windows 实测缺陷（两项，观察源：[ui-study](ui-study.md) §1）

1. **对话框导入受管副本缺失 + 打开静默失败**：对话框导入后 `Books/<hash>/` 只有 config.json + cover.png，**EPUB 本体缺失**（受管副本未落盘）；点击书卡打开**静默失败**（无 toast、无 console 错误）；以 argv 携路径重开补写 filePath 后才能打开（3 次点击复现）。代码侧对照：受管副本逻辑在 `importBook` 的 in-place/copy 分支（bookService.ts:500）；打开路径按 `resolveBookContentSource`（bookService.ts:51）判 `managed|external|url|missing`，缺失应抛 `BookFileNotFoundError`（bookService.ts:1087）并 toast「Unable to open book」（ReaderContent.tsx:147-160）——实测静默说明该失败面存在 UI 缺口（缺口确切位置未定位，属复现事实 + 代码对照，机制归因 [推断]）。
2. **软删记录不去重**：同一文件再次导入产生 library.json 第二行——`byFilePath` 路径索引显式跳过 tombstone（deletedAt 非空）记录（[ui-study](ui-study.md) §1 实测：argv 记录 deletedAt=createdAt 在册，再导入成新行；索引行为系代码侧判读 [推断]）。

附带观察：软删行 UI 无回收站/恢复入口（0.12.16 release note 明言 deleted books no longer come back）；「仅从设备中移除」确认对话一次复验未生效（疑确认层拦截，待复验）；移动除「仅设备」外还有「云端和设备/仅云端[未上传时禁用]」三选项（[ui-study](ui-study.md) §1）。

---

## 7. 平台桥（Rust / Tauri）

### 7.1 Rust 模块清单（src-tauri/src/，注册于 lib.rs）

| 模块（路径） | 职责 | 引用 |
|---|---|---|
| `lib.rs` | 应用入口 `run()`；builder、插件注册、invoke handler、窗口设置、init 脚本 | src-tauri/src/lib.rs:534-1159 |
| `main.rs` | 6 行 shim 调 `readestlib::run()` | src-tauri/src/main.rs |
| `transfer_file.rs` | HTTP 下载（`download_file`，1 MB 分片 x8 并发）+ 流式上传（`upload_file`）带进度 Channel；范围守卫路径解析（`ensure_path_allowed`） | src-tauri/src/transfer_file.rs:197-376,378-417,153-178 |
| `localsend/` | LocalSend 协议 v2.2 文件传输（Wi-Fi 设备间），见 §7.3 | src-tauri/src/localsend/service.rs |
| `nightly_update.rs` | Nightly 通道：base 感知 semver 比较（`is_update_newer`）、minisign `verify_update_signature` 命令（镜像 tauri-plugin-updater）、`install_nightly_update` 命令 | src-tauri/src/nightly_update.rs:17-44 |
| `web_browser.rs` | 应用内浏览器作书源：桌面 = 独立 `WebviewWindow` + 下载拦截 + 注入 chrome JS；移动 = native-bridge `WKWebView/WebView` 控制器 | src-tauri/src/web_browser.rs:1-6 |
| `browser_fetch.rs` | `fetch_web_browser_resource`——从应用内浏览器会话取 cookies/鉴权资源 | src-tauri/src/lib.rs:702 |
| `browser_cookies_macos.rs` | macOS Safari/WKWebView cookie 提取（cfg macos） | src-tauri/src/lib.rs:26-27 |
| `spawn_fresh_browser.rs` | `spawn_fresh_browser`——桌面 OAuth 冷启动浏览器回退（已运行浏览器收不到 Google scheme） | src-tauri/src/lib.rs:54-55,717-718；调用方 src/services/sync/providers/oauth/oauthDesktop.ts:19-25 |
| `media_proxy.rs` | `get_media_proxy_base`——媒体（有声书流）回环 HTTP 代理；经 reqwest 栈 hyper 服务 | src-tauri/src/lib.rs:703；src-tauri/Cargo.toml:114-115 |
| `range_file.rs` | 自定义 URI scheme `rangefile`，经 `?path=&start=&end=` 供本地字节区间（Android Chromium 重施 Range 偏移）；范围守卫 | src-tauri/src/lib.rs:737-740 |
| `backup_zip.rs` | `write_backup_zip`/`extract_backup_zip`——Rust 侧 zip 流式（避免批量字节过 IPC；Android body-as-JSON-array 仅 3.9 MB/s） | src-tauri/src/lib.rs:676-677；src/services/backupService.ts:424-439 |
| `dir_scanner.rs` | `read_dir` 命令，外部书库文件夹扫描 | src-tauri/src/lib.rs:675；src/services/nativeAppService.ts:505 |
| `cover_thumbnail.rs` | `optimize_cover_thumbnails` 命令 | src-tauri/src/lib.rs:674 |
| `epub_parser.rs` / `mobi_parser.rs` / `pdf_parser.rs` / `comic_parser.rs` | 原生元数据/封面/全解析命令（epub：`parse_epub_metadata`/`extract_epub_cover_full`/`parse_epub_full`；mobi 含 AZW；pdf：`parse_pdf_metadata`/`render_pdf_cover`；comic：`get_comic_page_sizes`） | src-tauri/src/lib.rs:678-685 |
| `discord_rpc.rs` | Discord Rich Presence（`update_book_presence`/`clear_book_presence`），仅桌面 | src-tauri/src/lib.rs:33-34,696-699 |
| `clip_url.rs` | `clip_url`——剪藏/分享 URL 入书（Send/clip 流） | src-tauri/src/lib.rs:700 |
| `file_reveal.rs` | `reveal_item_in_dir`（桌面） | src-tauri/src/lib.rs:38-39,667-668 |
| `window_state.rs` | 包装 tauri-plugin-window-state：加载前剥离非法几何（Windows `-32000` 哨兵值） | src-tauri/src/lib.rs:58-59,765-770 |
| `linux_display.rs` / `linux_single_instance.rs` | CEF-on-Linux：Tauri init 前强制 X11 显示检查；CEF 运行时的 DBus 单实例转发 | src-tauri/src/lib.rs:40-43,538-545 |
| `eink_identity.rs`（+ `android/eink.rs`） | Android e-ink 检测经 `ro.*` 系统属性，缓存；导出 JS 为 `window.__READEST_IS_EINK` | src-tauri/src/android/eink.rs:25-29；src-tauri/src/lib.rs:861-865,909 |
| `sentry_config.rs` | DSN 来自编译期 `SENTRY_DSN` 环境变量（未设 → 禁用）、release/environment 命名、webview 引擎/版本打标、浏览器噪声与 MOBI panic 过滤 | src-tauri/src/sentry_config.rs:6-15,97-113 |
| `macos/` | 红绿灯/覆盖标题栏、关窗隐藏行为、macOS 菜单、Safari 鉴权（`auth_with_safari`）、Apple 登录（`start_apple_sign_in`）、系统词典弹窗（`show_lookup_popover`）、os_version | src-tauri/src/lib.rs:45-46,686-695,1074-1104 |
| `windows/mod.rs` | Windows 专属胶水（ScrollBarStyle::FluentOverlay、边框恢复） | src-tauri/src/lib.rs:9-10,1005-1010 |

**确认不存在**：无 whisper/语音识别模块、无 `app_audio` 模块、无独立 KF8 解析器（MOBI 解析器经 `mobi_parser.rs` 处理 AZW/AZW3）。音频播放走前端 `NativeAudioPlayer` + native-bridge `use_background_audio`（plugins/tauri-plugin-native-bridge/src/desktop.rs:77）。

### 7.2 invoke 命令 → 前端调用方（注册于 lib.rs:661-722；精选）

| 命令（Rust） | 前端调用方 |
|---|---|
| `start_server` | 未发现 `invoke('start_server')` 调用方 [推断：预留；tauri-plugin-oauth JS 走自己的 `plugin:oauth|start`] |
| `download_file` / `upload_file` | src/utils/transfer.ts:215（tauriDownload；用于 libs/storage.ts:207）/ transfer.ts（tauriUpload；libs/storage.ts:70,114） |
| `get_environment_variable` | src/app/auth/page.tsx、src/hooks/useFileSelector.ts（6 处） |
| `get_executable_dir` | src/services/nativeAppService.ts:643、src/components/UpdaterWindow.tsx |
| `reveal_item_in_dir` | src/app/library/components/BookshelfItem.tsx、MigrateDataWindow.tsx |
| `is_updater_disabled` | src/services/nativeAppService.ts:658（另有注入快路 `window.__READEST_UPDATER_DISABLED`，lib.rs:912） |
| `allow_paths_in_scopes` | src/services/nativeAppService.ts:881 |
| `optimize_cover_thumbnails` | src/services/nativeAppService.ts:771 |
| `read_dir` | src/services/nativeAppService.ts:505 |
| `write_backup_zip` / `extract_backup_zip` | src/services/backupService.ts:486,765 |
| `parse_epub_metadata` / `parse_epub_full` | src/utils/tauriEpubBridge.ts（EPUB 预取桥 `tryNativePrefetchEpub`，document.ts:571-577） |
| `extract_epub_cover_full` / `extract_mobi_cover_full` | src/app/reader/hooks/useAutoSaveBookCover.ts:171,175 |
| `get_comic_page_sizes` | src/utils/spread.ts |
| `parse_mobi_metadata` | src/utils/tauriMobiBridge.ts |
| `parse_pdf_metadata` / `render_pdf_cover` | src/utils/tauriPdfBridge.ts |
| `auth_with_safari`（macos） | src/app/auth/utils/nativeAuth.ts |
| `start_apple_sign_in`（macos） | src/app/auth/utils/appleIdAuth.ts |
| `set_traffic_lights` / `set_window_title`（macos） | src/store/trafficLightStore.ts、src/utils/window.ts |
| `show_lookup_popover`（macos） | src/services/dictionaries/systemDictionary.ts |
| `update_book_presence` / `clear_book_presence` | src/utils/discord.ts |
| `clip_url` | src/app/send/page.tsx、src/services/novel/renderNovelPage.ts |
| `open_web_browser` / `set_web_browser_status` / `extract_web_browser_archive` | src/services/webBrowser/webBrowser.ts |
| `fetch_web_browser_resource` | src/services/webBrowser/browserFetch.ts |
| `get_media_proxy_base` | src/services/audiobook/mediaProxy.ts |
| `localsend_*`（11 命令） | src/services/localsend/service.ts:5-33 |
| `spawn_fresh_browser` | src/services/sync/providers/oauth/oauthDesktop.ts:20 |
| `verify_update_signature` / `install_nightly_update` | src/utils/bridge.ts |
| 其余：`set_webview_info`（nativeAppService.ts:648）、`get_webview_version`（AboutWindow.tsx） | — |

另有一方插件命令自 JS 调用（不在主 handler）：native-bridge（`copy_uri_to_path`、`select_directory`、`show_file_picker`、`set_screen_brightness`、`get_safe_area_insets`、`iap_*`、`set_sync_passphrase`、`open_external_url`、`use_background_audio`、`set_multicast_lock`、`get_sys_fonts_list` 等——plugins/tauri-plugin-native-bridge/src/desktop.rs:51-296）、native-tts（plugins/tauri-plugin-native-tts/src/lib.rs:44-53）、turso（`Database.load/execute/select/batch/close`——src/services/database/nativeDatabaseService.ts:18-52）、及 fs/dialog/http/opener/deep-link/updater/window-state/sharekit/biometric/haptics/clipboard/device-info/websocket/process/os/log（插件清单 src-tauri/src/lib.rs:650-802）。

### 7.3 窗口 / 协议 / 深链 / 更新 / CEF / eink / 传输 机制

- **单实例**：tauri-plugin-single-instance，DBus id `com.bilingify.readest`（lib.rs:527,742-758）；二次启动聚焦窗口并以 argv 发 `single-instance` 事件（文件打开由前端处理）。CEF/Linux 运行时跑不了该插件，`linux_single_instance::forward_to_running_instance` 于 init 前 DBus 转发（lib.rs:544-545）。
- **深链**：tauri-plugin-deep-link（lib.rs:760）；Windows/Linux `register_all()`（lib.rs:850-854）。Scheme（tauri.conf.json:217-241）：mobile App Link `https://web.readest.com`、自定义 `readest://`、`readest-onedrive://`、Google 反向 DNS `com.googleusercontent.apps.209390247301-…`（Drive OAuth 用，src/services/sync/providers/oauth/oauthDesktop.ts:10-14）。macOS 桌面经 Info.plist 注册。重投递 URL 以每次运行 `window.__READEST_APP_RUN_ID__` 去重（lib.rs:890-908）。
- **CLI**：tauri-plugin-cli 仅桌面注册（lib.rs:856-859），`file1..file4` 参数（tauri.conf.json:205-213）；仅桌面注入 `window.__READEST_CLI_ACCESS = true`（lib.rs:867-870,910）；前端 `hasCli()` 读取（src/services/environment.ts:14）。CLI 访问门控"可信环境"下的按用户数据隔离 [推断自旗标名；消费链在 src/utils/access.ts]。
- **更新器**：tauri-plugin-updater（桌面，lib.rs:762-763）；端点 `https://download.readest.com/releases/latest.json` + GitHub releases latest.json，minisign 公钥在配置（tauri.conf.json:245-252）。`compute_updater_disabled`：`READEST_DISABLE_UPDATER` 环境变量、或 Linux 非 AppImage（deb/rpm/pacman）/Flatpak 隐藏应用内更新（lib.rs:416-443）；权威 IPC `is_updater_disabled`（lib.rs:449-453）由 `NativeAppService.init()` 读取（src/services/nativeAppService.ts:658）。**Nightly 通道独立**：前端取 `https://download.readest.com/nightly/latest.json`（src/services/constants.ts:988），经 `verify_update_signature`（minisign，同公钥）校验并以 `install_nightly_update` 安装（src/helpers/updater.ts:106-160；src-tauri/src/nightly_update.rs:30-44）。
- **CEF 分支（Linux）**：feature `cef`（src-tauri/Cargo.toml:28-29）；运行时类型 `AppRuntime = tauri_runtime_cef::CefRuntime`（lib.rs:521-524）；入口 `cef_entry_point`（lib.rs:530-533）；Chromium 沙箱显式禁用并附理由（lib.rs:626-635）；`READEST_CDP_PORT` 环境变量开启 CDP 端口（否则拒绝 `--remote-debugging-port`）（lib.rs:636-647）。全部出厂 Linux 构建用 CEF（`--no-default-features --features cef`，Cargo.toml:20-27）；Wry/WebKitGTK 仅留给 webdriver 测试架。[baseline](baseline.md) §4 注：Windows 标准构建为 WebView2，`READEST_CDP_PORT` 仅 CEF 构建（src-tauri/src/lib.rs:635）。
- **E-ink**：Android setup 时检测 → `window.__READEST_IS_EINK`（lib.rs:861-865,909）；前端白窗背景 + `DEFAULT_EINK_VIEW_SETTINGS`（src/services/constants.ts:462）。
- **启动画面**：无。Windows 主窗先隐藏，前端发 `window-themed` 后才显示（30s 超时回退）（lib.rs:1042-1069）；Linux 显示后最大化还原（lib.rs:400-407）；macOS 关窗隐藏到 Dock（lib.rs:1085-1100）。
- **OAuth 回环**：`start_server` 命令启动 tauri-plugin-oauth localhost 监听，向窗口发 `redirect_uri`（lib.rs:249-257）。
- **splash/字体等其余**：见 §7.1 模块行。

### 7.4 LocalSend 传输（Wi-Fi 传输本体，fork 自 localsend core）

- LocalSend 协议 v2.2，钉自 Readest 的上游 localsend core fork rev 1609ca7，仅 `discovery` feature（无 WebRTC/v3）（src-tauri/Cargo.toml:104-109）。
- HTTP(S) 服务刻意绑定 **53318-53327**（把官方 53317 留给 LocalSend 应用），区间走查空闲端口；UDP 多播通告携带真实端口，SO_REUSEPORT（src-tauri/src/localsend/service.rs:29-35,115-171）。
- 多播发现组 `DEFAULT_MULTICAST_GROUP(_V6)` + register/goodbye 路由；离开设备通告端口 0（`DEPARTURE_PORT`），保持 15s（service.rs:306-325）；在线 TTL 4.5s（service.rs:376）。
- 命令（注册 lib.rs:706-716，定义 localsend/commands.rs:57,96,116,124,135,181,193,234,293,342,393）：`localsend_start/stop/get_status/list_devices/announce/is_alive/set_discoverable/respond/cancel_receive/send_files/cancel_send`。前端包装 src/services/localsend/service.ts:5-33。配对/信任态 + 逐传输确认对话在 src/services/localsend/pairedDevices.ts（自动接受为付费门控：src/utils/access.ts:133-148）。
- 平台可用性：invoke handler 无条件注册（无 cfg 门，lib.rs:706-716）——桌面与移动构建可用；web 无 Rust 壳不可用。

### 7.5 Tauri fork 增量（packages/tauri @ 382ea858，readest 分支）

- `readest` 分支 = 上游 tauri（快进至 `270c63f11 fix(ci): give audit permissions (#15970)`，即 tauri ~2.10-dev 期，wry 0.56）**加恰好 5 个 fork 提交**（读分支 log 核实；历史无更早 fork 专属提交）：
  1. `bfc0c89a2` enhance: auto hide home indicator on iOS（tauri-runtime-wry，+3 行）
  2. `97e3fd15b` feat: add Romanian language support to NSIS installer
  3. `79e17d98a` fix: guard unlisten script against already-removed listener（crates/tauri/src/event/mod.rs，1 行）
  4. `3156d92b7` feat: add a no-op `cef` feature stub（crates/tauri/Cargo.toml，+4 行）——让 macOS/Windows/mobile 构建能校验 `tauri/cef`；**真正的 CEF runtime 来自上游 tauri 的 `feat/cef` 分支**，经 `.cargo/cef.toml` [推断自提交信息；`.cargo/cef.toml` 本轮未读]
  5. `382ea858b` fix: don't block the mobile main thread on the plugin store for page loads（crates/tauri/src/manager/webview.rs，+60/-6）
- 规模：领先上游 5 提交；fork 仓库共 6,176 提交（含全量上游历史）；子模块 clone 无 tag；分支：`readest`（默认）、`dev`、`feat/cef*`（真 CEF runtime 在此）、`expose-content-range-header`、归档。
- **fork 接线**（src-tauri/Cargo.toml 无 `[patch]`；补丁在工作区根）：`[patch.crates-io] tauri = { path = "packages/tauri/crates/tauri" }` + `swift-rs = { path = "packages/swift-rs" }`（Xcode 26 vendored 修复）+ `tauri-runtime-cef = { path = "packages/tauri-runtime-cef-stub" }`（Cargo.toml:48-60）；Linux CEF 构建经 `apps/readest-app/src-tauri/.cargo/cef.toml` 把 tauri + runtime-cef 重定向回上游 git（Cargo.toml:1-8,56-59）。`packages/tauri` 自成 cargo workspace、被排除在工作区外（Cargo.toml:15-22）。
- 内嵌一方插件（src-tauri/plugins/）：`tauri-plugin-native-bridge`（移动+桌面原生胶水）、`tauri-plugin-native-tts`（OS TTS 引擎）、`tauri-plugin-turso`（嵌入式 SQLite，可选 AES-256-CBC，plugins/tauri-plugin-turso/README.md:1-3）、`tauri-plugin-webview-upgrade`（Android：侧载新版 `com.google.android.webview` 覆盖卡死的华为/文石 WebView；最低版本在 tauri.conf.json:253-256）。

### 7.6 平台差异要点（desktop / web / mobile）

- 应用服务分派：tauri → `NativeAppService`，浏览器 → `WebAppService`（IndexedDB 文件系统，src/services/webAppService.ts:42-58,421）；选择器 environment.ts:85-93。无独立"mobile 服务"——移动即 `NativeAppService` + native-bridge，内部分歧走 `OS_TYPE` 分支。`nodeAppService.ts` 供服务端/SSR（镜像目录 getter，`APP_NAME='Readest'`，src/services/nodeAppService.ts:19-50）。
- 文件读取：Android + Linux/CEF 必须走 `rangefile://` 自定义 scheme（Chromium 重施 Range 偏移，nativeAppService.ts:340-355）；iOS picker Inbox 文件优先 NativeFile（:356-359）；桌面用 asset-protocol RemoteFile（较 IPC NativeFile 快 2 倍，:360-370）。
- TTS：原生 OS 引擎仅移动（桌面 TODO，TTSController.ts:324）；Edge wss 直连（tauri）vs 代理 HTTPS（web）（edgeTTS.ts:390-440）；Readest Voice 全平台（配额+套餐）。
- Web 浏览器书源：桌面 = 额外 WebviewWindow；移动 = native-bridge 控制器（web_browser.rs:1-6）。
- 鉴权：macOS 原生 Apple（`start_apple_sign_in`）、Safari 会话鉴权（`auth_with_safari`）；iOS `sign_in_with_apple` 插件（lib.rs:792-793）；web/tauri OAuth 重定向流程不同（tauri：oauth 插件回环或深链；web：重定向）。
- 更新器：仅桌面；Linux deb/rpm/flatpak 隐藏（lib.rs:416-443）；nightly 安装仅桌面（lib.rs:720-721）；web PWA 无；移动走商店更新 [推断：无移动更新代码]。
- Discord RPC：仅桌面 macos/windows/linux（lib.rs:33-34,696-699）。IAP：仅移动经 native-bridge（desktop.rs:135-164 桌面为 no-op）；Stripe 在 web/桌面。生物识别/触感：移动插件（lib.rs:795-799）。窗口控制：Linux/CEF 需 JS 指针驱动移动/缩放（environment.ts:24-33）；macOS 覆盖标题栏；Windows 无边框 + FluentOverlay 滚动条（lib.rs:997-1024）。
- Web 专属代理：OPDS 代理与 deepl/yandex/ai/hardcover/notion 代理为 SSR 路由——web 使用；tauri 在 CORS 允许处直连（OPDS：tauri 直连 fetch，opds/audioStream.ts:155）[推断：翻译器 tauri 构建亦可打同一部署 API base]。CLI 访问旗标仅桌面（lib.rs:867-870）。Temp 目录 Android 覆盖（nativeAppService.ts:272-283）。

---

## 8. 服务与同步

平台选择：`environmentConfig.getAppService` 返回 `NativeAppService`（tauri）或 `WebAppService`（browser）（src/services/environment.ts:85-93）。Readest Cloud 基址：`getAPIBaseUrl()` = `<apiBaseUrl>/api`，默认 `https://web.readest.com/api`（environment.ts:16-20,45；constants.ts:958）；Node API 基址 `https://node.readest.com/api`（constants.ts:959；environment.ts:53）。**通用约定**：凡需账号的成功面在本轮均未实测，标注 缺证（未实测）→ [ui-study](ui-study.md) §6（该节实测了未登录失败面；登录成功面仅有一次被动事件佐证——共享 profile 会话继承导致云书自动下载，[ui-study](ui-study.md) §0/§6）。

1. **云端账户 + 权益（Readest Cloud，第一方）**：Supabase auth（`@supabase/supabase-js`，package.json:139）。方法：邮箱密码（`signInWithPassword`/`signUp`）、魔法链接（`signInWithOtp`）（src/app/auth/components/EmailPasswordAuth.tsx:94,100,108）；OAuth `google|apple|azure|github|discord` 经 `signInWithOAuth`（ProviderLogin.tsx:3；app/auth/page.tsx:115,155）；macOS/iOS 原生 Apple 走 `signInWithIdToken`（page.tsx:96-97）+ `start_apple_sign_in` / `auth_with_safari`。JWT：web 存 localStorage；tauri 用 `supabase.auth.getSession()`（src/utils/access.ts:280-298）。API 路由以缓存 JWKS（ES256）本地验签，HS256/自托管回退 Supabase getUser（access.ts:300-317）。无访客模式；未登录可本地使用；`keepLogin` 系统设置（constants.ts:207）；自托管解锁全部付费特性（`isSelfHosted`，access.ts:177-188）。**权益在 JWT**（custom access-token hook）：claims `plan`、`storage_usage_bytes`、`storage_purchased_bytes`、`customization_purchased`（access.ts:13-19,150-158）；套餐 free/plus/pro/purchase(lifetime)；门控：云存储配额（access.ts:210-226）、每日翻译配额（:228-235）、TTS 配额（:251-254）、Readest Voice = plus/pro（`TTS_PLANS` :243-249）、三方云同步 + TTS 缓存 + ABS 离线 + 近场配对 + 自定义翻译/TTS = 付费或自托管或一次性 Full Customization（:59-148,187-206）。缺证（未实测）→ ui-study §6。
2. **云端书文件存储**：客户端不打 Supabase Storage——应用调 Readest API `/storage/upload|download|delete|stats|list|purge` 取预签名 URL，设备端 PUT/GET（tauriUpload/tauriDownload = Rust `upload_file`/`download_file`；web = fetch）（src/libs/storage.ts:14-21,42-80,165-221；src/utils/transfer.ts:215）。键 `<userId>/Readest/Books/...`（storage.ts:130,182）。删除尽力而为吞错（storage.ts:223-240；Sentry READEST-5）。按用户配额取自 token claims。缺证（未实测）→ ui-study §6。
3. **结构化同步（replica 引擎，HLC CRDT）**：`POST/GET /sync/replicas` + `/sync/replica-keys`（推行 / 按 kind+HLC 游标拉 / 批量拉）（src/libs/replicaSyncClient.ts:7-8,48-99,112-120 → src/pages/api/sync/replicas.ts，落在 Supabase 表 `replicas`）。行带 HLC（`physicalMs-counter-deviceId`）时间戳；冲突按 HLC 比较 LWW（src/libs/crdt.ts:8-27）；每设备游标（src/services/sync/replicaCursorStore.ts）；触发 = 启动、`visibilitychange`、`online`（src/services/sync/replicaSyncManager.ts:121-122,324-338）；离线策略 = 上线即冲刷（未发现持久 outbox——未发行为下次冲刷时从本地状态重导 [推断自管理器设计]）。同步分类：settings、book、progress、note、stats、dictionary、font、texture、custom_translator、custom_tts、opds_catalog、credentials 等；book/progress/note 受 Readest Cloud 开关门控；`credentials`（OPDS/KOSync/Readwise/Hardcover 密钥）默认关、开启时端到端加密（src/services/sync/syncCategories.ts:52-64,121-156；encryptedFields 机制 src/services/sync/replicaRegistry.ts:44-53；口令/密钥 src/services/sync/passphraseGate.ts、`/sync/replica-keys`）。已注册副本适配器（src/services/sync/adapters/）：settings、bookshelf、font、texture、dictionary、customTTS、customTranslator、opdsCatalog、absServer；二进制（字体/词典/TTS 包）按需经云 `Readest/Replicas/<kind>/<replicaId>/` 同走预签名 URL 路径（src/services/cloudService.ts:123-171；constants.ts:54）。缺证（未实测）→ ui-study §6。
4. **遗留按书同步**：`SyncClient` → `/sync` 推拉 books/configs/notes/stats（src/libs/sync.ts:6-8；API src/pages/api/sync.ts，表 `books`、`book_configs`（push 代码内）、`stat_books`、`stat_pages` + rpc `upsert_stat_pages`、`stat_archives`）。冲突规则：`updated_at`/`synced_at` 游标（pages/api/sync.ts:399-512）。
5. **实时性**：客户端同步路径无实时通道（拉取靠 focus/online/interval；`SYNC_*_INTERVAL_SEC = 3/5/5 s`，constants.ts:1003-1005）[推断：同步代码内未发现 supabase channel 订阅；定时间隔的消费方未全追踪，§10]。
6. **统计同步**：`/api/stats/compact`（Cloudflare Worker 压缩，`files` 存储内 `stats/v1/` 分段）+ `/api/stats/restore`（src/libs/statsArchive.ts:7-18；路由清单）。本地库 `Data/statistics.db` KOReader 兼容（§6.1）；采集 `services/statistics/trackerCore.ts` `TrackerCore` 页驻留事件（翻页/空闲/隐藏时冲刷）、`ttsStatsRecorder.ts`；UI `ReadingStatsTracker.tsx` 挂于阅读器。缺证（未实测，需账号）→ ui-study §6。
7. **分享 / 发送**：`/api/share/*`（create/list/token/cover/download/import/revoke/og.png），表 `book_shares`；有效期 1/3/7 天，每用户上限 50（constants.ts:961-980）。Send 邮箱（Kindle 式）：`/send/*` 路由（地址分配、收件箱、发件人），表 `send_addresses`、`send_inbox`、`send_allowed_senders`；Plus/Pro/Lifetime 门控（`EMAIL_IN_PLANS`，access.ts:48-51；constants.ts:967-975）。缺证（未实测）→ ui-study §6。
8. **支付**：Stripe（`/api/stripe/{check,checkout,plans,portal,webhook}`）+ Apple/Google IAP 经 native-bridge `iap_*` 命令（plugins/tauri-plugin-native-bridge/src/desktop.rs:135-164；路由 app/api/apple/*、app/api/google/*）；表 `customers`、`subscriptions`、`plans`、`payments`。IAP 仅移动、Stripe 在 web/桌面（§7.6）。缺证（未实测）→ ui-study §6。
9. **Crosspoint（电纸书设备同步）**：RFC 8628 式设备授权——阅读设备出码，Web 应用批准；此后 `/api/crosspoint/syncs/progress` 镜像进度到设备（src/app/api/crosspoint/device/code/route.ts:1-30；表 `crosspoint_device_codes`、`crosspoint_devices`）。缺证（未实测）→ ui-study §6。
10. **KOReader sync（kosync）**：src/services/sync/KOSyncClient.ts——服务器可配（默认 `https://sync.koreader.rocks/`，constants.ts:84-94），md5 文档校验（binary/partial），鉴权头 `X-Auth-User/X-Auth-Key` 或 HTTP Basic（KOSyncClient.ts:60-80）；LAN 服务器绕过 `/api/kosync` 代理（该代理仅转发 https）[推断自 isLanAddress 用法 KOSyncClient.ts:12,24]。冲突策略 `prompt|silent`。只同步阅读进度。缺证（未实测）→ ui-study §6。
11. **BookOrbit**：第二个 KOReader 兼容服务（src/services/bookorbit/BookOrbitClient.ts），加注注释/书签交换、有声书配对、统计推送；水位存本地 SQLite（BookOrbitSyncStore.ts）；默认设置 `DEFAULT_BOOKORBIT_SETTINGS`（constants.ts:96-109；默认服务器 URL 未提取，§10）。缺证（未实测）→ ui-study §6。
12. **文件同步（WebDAV / Google Drive / S3 / OneDrive / iCloud）**：provider 注册表（src/services/sync/file/providerRegistry.ts:20-40）；冻结远端布局 `<rootPath>/Readest/library.json + books/<hash>/{书文件, cover.png, config.json}` + 可选 `tts/` 包（src/services/sync/file/layout.ts:20-47）。同步书文件 + 每书进度/注释 + 书库索引 + TTS 包；策略 send/receive/silent；按设备时钟/行新度合并（src/services/sync/file/merge.ts，引擎导入 engine.ts:22-29）。**付费门控**（`CLOUD_SYNC_REQUIRES_PREMIUM`，access.ts:59-81）。各 provider 默认 `syncBooks:false`（constants.ts:147-204）。iCloud 走 sharekit；Drive 走 OAuth+PKCE 桌面深链流程（oauthDesktop.ts）。逐书推送返回 `{uploaded:false, reason:'remote-matches'|'no-source'|'disabled'}`（sync/file/engine.ts:43-49）。缺证（未实测）→ ui-study §6。
13. **Audiobookshelf**：src/services/audiobookshelf/client.ts——用户自建服务器 URL；登录 + 刷新 token（`/login`、`/auth/refresh`，pre-2.26 遗留长 token，client.ts:121-231）；进度 `PATCH /api/me/progress/:libraryItemId`（client.ts:109）；流式经 Rust 回环媒体代理（src/services/audiobook/mediaProxy.ts → `get_media_proxy_base`）；离线下载付费门控（access.ts:106-123）；librarySync/ebookProgress/progressSync/offline 模块齐全。缺证（未实测）→ ui-study §6。
14. **Hardcover**：GraphQL `https://api.hardcover.app/v1/graphql`（直连），OAuth2 `https://api.hardcover.app/oauth2`（src/services/hardcover/HardcoverClient.ts:130；hardcoverOAuth.ts:16）；限速客户端（rateLimit.ts）；同步阅读状态/进度；本地 id 映射 SQLite（HardcoverSyncMapStore.ts）；代理路由 `/api/hardcover/graphql`。缺证（未实测）→ ui-study §6。
15. **Readwise**：`https://readwise.io/api/v2`（constants.ts:111；src/services/readwise/ReadwiseClient.ts），accessToken 同步受 `credentials` 分类门控（syncCategories.ts:57-59）。缺证（未实测）→ ui-study §6。
16. **Pagebound**：`https://prod-pagebound-api.onrender.com/api/v1`，Firebase 邮箱密码鉴权（内嵌公钥）+ Typesense 书搜索 `https://hztadco4ku1vqi6lp.a1.typesense.net/...`——代码注明"Pagebound 无公开 API；这些是其 web 应用自用端点"（src/services/pagebound/PageboundClient.ts:4-13）。缺证（未实测）→ ui-study §6。
17. **Notion**：用户 API integration 经代理 `/api/notion/[...path]`，api base `https://api.notion.com/v1`，版本 `2026-03-11`（constants.ts:136-145）；本地同步仓 SQLite（NotionSyncStore.ts）。缺证（未实测）→ ui-study §6。
18. **OPDS + 代理**：目录浏览在 src/services/opds/*（feed 解析、封面、有声/PSE 流式、自动下载、订阅态）；目录可选用户名/密码本地存储（src/store/customOPDSStore.ts:88,233-238）；web 构建经 SSRF 防护代理 `/api/opds/proxy`（重定向跳数主机检查，src/app/api/opds/proxy/route.ts:1-27）；tauri 直连 `tauriFetch`（src/services/opds/audioStream.ts:155）。下载经 `download_file`。OPDS 目录本身作为副本 kind（`opdsCatalog` 适配器）同步。缺证（未实测，需目录 URL）→ ui-study §6。
19. **TTS**：四个客户端 + 一个付费云音色（src/services/tts/）：Web Speech（`WebSpeechClient`，系统语音——**本地免费面实测可用**，ui-study §6）；Edge TTS（`EdgeTTSClient` + src/libs/edgeTTS.ts——tauri 直连 `wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1`，或 HTTPS 代理 `/api/tts/edge`（web/Workers）仅流音频，edgeTTS.ts:36,390,421-440）；原生 OS 引擎（`NativeTTSClient` → tauri-plugin-native-tts 命令 `init/speak/stop/pause/resume/set_rate/set_pitch/set_voice/get_all_voices/set_media_session_active`，plugins/tauri-plugin-native-tts/src/lib.rs:44-53；**仅移动**，桌面 TODO：src/services/tts/TTSController.ts:324）；**Readest Voice**（付费云 GPU）：`/api/tts/readest`（音色列表 `?all=1`）、`/api/tts/readest/stream`、`/api/tts/readest/jobs[/id]`（src/services/tts/providers/readest.ts:20-33,194,312,495,577）。服务端逐请求强制：`gateReadestVoice` 校验 auth → 服务已配置 → 套餐 ∈ `TTS_PLANS`（plus/pro）→ 目录（src/libs/readestVoice/gate.ts:20-32）；配额 `TTS_FIXED_QUOTA`/套餐（access.ts:251-254）；错误码 `NOT_AUTHENTICATED`/`NOT_CONFIGURED`/`PLAN_REQUIRED` 扁平字符串（gate.ts:14-32）。离线：逐章音频下载缓存（tts/providers/{bookCacheStore,cache,cacheSweep,opfsPackFs,sqliteCacheStore}.ts、ttsDownloadManager.ts），付费门控（`TTS_CACHE_REQUIRES_PREMIUM`，access.ts:89-104）。Readest Voice/自定义端点成功面缺证（未实测）→ ui-study §6。
20. **翻译**（src/services/translators/providers/）：deepl、yandex、azure、google（+ `custom/` 下 OpenAI 兼容 LLM/DeepL 自备 key）。DeepL 与 Yandex 走 Readest API 代理、**服务端内嵌 key 池**——`/api/deepl/translate` 从环境变量逗号分隔 key 列表随机取一（src/pages/api/deepl/translate.ts:13-33——内嵌 key 存在，本文不打印），`/api/yandex-translate` 代理 Yandex 会话+翻译端点（src/app/api/yandex-translate/route.ts:19-35）。每日配额按套餐（`DEFAULT_DAILY_TRANSLATION_QUOTA`，access.ts:228-235）。自定义翻译 key 为用户提供、付费门控（`isCustomTranslatorAllowed`，access.ts:196-206）。成功面缺证（DeepL/Yandex 需服务端 key）→ ui-study §6。
21. **AI（Reedy）**：完整的内嵌 AI 子系统（src/services/ai/）——providers：Ollama（本地默认 `http://127.0.0.1:11434`，模型 `llama3.2`，embeddings `nomic-embed-text`）、AI Gateway（经第一方代理 `fetch('/api/ai/chat')`，embeddings `/api/ai/embed`；默认模型 `google/gemini-2.5-flash-lite`，鉴权 = Readest 账户 token + gateway key，app/api/ai/chat/route.ts:20-37、AIGatewayProvider.ts:58）、OpenRouter（用户 key）（src/services/ai/providers/index.ts:10-18；src/services/ai/constants.ts:24-35）。RAG 服务 + chunker + 本地仓（ragService.ts、storage/aiStore.ts）；聊天适配 Tauri（adapters/TauriChatAdapter.ts）。阅读器接线：笔记 AI 聊天（notebook/AIAssistant.tsx + components/assistant/Thread.tsx，检索后端 `LegacyIdbBackend` vs `ReedyBackend` 二选一，AIAssistant.tsx:21-26；"Enable AI search and chat for this book" 开关门控，AIAssistant.tsx:418；侧栏 `ChatHistoryView`，Content.tsx:45-51）；Book Q&A/摘要经 prompts（ai/prompts.ts）接线、非 stub。Reedy 本地指标存 SQLite（`reedy_metrics`）、指标无网络出网（src/services/reedy/instrumentation.ts:1-14）。[推断：无一键"整书摘要"流水线——release note 的 "AI summarization building" 对应上述 chat/RAG 基建；`services/reedy` 仅粗读。]
22. **遥测 / Sentry**：Rust 侧仅当构建期烘焙 `SENTRY_DSN` 才启用（src-tauri/src/sentry_config.rs:13-15）；浏览器噪声 + MOBI 封面 panic 事件过滤；webview 引擎/版本打标（lib.rs:547-622、sentry_config.rs:97-113）；`tauri-plugin-sentry` 在守卫存在时桥接 WebView 事件（lib.rs:804-807）；Android/iOS 原生崩溃走 sentry-android/cocoa SDK，桌面 minidump handler 关闭（lib.rs:547-555）。除 Sentry 外未发现产品分析/遥测 SDK [推断自 absence]。结构化统计仅有 `/api/stats/*`。缺证面：各构建的 DSN 实配与否未知。
23. **更新通道**：stable（download.readest.com 或 GitHub 的 latest.json）与 nightly（`/nightly/latest.json` + minisign 校验 + `install_nightly_update`）（src/helpers/updater.ts:106-160；constants.ts:984-996）；changelog 取 `release-notes.json`（updater.ts:230）；检查间隔 24h（constants.ts:1006）；禁用矩阵见 §7.3。机制面已读码核实；实际更新拉取成功面缺证（未实测）。
24. **本地阅读辅助（无云依赖，清点在案）**：阅读标尺 `ReadingRuler.tsx`（`READING_RULER_COLORS`；矩形映射 41-45）；快读 RSVP `components/rsvp/`（`RSVPControl/RSVPOverlay/RSVPStartDialog`，TTS 同步闪词 `rsvpTts.ts` `decideRsvpTtsPosition` RSVPControl.tsx:110）；自动滚动 `useAutoScroll` + `AutoScrollControl/AutoscrollIndicator/AutoScrollSpeedOverlay`（速度手势 `useAutoScrollSpeedGesture`）、中键自动滚动 `useMiddleClickAutoscroll`；段落聚焦模式 `components/paragraph/`（ParagraphControl 压暗/聚光段落，TTS 联动 `paragraphTts.ts`）；手写笔记 `components/handwriting/`（HandwritingCanvas/Overlay、`useHandwriting`、`utils/inkAnchoring.ts`；文石后端 `handwriting/booxBackend.ts`）；氛围叠层 `AtmosphereOverlay`、`BrightnessOverlay`；Wordlens 行内翻译、小说页渲染器（src/services/ 下清点在案）。[推断：旧版 "Focus mode" 命名在本 tag 由段落模式 + 氛围实现；无独立 focus-mode 组件。]

---

## 9. 测试与质量

**测试栈（tag 内实读核实）**：

- 单元/组件：**Vitest**（`apps/readest-app/package.json:28` `test`、`:30` `test:coverage`、`:31` `test:browser`（vitest.browser.config.mts）、`:29` `test:extension`、`:34` `test:pr:web:unit`、`:37` `test:all`；另有 `:27` `test:lua`（KOReader 伴生插件脚本）与 `:32` `test:tauri`、`:33` `test:android`（bash 脚本））；依赖 `vitest ^4.1.11`（package.json:279）、`@vitest/browser-playwright`（:249）、`@vitest/browser-webdriverio`（:250）、`@vitest/coverage-v8`（:251）。配置文件：vitest.config.mts、vitest.browser.config.mts、vitest.android.config.mts、vitest.tauri.config.mts、vitest.env.mts、vitest.setup.ts、vitest.tauri.setup.ts（tag 检出实测存在）。
- E2E：**WebdriverIO**（`test:e2e` = `wdio run wdio.conf.ts`，package.json:40；`@wdio/*` 依赖 :252-257；`e2e/` 目录含 app.e2e.ts、fixtures、pages、tests、README.md）；**Playwright** web E2E（`test:e2e:web` = `playwright test`，package.json:41-44；`@playwright/test ^1.60.0` :225、`playwright ^1.58.2` :267；playwright.config.ts）。Rust 单测：`test:rust` = `cargo test -p Readest --lib`（package.json:52）。
- 规模与夹具：`src/` 下 **1,254 个测试文件**（.test.ts 949 + .test.tsx 305，tag 检出实测）；`src/__tests__/` 子目录覆盖 ai/android/api/bookshelves/components/database/document/fixtures/hooks/integration/ios/libs/pages/plugins/reader/reedy/services/statistics/store/tauri/utils/workers 等全树；**18 个 repro EPUB 夹具**（src/__tests__/fixtures/data/：repro-3583、repro-3683、repro-3688、repro-4379、repro-4439、repro-5263、repro-6128-image-highlight、repro-6129-tall-table、repro-6155-footnote-images、repro-6221-image-column-spill 等，以 issue 号命名）——即上游回归修复以最小 EPUB 夹具固化在仓内。
- i18n 覆盖：`i18n-langs.json` 34 个语言码 + en = `public/locales/` 35 个目录（tag 检出实测目录数；语言码清单见 i18n-langs.json）；key-as-content i18n 体系（仓内 docs/i18n.md）；KOReader 伴生插件 `apps/readest.koplugin` 另有自己的 gettext .po 管线（10 语言，仓内文档）。运行时实证：[ui-study](ui-study.md) §7——应用内搜索框正常接受中文 IME 组词 ✓；反例为原生 Win32 对话框逐字符注入被 IME 吃掉（真实键盘输入路径边界）。
- 测试基建的平台事实：全部出厂 Linux 构建走 CEF，**Wry/WebKitGTK 仅保留给 webdriver 测试架**（src-tauri/Cargo.toml:20-27；§7.3）。

**遥测默认面矛盾（平台侧在案）**：结构化统计同步通道存在且 stats 为同步分类之一（§8 条目 6/3；分类开关含 stats），Sentry 经构建期 DSN 接入 WebView 事件桥（lib.rs:804-807），**但代码内未发现任何同意对话框或条款开关**——鉴权组件与常量 grep 无 consent 面 [推断自 grep]；除 Sentry 外无产品分析 SDK [推断自 absence]。即"统计/遥测通道在册"与"零用户同意面"并存，属设计层面张力而非缺陷判定（DSN 实配与否按构建而定，见 §8 条目 22）。

**质量面其他在案事实**：booknotes 写入单点汇流（bookDataStore.ts:95 注释，§5.1）；进度保存防抖 + 无变化跳过保护云同步顺序（#4222）+ 页面隐藏冲刷（#5859）（§3.4 第 12 步）；settings.json 损坏 `.bak` 回退自动恢复（persistence.ts:28-53）；数据库关闭 WAL checkpoint 尽力而为 + 无参 close 守卫防止关一个库杀掉其他库（nativeDatabaseService.ts:38-52）；上游回归以 repro EPUB 夹具固化（本节上）。

---

## 10. 不确定与未验证

合并自引擎侧与平台侧两份研究笔记；本文正文所有 [推断] 标记的汇集：

**上游/分叉历史**
1. **精确 fork 点**：fork 含上游历史至 `c49ded0`（2025-09-24，最后一名 John Factotum 作者提交）；上游此后是否有从未合并的提交离线不可证（未允许联网 fetch）。"领先 254 提交"计 `c49ded0..HEAD`。（§3.2）
2. **fixed-layout.js 逐行归属未分**：该文件自上游初版（2022）即存在，未对上游逐行 diff 区分文件内上游代码与 fork 代码——fork 增量清单系 commit 信息推导。（§3.2）
3. **上游头部越过 c49ded0 的情况**：同 1，主分支候选能力不混入本 tag 分母（[baseline](baseline.md) §6 同口径）。

**引擎侧**
4. **书库 → 阅读器导航触发点**：`/reader/{hash}` 路由消费有证（ReaderContent.tsx:116），但 `src/app/library` 的 BooksGrid 点击处理未读，push 调用点系 [推断]。（§3.4 第 4 步）
5. **Rust 侧 EPUB 预取内部**（`parse_epub_full`，document.ts:196-199 注释）与 `Books/` 前缀 → 磁盘绝对路径映射位于 src-tauri/Tauri fork——JS 侧契约有证，Rust 实现未读（解析命令注册面已在平台侧补证：lib.rs:678-685）。
6. **CBZ 页级标注端到端范围**：定位器支持有证；应用是否端到端暴露漫画标注未追踪 [推断]。（§4.1 矩阵 CBZ 行）
7. **AI 摘要**：tag 内读者代码无一键摘要器；release note 表述对应 chat/RAG 基建 [推断]；`services/reedy`（Reedy 检索后端）仅粗读。（§8 条目 21）
8. **`view.initTTS`（view.js:697）与 TTSController 自建（TTSController.ts:918）并存**：应用路径用后者；前者疑为 API/演示兼容保留 [推断]。（§3.6）
9. **付费 TTS token 存储**：Readest Voice 经 `fetchWithAuth` 用账户 token（readest.ts:316）；token 的确切客户端存储（auth/cloudService）未追至该调用点之外。（§5.6）
10. **paginator 内部 `View`/iframe 沙箱细节**（CSP、脚本白名单在 paginator 与 epub Loader 间的强制点）仅部分读码（`allowScript` 门 FoliateViewer.tsx:774-776；loader 事件目标 epub.js:1312）。
11. 深嵌套 helper 的精确行号（如 `Overlayer.bubble` 内部、`splitSection` 头部之外）按模块/段粒度给出而非逐语句。

**平台/服务侧**
12. **`.cargo/cef.toml` 与真 CEF runtime 分支**：stub 与补丁间接已证（Cargo.toml:1-8,56-59；提交 3156d92b7 信息），但 `.cargo/cef.toml` 与上游 `feat/cef` 分支未打开——**Linux CEF 构建所用上游 tauri 精确 rev 未核实**。（§7.5）
13. **`start_server` 命令**：src/ 内未发现 `invoke('start_server')` 调用方——可能死代码或经 oauth 插件 JS API 以别名调用；未完全追踪。（§7.2 表）
14. **同步定时间隔**：常量定义 3-5s（constants.ts:1003-1005）但消费方未全追踪；阅读器内周期同步实际节奏可能不同（focus/online 触发已证）。（§8 条目 5）
15. **Supabase 表 schema**（列/约束）仅自 API 路由用法推断；未读迁移文件（Supabase 工程在仓外——检出内无 `supabase/` 目录）。（§8 条目 3/4）
16. **自定义根叶目录**：解析器限定自定义根为 `Settings/Data/Books/Fonts/Images/Dictionaries` 子目录（nativeAppService.ts:184-186）；设置 GUI 是否暴露全部叶目录或仅单根，UI 层未验证。（§6.1）
17. **内嵌密钥盘点非穷尽**：DeepL key 池为服务端环境变量（pages/api/deepl/translate.ts:31-33）；Pagebound Firebase key 内嵌于客户端但代码自述为公开 client key（PageboundClient.ts:10-11）；Google OAuth client id 内嵌（tauri.conf.json:238）；未审计全部常量。（§8）
18. **whisper/语音识别**：本 tag 确认**不存在**（src-tauri grep 无命中）——记为"验证性缺席"而非不确定。（§7.1）
19. **BookOrbit 默认服务器 URL**：未提取（constants.ts:96-109 默认块本轮只为 KOSync 读得）。（§8 条目 11）
20. **遥测/统计默认开关的实际默认值**：stats 属同步分类、无同意面（§9）；但"默认开/关"的 UI 初值未读（syncCategories.ts 默认值面未逐项核）——与 §9 矛盾一并留待复验。

**实测侧待复验（[ui-study](ui-study.md) 在案）**
21. 「仅从设备中移除」确认对话一次复验未生效（疑确认层拦截）；顶栏书签按钮点击未生效待复核；页码/进度计数滞后口径待查（[ui-study](ui-study.md) §1/§2/§3）。
22. 服务成功面（云同步/各集成/TTS 付费音色/翻译代理）全部缺证（未实测），指针统一见 §8 各条目与 [ui-study](ui-study.md) §6。
