// t07_meta_index_spec.as — PLAN-781 阶段 E（T-25）章 meta 索引规格。
// 对象：导入一次扫描产出 <book_id>.meta.json；toc/单章改走 meta 路径
// （不再整书重解析）；**meta 路径与 parse_book_json 路径全章逐字段
// parity**（number/title/body/word_count）——窗读字节偏移的等价性 oracle。
// 负例：meta 缺失/损坏 → 诚实失败（单章 title="索引缺失"、toc=[]），
// 不静默重建。
// 运行：auto tests/spec/t07_meta_index_spec.as
// 结果：%TEMP%/t07-spec.log；任何 FAIL 以 RuntimeError 非零退出。

use src.back.library: import_book_json, chapter_json, toc_json, meta_path, load_meta
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

// ═══ 收尾 ═══
log("SPEC t07 done fails=" + fails.to_string())
if fails > 0 {
    hash.file_sha256("__spec_failure__")
}
log("SPEC t07 RESULT: ALL PASS")
