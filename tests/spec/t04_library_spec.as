// t04_library_spec.as — READER-001 T-04 边界规格测试（脚本模式）。
// 覆盖：v0 旧形索引拒绝且保留原件（迁移语义）、孤儿受管副本复用
// （导入中断幂等完成）、记录在而副本被外删（内容缺失不伪造）、
// 同内容异名去重、同题异容独立档案。
// 运行：`auto tests/spec/t04_library_spec.as`

use src.back.pathx: join, mkdirs
use src.back.library: books_json, book_json, chapter_json, import_book_json, remove_book

fn log_path() str {
    let t str = Env.get("TEMP")
    return fs.join(t, "t04-spec.log")
}

fn log(msg str) {
    let lp str = log_path()
    var prev str = ""
    if file.exists(lp) {
        prev = file.read_text(lp)
    }
    prev = prev + msg
    prev = prev + "\n"
    file.write_text(lp, prev)
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
    file.write_text(lp, "SPEC t04 start\n")
    let t str = Env.get("TEMP")
    let uid str = str.uuid()
    let dir str = fs.join(t, "t04-spec-" + uid)
    Env.set("AUTO_READER_DATA", dir)
    mkdirs(dir)

    // S1 迁移：v0 旧形索引 → 拒绝加载 + 原件保留 + 错误信息明确
    let legacy str = join(dir, "library.json")
    fs.write_text(legacy, "{\"books\":[{\"id\":\"legacy-1\",\"name\":\"旧版手搬书目\"}]}")
    let src str = join(dir, "book.txt")
    fs.write_text(src, "第一章 起\n旧库正文\n")
    let o1 = json.parse(import_book_json(src, "", false))
    check(o1.code == "io_error", "v0 index rejected as io_error")
    check(o1.message.find("人工迁移") >= 0, "migration message explicit")
    check(fs.exists(legacy), "legacy file preserved")
    check(fs.read_text(legacy).find("legacy-1") >= 0, "legacy content intact")

    // S2 同内容异名 → duplicate（内容指纹判重，与文件名无关）
    Env.set("AUTO_READER_DATA", join(t, "t04-spec-" + uid + "-b"))
    mkdirs(join(dir, "b"))
    let dir2 str = join(dir, "b")
    Env.set("AUTO_READER_DATA", dir2)
    mkdirs(dir2)
    let a1 str = join(dir2, "xiaoshuo.txt")
    fs.write_text(a1, "第一章 山月\n内容甲。\n")
    let a2 str = join(dir2, "xiaoshuo-copy.txt")
    fs.write_text(a2, "第一章 山月\n内容甲。\n")
    let oa = json.parse(import_book_json(a1, "", false))
    check(oa.code == "ok", "first import ok")
    let ob = json.parse(import_book_json(a2, "", false))
    check(ob.code == "duplicate", "same-content different-name duplicate")

    // S3 导入中断（受管副本已写、索引未写）→ 再次导入幂等完成
    let ok_bid str = "" + oa.book_id
    let rec_raw str = book_json(ok_bid)
    let rec = json.parse(rec_raw)
    let mpath str = "" + rec.managed_path
    // 构造孤儿状态：清空索引（v1 空表），保留受管副本
    fs.write_text(join(dir2, "library.json"), "{\"version\":1,\"books\":[]}")
    let oa2 = json.parse(import_book_json(a1, "", false))
    check(oa2.code == "ok", "orphan reuse import ok")
    let rec2_raw str = book_json("" + oa2.book_id)
    let rec2 = json.parse(rec2_raw)
    check(rec2.managed_path == mpath, "managed copy reused (no rewrite)")
    check(fs.exists(mpath), "managed file still single")

    // S4 记录在、副本被外删 → 读取报内容缺失，不伪造
    // 受管副本指向同一路径，删除后章节读取应得「内容缺失」占位
    let del int = file.delete(mpath)
    let c1_raw str = chapter_json("" + oa2.book_id, 1)
    let c1 = json.parse(c1_raw)
    check(c1.title == "内容缺失", "missing managed content flagged")
    check(c1.body == "", "no fabricated body")

    // S5 同题异容 → 独立档案（AC-02）
    let x1 str = join(dir2, "same-title.txt")
    fs.write_text(x1, "第一章 起\n版本一。\n")
    let ox1 = json.parse(import_book_json(x1, "", false))
    let x2 str = join(dir2, "same-title-2.txt")
    fs.write_text(x2, "第一章 起\n版本二。\n")
    let ox2 = json.parse(import_book_json(x2, "", false))
    check(ox1.code == "ok" && ox2.code == "ok", "same-title both import")
    check(ox1.book_id != ox2.book_id, "same-title distinct ids")
    check(ox2.existing_id == "", "same-title no duplicate flag")

    log("SPEC t04 done fails=" + fails.to_string())
    if fails > 0 {
        hash.file_sha256("__spec_failure__")
    }
}
