# T-00 运行时能力核查报告（READER-001）

日期：2026-10-05 · 执行：READER-001 T-00 · 状态：完成（结论已回写计划）

## 核查范围

计划 T-00 要求：验证文件选择/读取、编码和存储在 Vue/VM 实际路径的能力；确定最小统一内容输出；记录缺失能力。核查方法是**运行真实探针**，不采信文档注释。

- 工具：`auto` CLI（PATH 解析至 `D:/autostack/auto-lang/target/debug/auto`，版本 `0.1.0+v0.4.2-2592-gee25d3b49-dirty`，构建自 auto-lang ee25d3b49-dirty）
- VM 轨：`auto tests/probe/t00_fs_probe.as` 等脚本直跑 AutoVM
- a2r 轨：`auto trans --path <file>.at rust` 检查生成 Rust 的 native 映射（未映射调用在 cargo 构建时即 E0425）
- 探针脚本：`tests/probe/t00_fs_probe.as`（fs/编码/hash/json/大文本）、`t00_cap_probe.as`（大写 File.*/uuid/Env/字符迭代）、`t00_split_probe.as`（split/starts_with/trim）、`t00_a2r_probe{,2,3}.at`（a2r 映射面）

## VM 轨实测结果（全部实跑）

| 探针 | 结果 |
|---|---|
| fs.mkdir_all + file.is_dir | PASS |
| file.write_text/read_text 中文 UTF-8 回环（94 字节） | PASS |
| file.read_text_range envelope 合法形状（total=94, next_offset:null） | PASS |
| 编码检测：GBK 双字节 → `total:-1` 拒绝 | **T-01 修正：初版判 PASS 为假阳性**——file.write_bytes/File.write_bytes 在 VM 轨 rc=0 但不落盘，当时检验的是「文件缺失→-1」。真实 GBK 字节拒绝由 READER-001 应用级 HTTP 验证交付 |
| read_text 对 GBK 静默返回 ""（不可单独作编码判据） | NOTE |
| hash.file_sha256（64 hex） | PASS |
| file.copy + exists + size | PASS |
| json.parse 字段访问（中文值+转义引号+嵌套数组） | PASS |
| 大文本 27,000,832 字节写盘+全文读回+sha256 | PASS（全程 1.4s） |
| 大写 `File.read_text_range` | PASS（VM 认大写形态） |
| str.uuid（36 字符） | PASS |
| Env.get | PASS |
| for-in 遍历 str | 按字符迭代（4 字符串计 4） |
| str.split("\n") 中文/空行/大文本（3.2MB→65537 行 <0.5s） | PASS |
| starts_with / trim（UTF-8） | PASS |
| substr | **字节索引**；多字节字符边界内取子串返回 "" |

## a2r 转译面映射实测（trans 生成 Rust 逐行核对）

**有映射**（生成 `a2r_std::…`）：`fs.exists / is_dir / file_size / read_text / read_to_string / write_text / write / append_text / create_dir / walk / copy_recursive`、`File.read_text_range`（**仅大写形态**）、`File.read_bytes`、`File.exists`、`Env.get`、`str.uuid`、`json.parse`（含字段访问）、`json.encode`（类型化值）。

**无映射**（生成裸 `fs.xxx`/`file.xxx`/`File::xxx` → E0425）：`fs.read_text_range`（小写）、`fs.mkdir_all`、`fs.copy`、`fs.delete`、`fs.remove_file`、`fs.read_dir`、`fs.metadata`（且错映射为 file_size——禁用）、`fs.join/parent/filename/ext/stem/canonical/mtime/rename`、**全部小写 `file.*` 模块调用**、**全部 `hash.*`**。

推论：027-file-manager 注释所记 E0425 债（P670-D1）在当前 CLI 上**部分仍成立**——目录类与 hash 类 native 依旧 VM-only；但基础读写/编码 envelope 已可双轨。

## VM 轨缺陷与规避（探针头注已固化）

