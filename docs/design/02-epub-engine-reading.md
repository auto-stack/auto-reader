# 02 · 正式 EPUB 引擎阅读与 Locator v2 设计（READER-007 T-01 冻结）

状态：proposed→frozen（T-01 冻结；落地与 Spec 增量见 READER-007 SD-01～05，T-10 沉淀）
来源：READER-007（2026-11-03）｜前置：[029 原生输入链与文档表面收口]
（auto-ui，archived 12/12，T-10 独立复审 pass，landing 65bb455f）｜
依赖接口：[document-surface-native-input]
（auto-ui/docs/specs/runtime/，029 SD-02 交付）。

本文档是**实施前冻结契约**：产品 profile、受管资源与安全边界、引擎预算、
Locator v2 存储/协议与 v1 兼容/迁移语义、版本管理、CFI 核验 owner 与可信
转换接缝。未冻结前不写用户数据、不开放 UI 写入。

## 1. 产品 profile（正式阅读表面第一期）

| 项 | 冻结值 | 说明 |
|---|---|---|
| 支持输入 | 无 DRM 重排版 EPUB3（继承 003/005 导入链） | 正文结构 + 基本出版物 CSS（标题/段落/强调/列表/简单表格/代码块）、内置/受管图片、目录/跨章/脚注往返、单列分页与连续滚动、字号/列宽/主题、精确选区/高亮/批注/恢复 |
| 非本期 | 复杂版式/竖排/公式/任意 CSS、PDF/漫画/Kindle/TTS/同步/书源/Notes 真实交接/系统深链/Linux/移动 | 不静默丢内容而显示已支持 |
| 装载方式 | 书架/正常路由自动装载应用自有固定资产与受管原件，默认本地离线 | 不依赖 tests/probe、D:/autostack/readest、PROBE_DATA_DIR/PROBE_ASSETS_DIR、驱动注入或旁路服务 |
| 启动 profile | vm 分离模式 `auto run -r vm --no-merge [-B 17825]`；vue 模式 `auto run --server=vm` | T-00 实测冻结；`-r vm --server=vm` 实测=仅后端无窗口（README 旧记载修订列入 T-10） |
| 表面接口 | 029 交付 `doc-surface (url: .model_url, height: N)`（auto-ui compiler feature `doc-surface`，windows；vue 轨退化为透传 div） | 事件/URL 契约以 document-surface-native-input §1 为准；产品 adapter 消费交付版引擎，不复制旧 bug、不靠驱动兜底 |
| 引擎 | foliate-js fork@3d794195（固定只读来源）+ 应用自有 engine-adapter（产品版，T-03/T-04 从 029 adapter 演化） | **许可与打包（T-02 固化）**：foliate-js = **MIT**（readest packages/foliate-js/package.json + LICENSE，2022 John Factotum）——可再分发；打包=按 prepare_engine_assets.py 模式做扁平化 flat 重写（含 vendor 引用一致化）→ 应用自有受管资产（默认随 app 分发，路由接入 T-03）；每次打包产出 manifest 记录文件 hash；不依赖 D:/autostack/readest 运行时检出 |

## 2. 受管资源与安全边界

1. **资源服务**：仅服务「本书受管内容」（受管副本/章缓存/提取资源）与「固定
   引擎资产」两个源；书内活动脚本、远程自动加载、DTD/外部实体、跨书路径、
   任意文件读取继续拒绝（继承 003/005 语义，扩展到引擎页面装载面）。
2. **引擎与内容隔离**：可信引擎脚本（受管 adapter/foliate fork 资产）与
   不可信出版物内容（XHTML/资源）分离装载；须证明浏览器引擎不能绕过现有
   解压/资源边界（P-09/P-02 资产变异门）。
3. **离线**：断网与移走 probe/readest 目录后仍可装载阅读（P-02）。
4. **拒绝形态**：预算超限、损坏、未知版本、非法资源具名拒绝且零半写
   （继承 epub_too_large/img_too_large/img_extract_failed/未知版本 refuse
   语义）；选区事件继承 32KiB UTF-8 上限，不静默截断用户摘录。

## 3. 引擎预算（T-01 冻结；语义继承 corpus_profile，产品化不降配额）

