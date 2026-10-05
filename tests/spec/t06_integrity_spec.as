// t06_integrity_spec.as — READER-001 Phase 2 T-06 完整性/写协议规格（脚本模式）。
// 修复对象 F-03（损坏受管副本不得产生成功导入）与 F-06（空/损坏索引不得
// 被当新库覆盖；备份失败必须中止索引改写；remove/restore 日志写入必须
// 校验返回值）。
// 演练纪律：file.delete 无法删除目录（实测）——目录占位类演练一律使用
// 独立数据目录，不做不可逆的现场恢复。
// 运行：auto tests/spec/t06_integrity_spec.as
// 结果：%TEMP%/t06-spec.log；任何 FAIL 以 RuntimeError 非零退出。

use src.back.library: books_json, book_json, chapter_json, import_book_json, remove_book, restore_book
use src.back.pathx: join, mkdirs

fn log_path() str {
    let t str = Env.get("TEMP")
    return fs.join(t, "t06-spec.log")
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
    let lp0 str = log_path()
    file.write_text(lp0, "SPEC t06 start\n")
    let t str = Env.get("TEMP")
    let uid str = str.uuid()

    // ═══ S1/S2/S3/S4 共享库：基线 + 索引损坏族（文件态，可恢复） ═══
    let dir str = fs.join(t, "t06-spec-" + uid)
    Env.set("AUTO_READER_DATA", dir)
    mkdirs(dir)
    let src1 str = join(dir, "book-one.txt")
    fs.write_text(src1, "第一章 起\n正文一。\n第二章 承\n正文二。\n")
    let src2 str = join(dir, "book-two.txt")
    fs.write_text(src2, "第一章 另起\n另一本正文。\n")

    let o1 = json.parse(import_book_json(src1, "", false))
    check(o1.code == "ok", "baseline first import")
    let o2 = json.parse(import_book_json(src2, "", false))
    check(o2.code == "ok", "baseline second import")
    let libfile str = join(dir, "library.json")
    let idx_before str = fs.read_text(libfile)
    let o3 = json.parse(import_book_json(src1, "", true))
    check(o3.code == "ok", "baseline force import")
    let bakfile str = libfile + ".bak"
    check(fs.read_text(bakfile) == idx_before, "bak holds pre-write index verbatim")
    let idx_after str = fs.read_text(libfile)

    // S2 索引被清空（0 字节）→ 拒绝导入且原件保留（F-06 case1）
    fs.write_text(libfile, "")
    let oc = json.parse(import_book_json(src1, "", false))
    check(oc.code == "io_error", "empty existing index rejected")
    check(oc.message.find("迁移") >= 0, "empty index rejection explicit")
    check(fs.read_text(libfile) == "", "empty index file preserved byte-identical")

    // S3 损坏（非合法 JSON）索引 → 拒绝且保留
    fs.write_text(libfile, "{\"version\":1,\"books\":[")
    let od = json.parse(import_book_json(src1, "", false))
    check(od.code == "io_error", "corrupt index rejected")
    check(fs.read_text(libfile) == "{\"version\":1,\"books\":[", "corrupt index preserved")

    // S4 schema 缺 books 字段 → 拒绝且保留
    fs.write_text(libfile, "{\"version\":1}")
    let oe = json.parse(import_book_json(src1, "", false))
    check(oe.code == "io_error", "schema-missing-books index rejected")
    check(fs.read_text(libfile) == "{\"version\":1}", "schema-violating index preserved")

    // 恢复有效索引，继续用本库演练备份失败与损坏副本
    fs.write_text(libfile, idx_after)
    check(books_json().find("book_id") > 0, "index restored readable")

    // ═══ S5 F-06 case2：备份位被目录占位（独立数据目录，不可逆演练） ═══
    let dir5 str = fs.join(t, "t06-spec-" + uid + "-bak")
    Env.set("AUTO_READER_DATA", dir5)
    mkdirs(dir5)
    let s5a str = join(dir5, "a.txt")
    fs.write_text(s5a, "第一章 甲\n甲正文。\n")
    let s5b str = join(dir5, "b.txt")
    fs.write_text(s5b, "第一章 乙\n乙正文。\n")
    let oa5 = json.parse(import_book_json(s5a, "", false))
    check(oa5.code == "ok", "bak-drill setup import ok")
    let lib5 str = join(dir5, "library.json")
    let idx5 str = fs.read_text(lib5)
    file.delete(join(dir5, "library.json.bak"))
    mkdirs(join(dir5, "library.json.bak"))
    let ob5 = json.parse(import_book_json(s5b, "", false))
    check(ob5.code == "io_error", "backup failure aborts import")
    check(ob5.message.find("索引写入失败") >= 0, "backup abort surfaces index error")
    check(fs.read_text(lib5) == idx5, "index untouched on backup failure")
    check(book_json("" + oa5.book_id) != "", "existing book intact on aborted import")

    // ═══ S6 索引位被目录占位（独立数据目录） ═══
    let dir6 str = fs.join(t, "t06-spec-" + uid + "-idxdir")
    Env.set("AUTO_READER_DATA", dir6)
    mkdirs(dir6)
    mkdirs(join(dir6, "library.json"))
    let s6a str = join(dir6, "c.txt")
    fs.write_text(s6a, "第一章 丙\n丙正文。\n")
    let oc6 = json.parse(import_book_json(s6a, "", false))
    check(oc6.code == "io_error", "directory-occupied index rejected")

    // ═══ S7 F-03：损坏受管副本的修复语义（回到主库） ═══
    Env.set("AUTO_READER_DATA", dir)
    let r1_raw str = book_json("" + o1.book_id)
    let r1 = json.parse(r1_raw)
    let mpath1 str = "" + r1.managed_path
    let saved_asset str = fs.read_text(mpath1)
    fs.write_text(mpath1, "")
    // 非 force：内容无法证实 → 不判重，不产生假成功
    let oh = json.parse(import_book_json(src1, "", false))
    check(oh.code == "ok", "corroded copy: plain reimport not falsely deduplicated")
    let oi = json.parse(import_book_json(src1, "", true))
    check(oi.code == "ok", "corroded copy: force import proceeds")
    let rnew_raw str = book_json("" + oi.book_id)
    let rnew = json.parse(rnew_raw)
    let mnew str = "" + rnew.managed_path
    check(mnew != mpath1, "repair goes to isolated asset")
    check(fs.read_text(mnew) == saved_asset, "repaired asset verbatim source")
    check(fs.read_text(mpath1) == "", "corroded asset not silently rewritten")
    check(rnew.size == saved_asset.len(), "new record size matches verified copy")
    // 损坏记录读取面诚实：内容缺失占位，不伪造
    let cbroken str = json.parse(chapter_json("" + o1.book_id, 1))
    check(cbroken.title == "内容缺失", "corroded record reads as missing (honest)")
    // 恢复现场：把主槽位还原为原内容，旧记录恢复可读
    fs.write_text(mpath1, saved_asset)
    let cok str = json.parse(chapter_json("" + o1.book_id, 1))
    check(cok.body != "", "corroded record readable after manual asset restore")

    // ═══ S8 remove：日志位被目录占位 → 移除中止（独立数据目录） ═══
    let dir8 str = fs.join(t, "t06-spec-" + uid + "-rem")
    Env.set("AUTO_READER_DATA", dir8)
    mkdirs(dir8)
    let s8a str = join(dir8, "r.txt")
    fs.write_text(s8a, "第一章 移除演练\n演练正文。\n")
    let or8 = json.parse(import_book_json(s8a, "", false))
    check(or8.code == "ok", "remove-drill setup import ok")
    mkdirs(join(dir8, "removed.jsonl"))
    let lib8 str = join(dir8, "library.json")
    let idx8 str = fs.read_text(lib8)
    check(remove_book("" + or8.book_id) != "", "remove aborted on log-write failure")
    check(fs.read_text(lib8) == idx8, "index untouched when remove aborted")
    check(book_json("" + or8.book_id) != "", "book still listed after aborted remove")

    // ═══ S9 正常 remove → restore → 重复 restore 明确报错（回到主库） ═══
    Env.set("AUTO_READER_DATA", dir)
    let r2_raw str = book_json("" + o2.book_id)
    let r2 = json.parse(r2_raw)
    check(remove_book("" + o2.book_id) == "", "remove ok for restore drill")
    let remfile str = join(dir, "removed.jsonl")
    check(fs.exists(remfile), "removed log exists")
    check(restore_book("" + o2.book_id) == "", "restore ok")
    check(fs.read_text(remfile) == "", "log line removed after restore")
    check(restore_book("" + o2.book_id) != "", "second restore explicit error")
    let c2 str = json.parse(chapter_json("" + o2.book_id, 1))
    check(c2.body == "另一本正文。", "restored book chapters verbatim")

    // ═══ S10 中断语义保持：合法空 v1 索引 + 孤儿副本 → 幂等复用 ═══
    let dir2 str = join(dir, "orphan")
    Env.set("AUTO_READER_DATA", dir2)
    mkdirs(dir2)
    let osrc str = join(dir2, "orphan-src.txt")
    fs.write_text(osrc, "第一章 孤儿\n孤儿正文。\n")
    let oo = json.parse(import_book_json(osrc, "", false))
    check(oo.code == "ok", "orphan drill first import")
    let orec_raw str = book_json("" + oo.book_id)
    let orec = json.parse(orec_raw)
    let ompath str = "" + orec.managed_path
    fs.write_text(join(dir2, "library.json"), "{\"version\":1,\"books\":[]}")
    let oo2 = json.parse(import_book_json(osrc, "", false))
    check(oo2.code == "ok", "orphan reimport completes")
    let orec2_raw str = book_json("" + oo2.book_id)
    let orec2 = json.parse(orec2_raw)
    check("" + orec2.managed_path == ompath, "orphan asset reused (no new copy)")
    check(fs.read_text(ompath) == "第一章 孤儿\n孤儿正文。\n", "orphan asset verbatim")

    // ═══ S11 数据目录被文件占位 → mkdirs 失败，导入早期明确失败 ═══
    let dir3 str = join(dir, "occupied")
    fs.write_text(dir3, "not a dir")
    Env.set("AUTO_READER_DATA", dir3)
    let oj = json.parse(import_book_json(src1, "", false))
    check(oj.code == "io_error", "occupied data dir fails early")
    Env.set("AUTO_READER_DATA", dir)

    // ═══ S12 暂存物与提交内容一致（暂存校验证据） ═══
    let tmpfile str = libfile + ".tmp"
    check(fs.read_text(tmpfile) == fs.read_text(libfile), "staged tmp matches committed index")

    log("SPEC t06 done fails=" + fails.to_string())
    if fails > 0 {
        hash.file_sha256("__spec_failure__")
    }
}
