# 主题采纳合同（theme-adoption）

> 来源：auto-os/PLAN-059（2026-11-04 work 执行）。宿主主合同：
> auto-os `docs/specs/shell/host-theme-policy-and-delivery.md`；
> 本批登记页：auto-os `docs/specs/apps/product-theme-batch-059.md`；
> 阅读面来源合同：`docs/specs/reader/epub-engine-reading.md`（READER-007）。

## 消费形态

- **固定快照**：`vendor/themes` = UI 管理渠道发布的官方主题包快照
  （`themes` 0.2.0，内容 digest
  `9fa07742dc68aa5377ae06cb2d966386002063f184c515b6c5dddf8a6bef838e`，
  per-file sha256 与源包逐文件校验同律；快照不可二次编辑、非第二权威
  源；升级 = UI 发新快照替换 + 本仓重验）。
- **pac 声明**：`dep themes { path: "vendor/themes" }`。pac `theme` 键
  **保持缺省 = follow 宿主**（宿主策略完整快照 > 本 design 默认 > legacy
  回退）。本产品无品牌 accent 键、无内容外品牌色键——无豁免声明面。
- **源内导入**：`use themes.themes: Auto`（app.at）——缺此行包主题不入
  收集链，design/follow 候选按 C-11 未注册整帧拒绝（031 合同）。
- **design 默认**：`theme: "Auto"` + `mode: if .dark_mode { "dark" } else
  { "light" }`。本产品原为纯浅色壳（无 dark_mode 位、无明暗切换——
  settings 页主题区为展示文案），独立默认腿取 **dark_mode=false=light**
  保现默认语义（056 auto-todo 先例）；`dark_mode` 保留名位由运行时种子
  链（AUTO_UI_THEME env > os-config > 系统主题，Plan 458/672）与宿主
  策略统一驱动，宿主内完整快照按 031 full-host 语义整体接管。App 级
  声明（056 notes 先例；store 不持主题位，避免双轨保留名歧义）。

## 阅读面（经 READER-007 正式引擎端口）

- **优先级**：显式书级选择（reading-state 持久化的 `theme` 键 / 阅读页
  选择器"亮/米/暗"）> 应用模式派生 > 内置缺省 light。sepia 恒为显式
  选择（宿主/模式不映射）。
- **派生默认**：无显式选择时，阅读页引擎默认随应用模式（本页 `dark_mode`
  保留名位）——dark 派生引擎 dark、light 保持 light；经
  `POST /api/reader/command` `op:"settings"` 主题字段下发（007 命令
  端口，engine-adapter `applySettings` 注入 sepia/dark CSS 并回读
  `window.__reader.appliedSettings.theme`）。
- **既有缺口修复（本批，具名）**：冷恢复此前不向引擎端口补发主题——
  stored theme=dark 的书重开后引擎面停留默认浅色（scroll-pane 铬面正
  确）。现 Init 末段按 SetTheme 同式经命令端口补发当前主题（含派生
  默认），V-02 冷恢复哨兵覆盖。
- **内容域豁免**：出版物正文/图片/封面/批注色语义归 owner（007 引擎
  面边界）；批注高亮 `bg-primary/10` 随主题 token（合法公共面）；引擎
  sepia/dark CSS 为 007 已交付引擎配色（本批消费，不改引擎）。

## 公共壳表面

- app.at 壳（sidebar/移动顶栏/outlet）、bookshelf、book_detail、settings
  全部语义 token 类（bg-background/bg-card/border-border/text-foreground），
  族内明暗由包 token 切换承接，无视图级 dark 分支（056 todo 先例）。
- settings 页既有"AutoRead follows the app theme"展示文案自采纳起为真。

## 框架投影依赖（本批修复，具名）

vue 轨 design.theme 投影此前被生成器门控（`has_accent_color ||
has_theme_name`）静默截断：无 accent/theme_name 状态的产品（本产品、
056 todo 同形）`design { theme }` 不产生任何运行时，官方包不上身（vue
轨停留 scaffold 静态表）。修复 = 门控扩三臂（accent_color / theme_name /
design.theme 投影），auto-ui 组树 `ui_gen/vue/script.rs` 三处（onMounted/
watch import + 运行时注入块）；三无 app 维持零注入（零变化优先裁定不
变）。owner 注记：056 todo 的 vue 轨像素门从未执行，本缺陷在其交付时
已存在；后继批次以同法核。

## 验证与测试设施

- **冻结工具链（os-059 组）**：auto-man 2bbd9542（安装版 auto.exe
  `0.1.0+plan-890-verified-r7-t19-17-g2bbd954`）/ auto-lang 2f558fc93 /
  auto-ui e06b65b2 + 本批投影修复（组树分支）/ auto-web 3de5524e /
  auto-down 7c4d5cbb；包源 = 组树 `packages/themes`（digest 9fa07742…）。
- `tests/theme_059_ui.spec.ts`（本批新增 vue 轨反控）+ `tests/
  test_059_theme.py`（七腿 runner，隔离 AUTO_READER_DATA + plan-artifacts
  语料 `gen_product_corpus.py` product-alpha）：
  - **腿 A 显式覆盖轨**：`AUTO_UI_THEME=dark` → 壳根像素 `#09090b`
    精确 + 引擎端口读回 `theme=dark` + 引擎文档 html 背景 `#1f2430`
    精确（shadow root 递归下钻 oracle）+ 真实书卡哨兵。
  - **腿 B OS 跟随轨**：env 缺省（浅色 OS）→ 壳根 `#ffffff`、读回
    light。
  - **腿 F standalone follow**：`AUTOOS_DESKTOP_CONFIG`（Solarized/dark）
    → 壳根 `#002b36` 精确、读回 dark。
  - **腿 FB 坏 digest 拒绝保旧**：digest 错误候选 → 具名拒绝、壳根
    保持 legacy light、工具宿主日志含拒绝行。
  - **腿 FR 重开追最新**：改写配置 Auto/dark 后重开 → 壳根 `#09090b`。
  - **腿 S1/S2 显式 override 优先**：UI 选择器置 sepia（真实用户路径，
    按书持久化）→ 重开于 Solarized/dark follow 下：壳暗 `#002b36`、
    阅读保持 sepia `#f4ecd8`（显式 > follow）。
- **原门不动**：`verify_standalone --profile vue|vm`（28/27）、
  `verify_local`（50）、`verify_epub`（22）、`auto test`（7）、
  `verify_epub_product`（READER-007 交付面）；VM 轨像素腿由 MCP
  autoui_screenshot 采样（引擎面 CDP 腿 = 007 具名 GAP 维持）。
- 运行 env：`AUTO_LANG_ROOT`/`AUTO_WEB_ROOT`/`AUTO_UI_TOOL_BIN` 指
  os-059 组树；语料/证据全在 `D:/autostack/plan-artifacts/plan-059/`
  （不触用户真实书库/全局设置）。