| 面 | 冻结值 |
|---|---|
| 导入 | 30MiB 输入、spine ≤4096、单章/单资源 12MiB 硬闸（继承，不改） |
| 引擎装载 | ≤15s（装载超时具名失败） |
| 选区回传 | ≤5s |
| 冷恢复 | ≤30s |
| 清理 | ≤10s（进程/端口/弹出窗释放） |
| 驱动总预算 | ≤600s/单 profile 跑（语义继承；产品门沿用） |
| 长文 | AUTO_HTTP_STEP_BUDGET=1e9 + AUTO_HTTP_REQUEST_TIMEOUT_MS=300000（继承） |
| 像素 | 渲染解码由引擎/WebView2 承载；应用不额外承诺逐像素解码；像素 oracle 仅作门内证据 |
| 边界两侧 | 合法/拒绝对照（P-09）；无法满足既有已支持输入时显式回规划，不暗降配额 |

## 4. Locator v2 契约（冻结方案甲）

### 4.1 方案比较（至多两种，冻结其一）

| 维度 | 方案甲：同文件版本化（冻结） | 方案乙：独立 locators 注册表 |
|---|---|---|
| 结构 | annotations/<book_id>.json 带 v2 锚的书升 version:2（v1 字段不变 + 每条记录可选 `locator`）；reading/<book_id>.json 可选顶层 `locator` | v1 文件不变 + 新 locators/<book_id>.json 注册表；v1 记录/状态可选 `locator_id` 引用 |
| 旧客户端行为 | version:2 具名拒绝（refuse-to-load，不误解、不静默丢） | 旧客户端继续读 v1 文件，但**重写会丢 locator_id 引用**（rec_json/reemit 白名单重建）→ 孤儿注册表条目，静默引用丢失 |
| 一致性/原子性 | 单文件沿既有 verified_write（.bak/暂存/提交/读回）；注释↔锚内聚 | 双文件需跨文件一致性；写失败需两段回滚 |
| 版本管理 | ReadingState（无全局版本，可选键）、注释文件（version 1/2）、locator 对象（schema/version）三者独立 | locator 注册表自版本化，注释/状态引用它 |
| 迁移 | 仅新增记录可选字段，旧 v1 记录原样；无整库改写 | 需注册表建表 + 引用回填两段动作 |

**冻结：方案甲。** 理由：单文件内聚沿既有写协议；旧客户端对 version:2
具名拒绝优于静默丢引用；无跨文件原子性负担；v1 记录逐字保留、可选 v2 锚
只在能证明唯一映射时生成，不整库强制改写。

### 4.2 存储形态

```jsonc
// annotations/<book_id>.json — 带任意 v2 锚的书写 version:2
{
  "version": 2,
  "book_id": "<uuid>",
  "source_hash": "sha256:<hex>",
  "updated_at": 0,
  "annotations": [
    {
      "annotation_id": "…", "kind": "highlight|bookmark|comment",
      "chapter_number": 3, "para_idx": 7,           // v1 段锚（恒在场，回退面）
      "quote": "逐字子串", "occurrence": 2,
      "comment": "…", "tags": ["…"], "created_at": 0, "updated_at": 0,
      "locator": { … }                              // 可选；缺位 = 纯 v1 锚
    }
  ]
}
```

```jsonc
// locator 对象（schema "reader-locator" version 1；随记录内嵌）
"locator": {
  "schema": "reader-locator", "version": 1,
  "kind": "epub_range",                 // "legacy_paragraph" 保留给仅段级锚
  "book_id": "<uuid>", "source_hash": "sha256:<hex>",
  "resource": { "spine_index": 3, "href": "xhtml/ch03.xhtml" },
  "engine": { "name": "foliate-js", "revision": "3d794195" },
  "range": {
    "start": { "cfi": "epubcfi(/6/2!/4/18,/1:27)" },
    "end":   { "cfi": "epubcfi(/6/2!/4/18,/1:60)" }   // 单点（书签）= end 缺位
  },
  "quote": "完整逐字原文（跨段=拼接原文）",
  "context": { "before": "≤64 前文", "after": "≤64 后文" },
  "occurrence": { "scope": "book", "index": 2 },     // 作用域显式：book|resource|section
  "created_at": 0
}
```

```jsonc
// reading/<book_id>.json — v1 形态不变 + 可选顶层 locator（同上对象）
{ "book_id": "…", "chapter_number": 3, "paragraph_index": 7,
  "para_hash": "…", "para_text": "段文本逐字全文", "quote_prefix": "",
  "font_size": "medium", "line_height": "comfy", "layout": "medium",
  "theme": "light", "updated_at": 0,
  "locator": { … } }                                  // 可选
```

### 4.3 契约规则

1. **主键纪律**：不把展示百分比、UTF-16/字节/字符裸偏移当主键；CFI + 逐字
   quote/context + 显式作用域 occurrence 是唯一锚。任何带偏移字段（若未来
   引入）必须带显式单位枚举（utf16|byte|char），不裸混传。
