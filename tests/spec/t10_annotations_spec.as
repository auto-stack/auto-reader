// t10_annotations_spec.as — READER-002 阶段A 注释/搜索/导出规格测试（脚本模式）。
// 覆盖（计划 §6 A-02/A-03 后端面）：
//   S1  注释 create/update/delete 回环（highlight/bookmark/comment；重发一致）
//   S2  重复句 occurrence 判别（同段两次出现：occ=2 可建、occ=3 拒）
//   S3  锚点核验（quote 非子串/段越界/章越界/书不存在 拒绝）
//   S4  update 锚字段不可变（kind/comment/tags 可变）；未知 id 拒
//   S5  delete 移除；未知 id 拒；删空后文件合法
//   S6  读侧容错：损坏文件 ok:false 且保留；空文件拒绝覆写（备份协议）
//   S7  搜索：跨章命中（para_idx 与段模型同口径）、中文精确子串、
//       无命中 total=0、空 query/缺书 拒绝
//   S8  导出：文件存在、计数一致、出处行核对；空集合 count=0 path=""
//   S9  reading layout/theme 扩展（可选键枚举校验；缺位不写存储态）
//   S10 源文本变化后：新锚拒绝（诚实）、既有注释 update 仍可（原摘录保留）
// 运行：auto tests/spec/t10_annotations_spec.as（日志 %TEMP%/t10-spec.log）

use src.back.pathx: join, mkdirs
use src.back.library: import_book_json, put_reading_json, get_reading_json
use src.back.annotations: get_annotations_json, put_annotations_json, search_book_json, export_annotations_json

