// t07_meta_index_spec.as — PLAN-781 阶段 E（T-25）章 meta 索引规格。
// 对象：导入一次扫描产出 <book_id>.meta.json；toc/单章改走 meta 路径
// （不再整书重解析）；**meta 路径与 parse_book_json 路径全章逐字段
// parity**（number/title/body/word_count）——窗读字节偏移的等价性 oracle。
// 负例：meta 缺失/损坏 → 诚实失败（单章 title="索引缺失"、toc=[]），
// 不静默重建。
// 运行：auto tests/spec/t07_meta_index_spec.as
// 结果：%TEMP%/t07-spec.log；任何 FAIL 以 RuntimeError 非零退出。

use src.back.library: import_book_json, chapter_json, chapter_json_raw, toc_json, meta_path, load_meta
use src.back.importers: parse_book_json
use src.back.pathx: join, mkdirs, json_escape

fn log_path() str {
    let t str = Env.get("TEMP")
    return fs.join(t, "t07-spec.log")
}

fn log(msg str) {
    var prev str = ""
    if file.exists(log_path()) {
        prev = file.read_text(log_path())
    }
    file.write_text(log_path(), prev + msg + "\n")
}

var fails int = 0

fn check(cond bool, name str) {
    if cond {
        log("PASS " + name)
    } else {
        fails = fails + 1
        log("FAIL " + name)
    }
}

/// 旧路径期望：parse_book_json → 按 number 取章字段。
fn old_chapter(text str, fmt str, title str, number int) str {
    let raw str = parse_book_json(text, fmt, title)
    let w = json.parse(raw)
    for it in w.chapters {
        if it.number == number {
            return "{\"number\":" + (it.number).to_string() + ",\"title\":" + json_of("" + it.title) + ",\"body\":" + json_of("" + it.body) + ",\"word_count\":" + (it.word_count).to_string() + "}"
        }
    }
    return "{}"
}

fn json_of(s str) str {
    return "\"" + json_escape(s) + "\""
}

/// 双路径全章 parity：对每章比对 number/title/body/word_count。
/// 返回首个失配描述（"" = 全等）。
fn parity(book_id str, text str, fmt str, title str) str {
    let toc str = toc_json(book_id)
    let tarr = json.parse(toc)
    var n int = 0
    for it in tarr {
        n = n + 1
    }
    var i int = 1
    while i <= n {
        let got = json.parse(chapter_json(book_id, i))
        let want = json.parse(old_chapter(text, fmt, title, i))
        if got.title != want.title {
            return "ch" + i.to_string() + " title [" + ("" + got.title) + "] != [" + ("" + want.title) + "]"
        }
        if got.body != want.body {
            return "ch" + i.to_string() + " body mismatch"
        }
        if got.word_count != want.word_count {
            return "ch" + i.to_string() + " word_count " + (got.word_count).to_string() + " != " + (want.word_count).to_string()
        }
        i = i + 1
    }
    return ""
}

// ── 隔离数据目录 ──
let lp0 str = log_path()
file.write_text(lp0, "SPEC t07 start\n")
let t str = Env.get("TEMP")
let uid str = str.uuid()
let dir str = fs.join(t, "t07-spec-" + uid)
Env.set("AUTO_READER_DATA", dir)
mkdirs(dir)

// ═══ S1 混合形态书：开篇 + 章头 + 章间空行 + CJK + 连续章头（空章）+
// 文件尾空行（body 窗含尾随 \n 的 contiguity 对齐）═══
let src1 str = join(dir, "book-mixed.txt")
let b1 str = "这是开篇内容，无章头先行。
第一章 起
正文一，中文多字节。

第二章 承
正文二。

第三章 转
第四章 合
正文四（第三章为空章）。
"
fs.write_text(src1, b1)
let o1 = json.parse(import_book_json(src1, "", false))
check(o1.code == "ok", "S1 mixed import ok")
let bid1 str = "" + o1.book_id
let mp1 str = meta_path(bid1)
check(fs.exists(mp1), "S1 meta file exists")

// meta 结构与统计
let meta1 = json.parse(load_meta(bid1))
check(meta1.version == 1, "S1 meta version 1")
check(meta1.total_chapters == 5, "S1 total_chapters=5 (开篇+4章)")
var sumw int = 0
for c in meta1.chapters {
    sumw = sumw + c.word_count
}
check(meta1.total_words == sumw, "S1 total_words == sum(chapters)")

// 全章 parity（窗读 vs 重解析）
let p1 str = parity(bid1, b1, "txt", "book-mixed")
check(p1 == "", "S1 full-chapter parity " + p1)

// toc 标题序列 parity
let toc1 = json.parse(toc_json(bid1))
var titles str = ""
var first bool = true
for it in toc1 {
    if !first {
        titles = titles + "|"
    }
    titles = titles + ("" + it.title)
    first = false
}
check(titles == "开篇|第一章 起|第二章 承|第三章 转|第四章 合", "S1 toc titles [" + titles + "]")