2. **身份链**：locator 恒携带 book_id/source_hash/resource/spine_index；
   恢复/核验时与当前书严格核对，错书/错源版本/错会话具名拒绝零写入。
3. **v1 兼容**：v1 记录/状态继续可读可回访；annotation_id/quote/comment/
   tags/created_at 不因换引擎改变；只在能证明唯一映射时生成可选 v2 锚；
   无法映射保留 v1 与明确状态；不伪造 CFI、不整库强制改写、不做第二套
   永久书库。
4. **新形态可辨**：version:2 文件旧客户端具名拒绝（未知版本 refuse 语义，
   原件逐字保留）；旧客户端对 reading 状态的可选 locator 键容忍读、重写时
   回落 v1 段锚（诚实降级——v1 锚恒在场，恢复仍按段级正确；该降级在本文档
   具名登记，不伪装成无损失）。
5. **写失败/损坏**：沿备份/暂存/提交/读回纪律；失败保留原文件/原注释；
   空/损坏/未知版本具名拒绝与恢复建议，不默清空、不假保存。
6. **跨段新选区**：用真正 range（start/end CFI）表示，不塞伪段号、不把
   跨段 quote 编成单段 occurrence。

## 5. CFI 核验 owner 与可信转换接缝

- **owner = Reader（消费方）**，机制分三环，全部不信任引擎自述：
  1. **录入环（创建时）**：adapter 真实 DOM range → CFI + quote + occurrence
     → 后端七级校验（book/hash/session/schema/kind/locator/oversize/stale，
     029 语义继承）：quote 与当前章原文逐字核对、occurrence 在界；失败零落盘。
  2. **恢复环（运行时）**：引擎解析 CFI 后，adapter 回报目标文本 → 与
     locator.quote/context 逐字比对一致才标记已恢复；**CFI 指向另一处重复
     句但 quote 相同的反例必须被识别**（回读文本不一致 → needs_relocate，
     原摘录保留，不静默跳第一处/删注释）。
  3. **回访环（跳转）**：搜索/注释回访命中 → 真实 range 定位与原文逐字
     oracle 双证；错锚/资产变异使原 oracle 真实失败非零，还原后转绿。
- **可信转换接缝**：引擎 CFI 是「可核验的 locator 载荷」，不是信任源；
  受管 adapter 是唯一转换面（选区→载荷、载荷→回读），产品不引入第二个
  自写 CFI 解析器制造不一致面。
- **百分比/前缀检查不够**：不因字符串以 epubcfi 开头、quote 在全书某处
  存在或记录数递增而判通过（029 N-09/N-11 位置指纹判据继承）。

## 6. 版本管理

| 面 | 版本 | 变化 |
|---|---|---|
| annotations 文件 | 1（纯 v1）→ 2（含 locator 记录） | version:2 仅因「存在任一 v2 锚」而写；纯 v1 书恒 version:1 字节兼容 |
| locator 对象 | schema reader-locator v1 | 新形态；未来变化升 version |
| reading 状态 | 无全局版本（可选 locator 键） | 词法门容忍未知键（已实测）；写侧在场才枚举校验 |
| 书籍 import_version | 1 不变 | 本计划不重写书库记录 |
| 引擎 | foliate-js@3d794195 固定 | 换引擎升 engine.revision，locator 按新引擎重新核验/迁移判定 |

## 7. 消费者入口与验收入口

- **消费者入口（冻结）**：正式 reading_page 的正文列从 scroll-pane 文本行
  形态扩展为「doc-surface 引擎表面 + 既有 scroll-pane 回退语义」；书架导入
  /正常路由 → 自动装载固定资产与受管原件（T-03/T-04 接线，本设计冻结契约）。
  旧 TXT/MD/最小 EPUB 阅读路径保留兼容与诊断用途。
- **永久验收入口（T-02 建立）**：`python tests/product/verify_epub_product.py
  --profile vue|vm --auto-bin <固定auto> --out-dir <自有隔离>`；必需集
  P-01～12 注册唯一 ID，0 选择/缺项/GAP/not_run 非零，exit0 当且仅当
  全 PASS；数据/API/磁盘仅独立读回，正常保存不预写；旧门
  （verify_standalone/verify_local/verify_epub/原生驱动）同 cohort 回归。
- **语料**（T-02 冻结）：先复用 006/029 合成集，再新增至少一组可再分发
  真实 EPUB（不同内容结构/重复句/跨段/长章/损坏与资源边界样本）；清单/许可
  /hash/预期可重算；拟语料不计已执行。