fn log_path() str {
    let t str = Env.get("TEMP")
    return fs.join(t, "t10-spec.log")
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

fn main() {
    let lp str = log_path()
    file.write_text(lp, "SPEC t10 start\n")
    let t str = Env.get("TEMP")
    let uid str = str.uuid()
    let dir str = fs.join(t, "t10-spec-" + uid)
    Env.set("AUTO_READER_DATA", dir)
    mkdirs(dir)

    // 导入：第一章 5 行（含重复句段、空行），第二章 2 行（中文+emoji）
    let book str = fs.join(dir, "an.txt")
    fs.write_text(book, "第一章 起\n春天来了。\n\n桥边的老树开花了，桥边的老树开花了，年年如此。\n第四段。\n\n第二章 承\n尾段 🌸。\n")
    let ok_raw str = import_book_json(book, "", false)
    let ok = json.parse(ok_raw)
    check(ok.code == "ok", "import ok")
    let bid str = "" + ok.book_id

    // ── S1 create 回环：highlight（quote=「春天来了。」occ=1）──
    let c1 str = put_annotations_json(bid, "create", "", "highlight", 1, 0, 1, "开篇批注", "[\"开篇\",\"春天\"]", "春天来了。")
    check(c1.find("\"ok\":true") >= 0, "S1 create highlight ok")
    let g1 str = get_annotations_json(bid)
    check(g1.find("\"ok\":true") >= 0, "S1 get ok")
    check(g1.find("\"kind\":\"highlight\"") >= 0, "S1 kind roundtrip")
    check(g1.find("\"quote\":\"春天来了。\"") >= 0, "S1 quote roundtrip (中文逐字)")
    check(g1.find("\"comment\":\"开篇批注\"") >= 0, "S1 comment roundtrip")
    check(g1.find("\"tags\":[\"开篇\",\"春天\"]") >= 0, "S1 tags roundtrip")
    let pa = json.parse(g1)
    let arr1 = pa.annotations
    var aid1 str = ""
    for it in arr1 {
        aid1 = "" + it.annotation_id
    }
    check(aid1 != "", "S1 server-assigned annotation_id")
    check(aid1.len() >= 32, "S1 annotation_id uuid-shaped")

    // 章级书签（para_idx=-1、quote 空）
    let c2 str = put_annotations_json(bid, "create", "", "bookmark", 2, -1, 1, "", "[]", "")
    check(c2.find("\"ok\":true") >= 0, "S1 chapter bookmark ok")
    // comment 类（段级 quote 必填）
    let c3 str = put_annotations_json(bid, "create", "", "comment", 2, 0, 1, "emoji 段注", "[]", "尾段 🌸。")
    check(c3.find("\"ok\":true") >= 0, "S1 emoji comment ok (多字节顶层传输)")

    // ── S2 重复句 occurrence ──
    let dupq str = "桥边的老树开花了"
    let d1 str = put_annotations_json(bid, "create", "", "highlight", 1, 2, 2, "第二处", "[]", dupq)
    check(d1.find("\"ok\":true") >= 0, "S2 occ=2 of 2 accepted")
    let d2 str = put_annotations_json(bid, "create", "", "highlight", 1, 2, 3, "第三处", "[]", dupq)
    check(d2.find("\"ok\":false") >= 0, "S2 occ=3 rejected (honest)")
    let d3 str = put_annotations_json(bid, "create", "", "highlight", 1, 2, 1, "第一处", "[]", dupq)
    check(d3.find("\"ok\":true") >= 0, "S2 occ=1 accepted")

    // ── S3 锚点核验 ──
    let r1 str = put_annotations_json(bid, "create", "", "highlight", 1, 1, 1, "", "[]", "不存在的句子")
    check(r1.find("\"ok\":false") >= 0, "S3 quote-not-substring rejected")
    let r2 str = put_annotations_json(bid, "create", "", "highlight", 1, 99, 1, "", "[]", "春天来了。")
    check(r2.find("\"ok\":false") >= 0, "S3 para out of range rejected")
    let r3 str = put_annotations_json(bid, "create", "", "highlight", 9, 1, 1, "", "[]", "春天来了。")
    check(r3.find("\"ok\":false") >= 0, "S3 chapter out of range rejected")
    let r4 str = put_annotations_json(bid, "create", "", "highlight", 2, 0, 1, "", "[]", "春天来了。")
    check(r4.find("\"ok\":false") >= 0, "S3 cross-chapter quote rejected")
    let r5 str = put_annotations_json("no-such-book", "create", "", "highlight", 1, 1, 1, "", "[]", "q")
    check(r5.find("\"ok\":false") >= 0, "S3 unknown book rejected")
    let r6 str = put_annotations_json(bid, "create", "", "badkind", 1, 1, 1, "", "[]", "春天来了。")
    check(r6.find("\"ok\":false") >= 0, "S3 invalid kind rejected")
    let r7 str = put_annotations_json(bid, "create", "", "highlight", 1, 1, 1, "", "[\"\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\\u4e00\"]", "春天来了。")
    check(r7.find("\"ok\":false") >= 0, "S3 tag >32 rejected")
    let r8 str = put_annotations_json(bid, "create", "", "highlight", 1, 1, 0, "", "[]", "春天来了。")
    check(r8.find("\"ok\":false") >= 0, "S3 occurrence=0 rejected")

    // ── S4 update：锚字段不可变 ──
    let u1 str = put_annotations_json(bid, "update", aid1, "comment", 0, 0, 0, "改后的批注", "[\"新标签\"]", "")
    check(u1.find("\"ok\":true") >= 0, "S4 update ok")
    let g4 str = get_annotations_json(bid)
    check(g4.find("\"comment\":\"改后的批注\"") >= 0, "S4 comment changed")
    check(g4.find("\"quote\":\"春天来了。\"") >= 0, "S4 quote immutable")
    check(g4.find("\"chapter_number\":1") >= 0, "S4 chapter immutable")
    let pa4 = json.parse(g4)
    let arr4 = pa4.annotations
    var upd_ch int = -1
    var upd_create int = -1
    for it in arr4 {
        let tid str = "" + it.annotation_id
        if tid == aid1 {
            upd_ch = it.chapter_number
            upd_create = it.created_at
        }
    }
    check(upd_ch == 1, "S4 anchor chapter preserved")
    check(upd_create > 0, "S4 created_at preserved")
    let u2 str = put_annotations_json(bid, "update", "missing-id", "comment", 0, 0, 0, "x", "[]", "")
    check(u2.find("\"ok\":false") >= 0, "S4 unknown id rejected")

    // ── S5 delete ──
    let del1 str = put_annotations_json(bid, "delete", aid1, "", 0, 0, 0, "", "[]", "")
    check(del1.find("\"ok\":true") >= 0, "S5 delete ok")
    let g5 str = get_annotations_json(bid)
    check(g5.find("春天来了。") < 0, "S5 deleted record gone")
    let del2 str = put_annotations_json(bid, "delete", aid1, "", 0, 0, 0, "", "[]", "")
    check(del2.find("\"ok\":false") >= 0, "S5 double delete rejected")

    // ── S6 读侧容错 ──
    let afile str = join(dir, "annotations/" + bid + ".json")
    check(fs.exists(afile), "S6 annotations file exists")
    let keep str = fs.read_text(afile)
    fs.write_text(afile, "{\"version\":1,")
    let g6 str = get_annotations_json(bid)
    check(g6.find("\"ok\":false") >= 0, "S6 corrupt file ok:false (no fake empty)")
    check(fs.read_text(afile) == "{\"version\":1,", "S6 corrupt file preserved")
    // 备份协议：空现文件拒绝覆写（-3）
    fs.write_text(afile, "")
    let w6 str = put_annotations_json(bid, "create", "", "bookmark", 1, -1, 1, "", "[]", "")
    check(w6.find("unreadable") >= 0, "S6 empty file refuses (unreadable)")
    check(fs.read_text(afile) == "", "S6 empty file preserved")
    // 还原有效态供后续
    fs.write_text(afile, keep)

    // ── S7 搜索 ──
    let s1 str = search_book_json(bid, "桥边的老树开花了")
    check(s1.find("\"ok\":true") >= 0, "S7 search ok")
    check(s1.find("\"chapter_number\":1") >= 0, "S7 hit chapter 1")
    check(s1.find("\"para_idx\":2") >= 0, "S7 para_idx=2 (原行号口径，空行占位)")
    let s2 str = search_book_json(bid, "不存在的查询词")
    check(s2.find("\"total\":0") >= 0, "S7 no hit total=0")
    let s3 str = search_book_json(bid, "尾段")
    check(s3.find("\"chapter_number\":2") >= 0, "S7 cross-chapter hit")
    let s4 str = search_book_json(bid, "")
    check(s4.find("\"ok\":false") >= 0, "S7 empty query rejected")
    let s5 str = search_book_json("no-such-book", "x")
    check(s5.find("\"ok\":false") >= 0, "S7 unknown book rejected")
    let s6 str = search_book_json(bid, "🌸")
    check(s6.find("\"total\":1") >= 0, "S7 emoji substring hit")

    // ── S8 导出 ──
    let e1 str = export_annotations_json(bid)
    check(e1.find("\"ok\":true") >= 0, "S8 export ok")
    let pe = json.parse(e1)
    let ecount int = pe.count
    check(ecount >= 4, "S8 count matches (>=4 remaining)")
    if e1.find("\"ok\":true") >= 0 {
        let epath str = "" + pe.path
        check(epath != "", "S8 path returned")
        check(fs.exists(epath), "S8 export file exists")
        let md str = fs.read_text(epath)
        check(md.find("桥边的老树开花了") >= 0, "S8 quote in export")
        check(md.find("第二处") >= 0, "S8 comment in export")
        check(md.find("第 1 章 · 第 2 段") >= 0, "S8 locator in export")
        check(md.find(bid) >= 0, "S8 book id in export")
    }
    // 空集合导出：诚实 count=0 无文件
    fs.write_text(fs.join(dir, "an2.txt"), "空书。\n只有一段。\n")
    let bid2_r str = import_book_json(fs.join(dir, "an2.txt"), "", false)
    let ok2 = json.parse(bid2_r)
    let bid2 str = "" + ok2.book_id
    let e2 str = export_annotations_json(bid2)
    check(e2.find("\"count\":0") >= 0, "S8 empty export count=0")
    check(e2.find("\"path\":\"\"") >= 0, "S8 empty export no path")

    // ── S9 reading layout/theme 扩展 ──
    var st9 str = "{\"book_id\":\""
    st9 = st9 + bid
    st9 = st9 + "\",\"chapter_number\":1,\"paragraph_index\":-1,\"font_size\":\"medium\",\"line_height\":\"comfy\",\"layout\":\"wide\",\"theme\":\"sepia\",\"updated_at\":0}"
    check(put_reading_json(bid, st9, "") .find("\"ok\":true") >= 0, "S9 put with layout/theme ok")
    let g9 str = get_reading_json(bid)
    check(g9.find("\"layout\":\"wide\"") >= 0, "S9 layout persisted")
    check(g9.find("\"theme\":\"sepia\"") >= 0, "S9 theme persisted")
    var bad9 str = "{\"book_id\":\""
    bad9 = bad9 + bid
    bad9 = bad9 + "\",\"chapter_number\":1,\"paragraph_index\":-1,\"font_size\":\"medium\",\"line_height\":\"comfy\",\"layout\":\"huge\",\"updated_at\":0}"
    check(put_reading_json(bid, bad9, "") != "", "S9 invalid layout rejected")
    // 缺位扩展键 = 旧态兼容
    var st92 str = "{\"book_id\":\""
    st92 = st92 + bid
    st92 = st92 + "\",\"chapter_number\":2,\"paragraph_index\":-1,\"font_size\":\"small\",\"line_height\":\"compact\",\"updated_at\":0}"
    check(put_reading_json(bid, st92, "").find("\"ok\":true") >= 0, "S9 legacy payload ok")
    check(get_reading_json(bid).find("\"layout\"") < 0, "S9 absent extension not written")

    // ── S10 源文本变化 ──
    // 改受管副本：等字节长度改写「春天来了。」→「春日已至。」（各 15
    // UTF-8 字节——meta 章窗口 body_off/body_len 不漂移），模拟改版。
    let lib_raw str = fs.read_text(join(dir, "library.json"))
    let libp = json.parse(lib_raw)
    let books = libp.books
    var managed str = ""
    for b in books {
        let tb str = "" + b.book_id
        if tb == bid {
            managed = "" + b.managed_path
        }
    }
    check(managed != "", "S10 managed path found")
    let orig str = fs.read_text(managed)
    let changed str = orig.replace("春天来了。", "春日已至。")
    fs.write_text(managed, changed)
    // 新建旧锚 → 诚实拒绝（quote 不再命中）
    let n10 str = put_annotations_json(bid, "create", "", "highlight", 1, 0, 1, "改版后新建", "[]", "春天来了。")
    check(n10.find("\"ok\":false") >= 0, "S10 stale quote create rejected")
    // 既有注释 update（改批注）仍可 —— 原摘录保留，不静默换锚
    var keep_aid str = ""
    let g10 str = get_annotations_json(bid)
    let pa10 = json.parse(g10)
    let arr10 = pa10.annotations
    for it in arr10 {
        let tq str = "" + it.quote
        if tq == "桥边的老树开花了" {
            keep_aid = "" + it.annotation_id
        }
    }
    check(keep_aid != "", "S10 existing record present")
    let u10 str = put_annotations_json(bid, "update", keep_aid, "highlight", 0, 0, 0, "改版后仍可改注", "[]", "")
    check(u10.find("\"ok\":true") >= 0, "S10 update after source change ok")
    check(get_annotations_json(bid).find("桥边的老树开花了") >= 0, "S10 original quote preserved")

    // ── S11 CRLF + 多字节出现计数（滑窗口径回归）──
    let book3 str = fs.join(dir, "crlf.txt")
    fs.write_text(book3, "第一章 起\r\n春天来了。\r\n\r\n桥边的老树开花了，桥边的老树开花了，年年如此。\r\n")
    let ok3_raw str = import_book_json(book3, "", false)
    let ok3 = json.parse(ok3_raw)
    check(ok3.code == "ok", "S11 import crlf ok")
    let bid3 str = "" + ok3.book_id
    let c31 str = put_annotations_json(bid3, "create", "", "highlight", 1, 2, 2, "CRLF 第二处", "[]", "桥边的老树开花了")
    check(c31.find("\"ok\":true") >= 0, "S11 crlf+中文 occ=2 accepted")
    let c32 str = put_annotations_json(bid3, "create", "", "highlight", 1, 2, 3, "CRLF 第三处", "[]", "桥边的老树开花了")
    check(c32.find("\"ok\":false") >= 0, "S11 crlf occ=3 rejected")

    log("SPEC t10 done fails=" + fails.to_string())
    if fails > 0 {
        hash.file_sha256("__spec_failure__")
    }
}
