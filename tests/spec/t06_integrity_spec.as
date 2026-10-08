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

/// S13 助手：把 record 中 "size":N 的字面量替换为给定文本（首个 "size" 唯一）。
fn size_replaced(rj str, v str) str {
    let key str = "\"size\":"
    let k int = rj.find(key)
    let head str = rj.substr(0, k + key.len())
    var e int = k + key.len()
    while e < rj.len() {
        if rj.substr(e, 1) == "," {
            break
        }
        e = e + 1
    }
    let tail str = rj.substr(e, rj.len() - e)
    return head + v + tail
}

/// S13 助手：把 record 中首个 "key":"old" 的值替换为 v（用于内层身份不一致）。
fn first_str_replaced(rj str, key str, v str) str {
    let pat str = "\"" + key + "\":\""
    let k int = rj.find(pat)
    let head str = rj.substr(0, k + pat.len())
    var e int = k + pat.len()
    while e < rj.len() {
        if rj.substr(e, 1) == "\"" {
            break
        }
        e = e + 1
    }
    let tail str = rj.substr(e, rj.len() - e)
    return head + v + tail
}

/// S13 助手：构造 remove_book 同构的移除日志行。
fn removed_envelope(bid str, rj str) str {
    var out str = "{\"book_id\":\""
    out = out + bid
    out = out + "\",\"removed_at\":0,\"record\":"
    out = out + rj
    out = out + "}"
    return out
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

    // S4b F-11：错误 books 形态（对象/null/字符串/数字）→ 一律拒绝且
    // 原件逐字保留——绝不把损坏形态当空库覆盖
    fs.write_text(libfile, "{\"version\":1,\"books\":{}}")
    let o_f11a = json.parse(import_book_json(src1, "", false))
    check(o_f11a.code == "io_error", "books-as-object rejected")
    check(fs.read_text(libfile) == "{\"version\":1,\"books\":{}}", "books-object preserved")
    fs.write_text(libfile, "{\"version\":1,\"books\":null}")
    let o_f11b = json.parse(import_book_json(src1, "", false))
    check(o_f11b.code == "io_error", "books-null rejected")
    check(fs.read_text(libfile) == "{\"version\":1,\"books\":null}", "books-null preserved")
    fs.write_text(libfile, "{\"version\":1,\"books\":\"x\"}")
    let o_f11c = json.parse(import_book_json(src1, "", false))
    check(o_f11c.code == "io_error", "books-string rejected")
    fs.write_text(libfile, "{\"version\":1,\"books\":5}")
    let o_f11d = json.parse(import_book_json(src1, "", false))
    check(o_f11d.code == "io_error", "books-number rejected")
    fs.write_text(libfile, "{\"version\":\"1\",\"books\":[]}")
    let o_f11e = json.parse(import_book_json(src1, "", false))
    check(o_f11e.code == "io_error", "string version rejected")
    fs.write_text(libfile, "{\"version\":1,\"books\":[{\"book_id\":5}]}")
    let o_f11f = json.parse(import_book_json(src1, "", false))
    check(o_f11f.code == "io_error", "record wrong field type rejected")
    // S4c F-15：数值元数据字段小数/指数 → 拒绝且原件逐字保留
    fs.write_text(libfile, "{\"version\":1,\"books\":[{\"book_id\":\"a\",\"source_hash\":\"h\",\"title\":\"t\",\"author\":\"a\",\"format\":\"txt\",\"original_path\":\"o\",\"managed_path\":\"m\",\"size\":1.5,\"chapter_count\":1,\"import_version\":1,\"created_at\":0}]}")
    let o_f15a = json.parse(import_book_json(src1, "", false))
    check(o_f15a.code == "io_error", "record size 1.5 rejected")
    check(fs.read_text(libfile).find("1.5") >= 0, "size-1.5 index preserved")
    fs.write_text(libfile, "{\"version\":1,\"books\":[{\"book_id\":\"a\",\"source_hash\":\"h\",\"title\":\"t\",\"author\":\"a\",\"format\":\"txt\",\"original_path\":\"o\",\"managed_path\":\"m\",\"size\":1,\"chapter_count\":1,\"import_version\":1.5,\"created_at\":0}]}")
    let o_f15b = json.parse(import_book_json(src1, "", false))
    check(o_f15b.code == "io_error", "record import_version 1.5 rejected")
    fs.write_text(libfile, "{\"version\":1,\"books\":[{\"book_id\":\"a\",\"source_hash\":\"h\",\"title\":\"t\",\"author\":\"a\",\"format\":\"txt\",\"original_path\":\"o\",\"managed_path\":\"m\",\"size\":1,\"chapter_count\":1,\"import_version\":1,\"created_at\":1.5e2}]}")
    let o_f15c = json.parse(import_book_json(src1, "", false))
    check(o_f15c.code == "io_error", "record created_at exponent rejected")
    // 合法整数记录仍可导入
    fs.write_text(libfile, "{\"version\":1,\"books\":[{\"book_id\":\"a\",\"source_hash\":\"h\",\"title\":\"t\",\"author\":\"a\",\"format\":\"txt\",\"original_path\":\"o\",\"managed_path\":\"m\",\"size\":3,\"chapter_count\":1,\"import_version\":1,\"created_at\":0}]}")
    let o_f15d = json.parse(import_book_json(src1, "", false))
    check(o_f15d.code == "duplicate" || o_f15d.code == "ok", "valid integer record importable", o_f15d)
    fs.write_text(libfile, idx_after)

    // 恢复有效索引，继续用本库演练备份失败与损坏副本
    fs.write_text(libfile, "{\"version\":1,\"books\":[]}")
    let o_f11g = json.parse(import_book_json(src1, "", false))
    check(o_f11g.code == "ok", "valid empty array still importable")
    fs.write_text(libfile, idx_after)

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

    // ═══ S13 F-18：恢复消费者准入——移除日志不是可信输入（Phase 6 T-29） ═══
    // 真实移除生成日志行，改写 record/外层后恢复：非法（小数/越界/结构坏/
    // 身份换绑）一律拒绝且主库/备份/暂存/移除日志/受管资产逐字不变；
    // 合法恢复、i32 最大/最小边界与未知合法键保持成功且无损。
    let dir13 str = fs.join(t, "t06-spec-" + uid + "-f18")
    Env.set("AUTO_READER_DATA", dir13)
    mkdirs(dir13)
    let s13 str = join(dir13, "f18.txt")
    fs.write_text(s13, "第一章 恢复准入\n准入正文。\n")
    let o13 = json.parse(import_book_json(s13, "", false))
    check(o13.code == "ok", "f18 setup import ok")
    let bid13 str = "" + o13.book_id
    let rj13 str = book_json(bid13)
    let rec13 = json.parse(rj13)
    let mp13 str = "" + rec13.managed_path
    let asset13 str = fs.read_text(mp13)
    check(remove_book(bid13) == "", "f18 real remove ok")
    let rem13 str = join(dir13, "removed.jsonl")
    let lib13 str = join(dir13, "library.json")
    let log13 str = fs.read_text(rem13)
    let lib13b str = fs.read_text(lib13)
    let bak13b str = fs.read_text(lib13 + ".bak")
    let tmp13b str = fs.read_text(lib13 + ".tmp")
    check(log13 == removed_envelope(bid13, rj13) + "\n", "f18 log line is verbatim envelope")
    // 负例：record.size 小数——拒绝且全部既有字节不变（r6 反例永久化）
    let bad15 str = removed_envelope(bid13, size_replaced(rj13, "1.5"))
    fs.write_text(rem13, bad15)
    check(restore_book(bid13) != "", "f18 size 1.5 restore rejected")
    check(fs.read_text(lib13) == lib13b, "f18 size 1.5 library unchanged")
    check(fs.read_text(rem13) == bad15, "f18 size 1.5 log unchanged")
    check(fs.read_text(lib13 + ".bak") == bak13b, "f18 size 1.5 backup unchanged")
    check(fs.read_text(lib13 + ".tmp") == tmp13b, "f18 size 1.5 staging unchanged")
    check(fs.read_text(mp13) == asset13, "f18 size 1.5 asset unchanged")
    // 负例：record.size 正越界（r6 反例永久化）
    let badup str = removed_envelope(bid13, size_replaced(rj13, "2147483648"))
    fs.write_text(rem13, badup)
    check(restore_book(bid13) != "", "f18 size 2147483648 restore rejected")
    check(fs.read_text(lib13) == lib13b, "f18 size 2147483648 library unchanged")
    check(fs.read_text(rem13) == badup, "f18 size 2147483648 log unchanged")
    // 负例：record.size 负越界
    let baddn str = removed_envelope(bid13, size_replaced(rj13, "-2147483649"))
    fs.write_text(rem13, baddn)
    check(restore_book(bid13) != "", "f18 size -2147483649 restore rejected")
    check(fs.read_text(lib13) == lib13b && fs.read_text(rem13) == baddn, "f18 size -2147483649 bytes unchanged")
    // 负例：其他整数键共享同一规则（chapter_count 正越界 / created_at 小数）
    let ccpos int = rj13.find("\"chapter_count\":")
    let cchead str = rj13.substr(0, ccpos + 16)
    var cce int = ccpos + 16
    while cce < rj13.len() {
        if rj13.substr(cce, 1) == "," {
            break
        }
        cce = cce + 1
    }
    let badcc2 str = removed_envelope(bid13, cchead + "2147483648" + rj13.substr(cce, rj13.len() - cce))
    fs.write_text(rem13, badcc2)
    check(restore_book(bid13) != "", "f18 chapter_count 2147483648 restore rejected")
    check(fs.read_text(lib13) == lib13b && fs.read_text(rem13) == badcc2, "f18 chapter_count overflow bytes unchanged")
    let capos int = rj13.find("\"created_at\":")
    let cahead str = rj13.substr(0, capos + 13)
    var cae int = capos + 13
    while cae < rj13.len() {
        if rj13.substr(cae, 1) == "}" {
            break
        }
        cae = cae + 1
    }
    let badca2 str = removed_envelope(bid13, cahead + "1.5" + rj13.substr(cae, rj13.len() - cae))
    fs.write_text(rem13, badca2)
    check(restore_book(bid13) != "", "f18 created_at 1.5 restore rejected")
    check(fs.read_text(lib13) == lib13b && fs.read_text(rem13) == badca2, "f18 created_at fraction bytes unchanged")
    // 负例：外层结构坏（缺 record / record 非对象 / book_id 数字）
    fs.write_text(rem13, "{\"book_id\":\"" + bid13 + "\",\"removed_at\":0}")
    check(restore_book(bid13) != "", "f18 envelope missing record rejected")
    check(fs.read_text(lib13) == lib13b, "f18 envelope missing record library unchanged")
    fs.write_text(rem13, "{\"book_id\":\"" + bid13 + "\",\"removed_at\":0,\"record\":\"x\"}")
    check(restore_book(bid13) != "", "f18 envelope record non-object rejected")
    fs.write_text(rem13, "{\"book_id\":5,\"removed_at\":0,\"record\":" + rj13 + "}")
    check(restore_book(bid13) != "", "f18 envelope book_id number rejected")
    // 负例：内层身份换绑（外层对齐请求、record 指向他书）
    let recx str = first_str_replaced(rj13, "book_id", "t06-f18-other")
    fs.write_text(rem13, removed_envelope(bid13, recx))
    check(restore_book(bid13) != "", "f18 inner identity mismatch rejected")
    check(fs.read_text(lib13) == lib13b && fs.read_text(rem13) == removed_envelope(bid13, recx), "f18 identity mismatch bytes unchanged")
    // 正例：未知合法键容忍（信封层 + record 层）
    let rju str = rj13.substr(0, rj13.len() - 1) + ",\"rating\":4.5}"
    fs.write_text(rem13, "{\"book_id\":\"" + bid13 + "\",\"removed_at\":0,\"note\":{\"k\":[1,2]},\"record\":" + rju + "}")
    check(restore_book(bid13) == "", "f18 unknown legal keys restore ok")
    check(book_json(bid13) != "", "f18 unknown legal keys book restored")
    check(fs.read_text(rem13) == "", "f18 unknown legal keys log cleared")
    // 正例：i32 最小/最大边界无损恢复
    check(remove_book(bid13) == "", "f18 re-remove for min boundary")
    fs.write_text(rem13, removed_envelope(bid13, size_replaced(rj13, "-2147483648")))
    check(restore_book(bid13) == "", "f18 i32 minimum restore ok")
    let rmin_raw str = book_json(bid13)
    let rmin = json.parse(rmin_raw)
    let nmin int = rmin.size
    // 注意：源码字面量 -2147483648 受 i32 词法 wrap（2147483648 先 wrap 成
    // -2147483648 再取负）不能用于比较 i32 最小值——用计算式（探针实测）。
    let min_ref int = 0 - 2147483647 - 1
    check(nmin == min_ref, "f18 i32 minimum lossless")
    check(remove_book(bid13) == "", "f18 re-remove for max boundary")
    fs.write_text(rem13, removed_envelope(bid13, size_replaced(rj13, "2147483647")))
    check(restore_book(bid13) == "", "f18 i32 maximum restore ok")
    let rmax_raw str = book_json(bid13)
    let rmax = json.parse(rmax_raw)
    let nmax int = rmax.size
    check(nmax == 2147483647, "f18 i32 maximum lossless")
    check(fs.read_text(rem13) == "", "f18 i32 maximum log cleared")
    let c13 str = json.parse(chapter_json(bid13, 1))
    check(c13.body == "准入正文。", "f18 restored chapters verbatim")

    log("SPEC t06 done fails=" + fails.to_string())
    if fails > 0 {
        hash.file_sha256("__spec_failure__")
    }
}