1. 裸列表字面量直接传 native（`file.write_bytes(p, [1,2])`）→ `Invalid list ID` 崩溃。规避：`List<int>.new([...])`。
2. `== null` 比较崩溃。规避：envelope 原文 `"next_offset":null` 子串探测。
3. `json.to_string`/`json.encode` 对**动态 map** 返回内部句柄数字（如 `"18443647848969734400"`）——不可用作持久化写侧。规避：手工转义写 JSON（读侧 json.parse 可用）；类型化 struct 的 encode 待应用内验证。
4. `file.append_text` 在 Windows VM 报 os error 123。规避：read+write 拼接。
5. `hash.file_sha256` 对缺失文件抛 RuntimeError（stdlib 注释称返回空串，实况不符）。规避：调用前 `fs.exists` 门控。
6. 约 18 万次线性字符串拼接致 VM 静默退出（exit 0 无输出）。规避：倍增拼接；导入器禁止逐段拼接超长文本。
7. **（T-01 补录）`file.write_bytes`/`File.write_bytes` 在 VM 轨 rc=0 但不落盘**（静默失败）；a2r 轨映射存在。字节级写侧测试只能在应用外构造文件。
8. **（T-01 补录）跨模块 fn 调用的多字节字符串实参在脚本/测试上下文被剥离**（如「上卷」「作者五」传入后变空/残缺）；模块→模块调用正常（章节中文正文逐字校验通过）。脚本规格测试一律用 ASCII 路径与作者名，中文内容经文件本体（native 读）进入。
9. **（T-01 补录）VM 测试装置（#[test]）缺陷三则**：跨模块调用 + var 局部字符串累积会把模块变量名混入局部值；struct/List 作 fn 参数时元素字段清零/串位；模块级数值常量未初始化（除零）。规避：自包含模块单测（pathx/hashx/importers）+ 脚本规格测试（标量参数边界）+ 应用级 HTTP 验证。
10. **（T-01 补录）`ext` 是保留字**（Plan 035 类型扩展），不能作变量名。
11. **（T-01 终版修正·根因）本计划早期误判的多起「跨模块字符串实参剥离/struct str 字段清零」实为本仓代码缺陷**：pathx 的 `json_escape`/`normalize` 逐字节 `substr(i,1)` 走查会吞掉全部多字节字符（所有标题/正文/中文路径都流经它们）。改用原生 `replace` 链与 find+substr 渐进切片（字节一致语义，实测 find/substr/replace 均按字节索引且保多字节）后，中文路径/标题/正文全链路逐字一致。`for ch in str` 产出**整数码点**而非字符（且无码点→字符转换），字符级走查不可用。
12. **（T-01 补录）a2r（rust 后端）转译/编译面缺陷群**（`auto run` 缺省轨当前无法承载本模块，阻断证据=构建错误清单）：
    - `#[api]` 端点类型必须住 api.at（types.rs 仅收 api.at 的 pub 类型并给 serde 派生；其他模块的 pub struct 无 serde 派生，进不了 JsonResponse）；
    - 非 api/db 模块构造 api 导入类型 → 转译报误导性 `undefined variable`（同文件 own-type 构造在前还会毒化后续导入类型构造）；
    - 动态 JSON 字段访问不转译（`parsed.books` → `Value.books`，E0609 ×13）；
    - `auto_lang::a2r_std` 缺 `uuid`/`time`（转译器 emits、std 缺失）；
    - path-form `use src.back.x` 生成 `src::back::x` 与平坦 crate 布局不符（E0433）→ 共享模块只能 bare `use x`（生成 `crate::x` ✓），但 bare 形式在 VM 测试装置（#[test] 发现）下不可解析——两轨语法要求冲突；
    - `substr` 链式调用 i64/i32 失配；基线 `db.at get_chapter` 回退构造也被当前 dirty 构建转译坏（E0308）。
    结论：rust 后端轨登记为跨仓能力计划候选（auto-lang 仓库），本计划双轨交付改为 `auto run --server=vm`（Vue 前端 + AutoVM HTTP 后端）与 `auto run -r vm --server=vm`（VM 全轨），两条轨均实测通过（见 T-01 证据）。

## 对 READER-001 设计的决定

- **共享 back 代码只用双轨映射集**：`fs.exists/is_dir/file_size/read_text/write_text/create_dir` + `File.read_text_range` + `str.uuid` + `Env.get` + `json.parse` + 纯 .at 路径/转义助手。VM-only native 只出现在 tests/probe。
- **编码检测**：`File.read_text_range`（大写）双轨可用，envelope `total:-1` = 无法解码；辅以 `read_text 后 len != file_size` 交叉校验。
- **source_hash**：`hash.*` 无 a2r 映射，sha256 双轨不可用 → v1 用纯 .at 采样多项式哈希（算法名 `ph1`，写入 source_hash 前缀，import_version 可升级）；spec 增量如实记录能力边界（sha256 待运行时补齐后升级）。
- **mkdir_all 替代**：create_dir 按路径段逐级创建（纯 .at 助手）。
- **删除语义**：所有 delete native 均无双轨映射 → 书目移除采用「记录移除、内容文件保留」的可恢复设计（与 AC-05 一致，物理清理属后续显式动作），导入全程无需 delete。
- **文件选择 UI**：沿用 027-file-manager 模式——路径输入由 back 端点处理，Vue/VM 双轨同一 back 代码，无浏览器沙箱/VM DOM 分叉。
- **演示目录后备不适用**：本应用 rust 轨 back 不再落 Default 骨架——所有 fs 调用都在双轨映射集内，`#[api]` 端点保持 thin 体 + 普通 fn 实现的 Plan 400 纪律。

## 最小统一内容输出（T-01 接口预裁定）

导入器统一输出：`ImportedBook { book_id, source_hash(hash_algo+hex), title, author, format, chapters[] { number, title, body } , original_path, managed_path, size }`。TXT/Markdown 共用同一结构；章节切分规则：Markdown 按 ATX 标题（#/##）分章，TXT 按「第X章/Chapter X」行模式分章，无匹配则整本单章（标题取文件名 stem）。无匹配模式的边界在 T-01 以 fixture 固化。
