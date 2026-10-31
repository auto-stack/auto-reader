# READER-003 框架前置缺口报告（framework-gap）

日期：2026-10-31 · 提出方：READER-003 T-01（work 阶段，goal 会话）
运行时：`auto 0.1.0+v0.0.20-118-ge6cc06f`（D:/autostack/auto-man/target/debug/auto.exe）
影响：纯 .at DEFLATE 解压无法可靠实现——READER-003（最小 EPUB）work 阶段
按计划 CAP-01 路由 **blocked**，待框架侧最小前置交付回执。

## 缺陷目录（全部可复现，探针在本仓 tests/probe/，原始日志 %TEMP%/t00-*.log）

| ID | 症状 | 最小复现 | 影响 |
|---|---|---|---|
| N-003-1 | `file.write_bytes` 对 `List<int>.new([])`+push 构建的列表 raise；种子字面量（`new([0])`+push）可绕 | t00_epub_cap_probe5 T2/T1 | 字节写侧需非常规形态 |
| N-003-2 | `file.read_bytes` 产物 `len()` 虚报（5 字节文件报 7）；越界索引 raise | t00_epub_cap_probe4 S1 | 真实长度只能用 `fs.file_size` |
| N-003-3 | 脚本（.as）上下文 `to_int`/var 累加出现字符串拼接毒化与字符串池串扰 | t00_epub_cap_probe6-8 | 脚本测试正确性 |
| N-003-4 | FFI 创建的列表（read_bytes 产物）作为 fn 参数跨边界后，模块内读值失真 | t00_param（期望 11211，实测否） | 字节必须「同帧读同帧用」 |
| N-003-5 | **同一循环迭代内 ≥3 次计算索引列表读 → 值失真；≤2 次安全** | t00_mr（4 读 FAIL）/t00_two（2 读 PASS） | 表驱动算法（哈夫曼）受限 |
| N-003-6 | 嵌套循环+分支上下文中的表读系统性偏移：固定表解码 130KB 文本流，前 32 字面量后首个长度码解码输出 = 期望值逐字节 **+7**（partial_out.bin vs 期望文本，解码状态 trace 全对：code=1/cl=7/cnt=24/first=0/index=0） | inflate_file（src/back/inflatex.at）+ t00_inflate_probe | 哈夫曼/查表解码不可靠 |

## 已验证可靠的原语（可作为修复后的语义基准）

- 单层 while + 类型化 `let` 提取 + 自累加（`x = x + e`）：值与顺序均正确
  （probe/9 X1-X3、probe2 Q9 200k 元素求和）。
- 列表 push（含 1M 元素）；callee 对 List 形参 push 对调用方可见
  （t00_list_param、t00_seed_callee）。
- `file.read_bytes` 在**同帧**类型化索引逐字节精确（probe/9 X2 与 Python
  hex dump 逐字节一致）；`hash.file_sha256`/`hash.sha256` 已知向量 PASS。
- `file.copy` 二进制逐字节（sha256 相等）；种子字面量 + push 的
  `write_bytes` 64KB 规模回环 PASS。

## 参考实现（修复验证基准）

`src/back/inflatex.at`：完整 RFC 1951 inflate（stored/固定/动态哈夫曼、
位展开平面游标、puff 解码、预算上限），已按上列「已验证形态」纪律编写，
可在当前运行时编译运行；在 N-003-6 修复的运行时上，应直接通过：

```
python 生成向量（zlib.compressobj(9, DEFLATED, -15)，~70KB 文本）
"D:/autostack/auto-man/target/debug/auto.exe" tests/probe/t00_inflate_probe.as
→ 期望日志 PASS 全文逐字一致（write+read_text oracle）
```

## 给框架 owner 的最小修复选项（任一即解除阻断）

- **选项 A（最小）**：修复 VM 列表读值失真（N-003-5/6 根因——怀疑
  FFI `ListData<i32>` 与 .at `List<int>` 表示不匹配引发的池槽别名，
  convert.rs `VMConvertible for Vec<i32>` push_to_stack 路径），使
  inflatex 参考实现直接通过。附带修复 N-003-1/2/4。
- **选项 B（替代）**：提供 `zip`/inflate native（如 `zip.open` +
  `zip.read_entry` 或 `inflate(data []int, out []int) int`），app 放弃
  纯 .at inflate（inflatex.at 归档为能力研究记录）。

任一选项交付后，READER-003 按计划 §10.5 路由恢复：T-01 以
t00_inflate_probe 全绿 + E-01..06 续跑，计划目标、AC、范围不变。

## 证据文件

- 探针：tests/probe/t00_epub_cap_probe{,2..10}.as、t00_{idx_assign,inflate,
  fn_list,list_param,seed_callee,alias,ht_dump,mod_selftest,dynlit,mini,
  mini2,mini5,v67,v8,tri,comp,param,mread,afterexp,nested,ifbr,mr,two,
  expand}.as、byte_module_probe.at
- 运行时失真直接证据：%TEMP%/partial_out.bin（+7 位移输出）对照
  %TEMP%/t00-epub-cap-probe/vec_fixed_expected.txt
- 能力决策与预算：docs/plans/evidence/003/capability-decision.md