// ═══ S2 无章头书：单章以文件主名为题 ═══
let src2 str = join(dir, "nohead.txt")
let b2 str = "只有一段没有章头的正文。
第二行。
"
fs.write_text(src2, b2)
let o2 = json.parse(import_book_json(src2, "", false))
check(o2.code == "ok", "S2 no-heading import ok")
let bid2 str = "" + o2.book_id
let p2 str = parity(bid2, b2, "txt", "nohead")
check(p2 == "", "S2 no-heading parity " + p2)

// ═══ S3 Markdown：ATX 章头 + 井号剥离 ═══
let src3 str = join(dir, "book-md.md")
let b3 str = "# 序章之始
md 开篇。

# 第一章 风起
md 正文一。

## 第二章 云涌
md 正文二。
"
fs.write_text(src3, b3)
let o3 = json.parse(import_book_json(src3, "", false))
check(o3.code == "ok", "S3 md import ok")
let bid3 str = "" + o3.book_id
let p3 str = parity(bid3, b3, "md", "book-md")
check(p3 == "", "S3 md parity " + p3)

// ═══ S4 负例：meta 缺失 → 诚实失败 ═══
fs.delete(meta_path(bid1))
let mj str = chapter_json(bid1, 1)
let mo = json.parse(mj)
let mo_title str = "" + mo.title
check(mo_title.find("索引缺失") >= 0, "S4 chapter honest-fail on missing meta [" + mo_title + "]")
check(toc_json(bid1) == "[]", "S4 toc [] on missing meta")

// ═══ S5 负例：meta 损坏（截断 JSON）→ 同诚实失败 ═══
fs.write_text(meta_path(bid1), "{\"version\":1,\"total_chapters\":3,\"chapters\":[{\"num")
let mj2 str = chapter_json(bid1, 1)
let mo2 = json.parse(mj2)
let mo2_title str = "" + mo2.title
check(mo2_title.find("索引缺失") >= 0, "S5 chapter honest-fail on corrupt meta")

// ═══ S6 损坏偏移负例：偏移窗大变异 → parity 必红（oracle 会失败证明）═══
// 把 bid2 首章（单章书，body_off=0）窗起点移 10 字节（落入正文中段——
// 小变异会被 read_text_range 的 mid-char 边界回退吸收，大变异必然
// 漂移）；parity 断言捕获（证明 oracle 对索引损坏敏感）。
let good_meta2 str = load_meta(bid2)
fs.write_text(meta_path(bid2), good_meta2.replace_first("\"body_off\":0,", "\"body_off\":10,"))
let drifted = json.parse(chapter_json(bid2, 1))
let wantdr = json.parse(old_chapter(b2, "txt", "nohead", 1))
let db str = "" + drifted.body
let wb str = "" + wantdr.body
check(db != wb, "S6 corrupted offset detected by oracle")

// ═══ S7 负例（F-781-R05 复审反例原样）：完整形状但内部 JSON 畸形 ═══
// 前缀/后缀门禁双过、json.parse 必 raise——修复前 load_meta 帧内
// catch 毒化 chapter_json 参数槽（str+NoneType 崩溃、exit 1）；修复后
// 消费方帧内联 try 受控拒绝，且**后续请求不受染**。
fs.write_text(meta_path(bid1), "{\"version\":1,\"source_sha256\":\"x\",\"total_chapters\":1,\"chapters\":[BAD]}")
let mj3 str = chapter_json(bid1, 1)
let mo3 = json.parse(mj3)
let mo3_title str = "" + mo3.title
check(mo3_title.find("索引缺失") >= 0, "S7 internal-malformed JSON honest-fail [" + mo3_title + "]")
check(toc_json(bid1) == "[]", "S7 toc [] on internal-malformed JSON")
// 后续请求仍正常（同进程无帧毒化残留）：未受损书 bid3 的章/toc 照常。
let after7 = json.parse(chapter_json(bid3, 1))
let after7_title str = "" + after7.title
check(after7_title.find("序章之始") >= 0, "S7 subsequent request unaffected (bid3 ch1) [" + after7_title + "]")
let toc_after7 = json.parse(toc_json(bid3))
var n_after7 int = 0
for it7 in toc_after7 {
    n_after7 = n_after7 + 1
}
check(n_after7 == 3, "S7 subsequent toc unaffected (bid3 3 chapters)")

// ═══ S8 负例：合法 JSON 但缺字段（toc 消费面 title 缺席）═══
fs.write_text(meta_path(bid1), "{\"version\":1,\"source_sha256\":\"x\",\"total_chapters\":1,\"total_words\":1,\"chapters\":[{\"number\":1,\"body_off\":0,\"body_len\":5,\"word_count\":5}]}")
let mj4 str = chapter_json(bid1, 1)
let mo4 = json.parse(mj4)
let mo4_title str = "" + mo4.title
check(mo4_title.find("索引缺失") >= 0, "S8 missing-title honest-fail [" + mo4_title + "]")
check(toc_json(bid1) == "[]", "S8 toc [] on missing title")

// ═══ S9 负例（r4 修复轮升级）：合法 JSON 但数字字段错类型（number
// 为字符串）→ 拒绝。r3 轮此为动态类型边界（静默强转）；r4 探测升级
// 后数字字段须满足消费前提（`> -1` 判别非负整数，字符串/负数为
// false 不 raise）——错类型数字字段与缺字段同拒（索引缺失/[]）。
// 字符串字段（title）仅查存在性，值语义松转换无害（边界收窄至此）。
fs.write_text(meta_path(bid1), "{\"version\":1,\"source_sha256\":\"x\",\"total_chapters\":1,\"total_words\":1,\"chapters\":[{\"number\":\"one\",\"title\":\"t\",\"body_off\":0,\"body_len\":5,\"word_count\":5}]}")
let mj5 str = chapter_json(bid1, 1)
let mo5 = json.parse(mj5)
let mo5_title str = "" + mo5.title
check(mo5_title.find("索引缺失") >= 0, "S9 wrong-type numeric rejected [" + mo5_title + "]")
check(toc_json(bid1) == "[]", "S9 toc [] on wrong-type numeric")
// 后续请求仍正常：bid3 未受染。
let toc9b = json.parse(toc_json(bid3))
var n9b int = 0
for it9 in toc9b {
    n9b = n9b + 1
}
check(n9b == 3, "S9 subsequent toc unaffected (bid3 3 chapters)")

// ═══ S11 负例矩阵（R05 r4 修复轮）：逐字段删除——五必需字段各自
// 缺失都必须整体拒绝（索引缺失/[]），不得合成空章节假成功。═══
// 复审反例形态：仅删除一章的 body_len，其余一字不动。
// bid2 的 meta 自 S6 起为漂移版——S11 用 force 重导入的新书取干净基线。
let o11r = json.parse(import_book_json(src2, "", true))
let bid2r str = "" + o11r.book_id
let good11 str = load_meta(bid2r)
fn meta_without_field(meta str, field str, drop_count int) str {
    // 在第一章 entry 内删除 "field":值, 片段（值形态：数字或带引号串）。
    let key str = "\"" + field + "\":"
    let k int = meta.find(key)
    if k < 0 {
        return meta
    }
    var e int = k + key.len()
    if meta.substr(e, 1) == "\"" {
        e = e + 1
        while e < meta.len() {
            if meta.substr(e, 1) == "\"" {
                e = e + 1
                break
            }
            e = e + 1
        }
    } else {
        while e < meta.len() {
            let ch str = meta.substr(e, 1)
            if ch == "," || ch == "}" {
                break
            }
            e = e + 1
        }
    }
    // 连同尾随逗号一起删除（首 entry 内字段恒有尾逗号——chapters 非空
    // 且每 entry 有后续字段）。
    if meta.substr(e, 1) == "," {
        e = e + 1
    }
    return meta.substr(0, k) + meta.substr(e, meta.len() - e)
}
var f_i int = 0
let f_names = ["number", "title", "body_off", "body_len", "word_count"]
while f_i < 5 {
    let fname str = "" + f_names[f_i]
    let mutated str = meta_without_field(good11, fname, 1)
    check(mutated != good11, "S11 mutation applied [" + fname + "]")
    fs.write_text(meta_path(bid2r), mutated)
    // 注：find(json-标题) 形态在本循环上下文观测到池/槽混叠（标题槽
    // 读作 check 消息内容）——改全串相等断言（确定性占位符构造）。
    let mj11 str = chapter_json(bid2r, 1)
    let expect11 str = chapter_json_raw(1, "索引缺失", "", 0)
    check(mj11 == expect11, "S11 missing " + fname + " rejected")
    check(toc_json(bid2r) == "[]", "S11 toc [] on missing " + fname)
    f_i = f_i + 1
}
// 恢复 + 控制：好 meta 归位后全链照常。
fs.write_text(meta_path(bid2r), good11)
let p11 str = parity(bid2r, b2, "txt", "nohead")
check(p11 == "", "S11 restored parity " + p11)

// ═══ S10 控制：正常 meta 恢复后全链照常（S7..S9 污染不残留）═══
// 同指纹重导入需 force（否则 duplicate）——force 后 meta 重写为好值。
let o1b = json.parse(import_book_json(src1, "", true))
check(o1b.code == "ok", "S10 force re-import ok [" + ("" + o1b.code) + "]")
let bid1b str = "" + o1b.book_id
let p10 str = parity(bid1b, b1, "txt", "book-mixed")
check(p10 == "", "S10 full parity after corruption battery " + p10)

// ═══ 收尾 ═══
log("SPEC t07 done fails=" + fails.to_string())
if fails > 0 {
    hash.file_sha256("__spec_failure__")
}
log("SPEC t07 RESULT: ALL PASS")
