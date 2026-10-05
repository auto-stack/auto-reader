// t05_collision_spec.as — READER-001 Phase 2 T-05 碰撞/隔离规格（脚本模式）。
// 修复对象 F-02：等长、每行前 64 字符相同而行尾不同的两份文件 ph1 必同值
// （确定性碰撞）——去重必须逐字核对内容，force 不得串换正文，旧库碰撞
// 记录不被改写或静默合并。
// 脚本纪律：脚本→模块调用的多字节字符串实参会被剥离（T-00 报告缺陷 8）
// ——本规格内容用 ASCII；中文内容的逐字行为由 t01 规格与 HTTP 驱动覆盖。
// 运行：auto tests/spec/t05_collision_spec.as
// 结果：%TEMP%/t05-spec.log；任何 FAIL 以 RuntimeError 非零退出。

use src.back.library: books_json, book_json, chapter_json, import_book_json
use src.back.pathx: join, mkdirs

fn log_path() str {
    let t str = Env.get("TEMP")
    return fs.join(t, "t05-spec.log")
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
    file.write_text(lp, "SPEC t05 start\n")
    let t str = Env.get("TEMP")
    let uid str = str.uuid()
    let dir str = fs.join(t, "t05-spec-" + uid)
    Env.set("AUTO_READER_DATA", dir)
    mkdirs(dir)

    // S1 构造确定性碰撞对：同字节数、每行前 64 字符相同、行尾不同。
    // ph1 折叠每行前 64 字符 + 行长 + 总字节数——三者均同 → 必同指纹。
    let prefix str = "0123456789012345678901234567890123456789012345678901234567890123"
    let ta str = prefix + "alpha\n"
    let tb str = prefix + "omega\n"
    let fa str = join(dir, "collide-a.txt")
    let fb str = join(dir, "collide-b.txt")
    fs.write_text(fa, ta)
    fs.write_text(fb, tb)
    let oa = json.parse(import_book_json(fa, "t05", false))
    check(oa.code == "ok", "collision pair: first import ok")
    let ob = json.parse(import_book_json(fb, "t05", false))
    // F-02 主断言：内容不同 → 不得判重，必须导入成功
    check(ob.code == "ok", "same-ph1 different-content NOT deduplicated")
    let bid_a str = "" + oa.book_id
    let bid_b str = "" + ob.book_id
    check(bid_b != bid_a, "collision pair distinct ids")
    // force 后正文不串换：两本书各自读到自己的原文
    let ca str = json.parse(chapter_json(bid_a, 1))
    check(ca.body == ta.trim(), "book A body verbatim (no swap)")
    let cb str = json.parse(chapter_json(bid_b, 1))
    check(cb.body == tb.trim(), "book B body verbatim (no swap)")

    // S2 force 再导入 B：内容核对命中 B 自己 → 允许独立副本，正文仍为 B
    let of_b = json.parse(import_book_json(fb, "t05", true))
    check(of_b.code == "ok", "force re-import of B ok")
    let bid_b2 str = "" + of_b.book_id
    check(bid_b2 != bid_b, "force creates distinct archive id")
    let cb2 str = json.parse(chapter_json(bid_b2, 1))
    check(cb2.body == tb.trim(), "forced archive body verbatim B")

    // S3 真重复（内容逐字相同）行为保持：duplicate 提示 + existing_id
    let od = json.parse(import_book_json(fa, "", false))
    check(od.code == "duplicate", "true duplicate still detected")
    check(od.existing_id == bid_a, "duplicate existing_id points to A")

    // S4 资产隔离：两本碰撞书的受管路径不同且内容各自正确
    let ra_raw str = book_json(bid_a)
    let ra = json.parse(ra_raw)
    let rb_raw str = book_json(bid_b)
    let rb = json.parse(rb_raw)
    let pa str = "" + ra.managed_path
    let pb str = "" + rb.managed_path
    check(pa != pb, "colliding books isolated asset paths")
    check(fs.read_text(pa) == ta, "asset A content intact")
    check(fs.read_text(pb) == tb, "asset B content intact")

    // S5 旧库兼容：模拟 ph1 时代碰撞误并记录（记录指向含他文的主槽位），
    // 再导入真实内容 → 不得判重、不得改写旧记录指向的资产（不改旧 ID、
    // 不静默合并），新内容落独立槽位。
    let hdir str = ""
    // 从 A 的记录取指纹构造旧形目录：直接复用 A 的 managed 目录布局
    // （A 的资产在主槽位；向其中写入碰撞内容模拟历史误并）
    let legacy_idx str = books_json()
    check(legacy_idx.find("\"version\":1") >= 0, "index readable before legacy drill")
    // 以 B 的内容覆盖 A 的主槽位资产（模拟历史碰撞串文后的库）
    // ——先保存 A 的原字节，演练后恢复
    let saved_a str = fs.read_text(pa)
    fs.write_text(pa, tb)
    // 此时 A 记录核对失败（内容≠A 源），再导入 A 源 → 不得判重
    let oc = json.parse(import_book_json(fa, "", false))
    check(oc.code == "ok", "corrode-then-reimport A not deduplicated")
    let bid_a2 str = "" + oc.book_id
    check(bid_a2 != bid_a, "repaired A gets new record id")
    let ra2_raw str = book_json(bid_a2)
    let ra2 = json.parse(ra2_raw)
    let pa2 str = "" + ra2.managed_path
    check(pa2 != pa, "repaired A isolated from corroded asset")
    check(fs.read_text(pa2) == ta, "repaired A asset verbatim")
    // 旧记录原样保留（不静默合并/改写）；其资产字节未被本次导入触碰
    check(book_json(bid_a) == ra_raw, "legacy record untouched")
    check(fs.read_text(pa) == tb, "corroded legacy asset untouched by repair")
    // 恢复演练现场（A 主槽位还原为 A 内容）
    fs.write_text(pa, saved_a)
    let ca3 str = json.parse(chapter_json(bid_a, 1))
    check(ca3.body == ta.trim(), "legacy A readable again after restore")

    // S6 跨扩展名：同内容 .md 与 .txt → 逐字同文判重（语义保持）
    let fm str = join(dir, "twin.md")
    fs.write_text(fm, "第一章 起\n同文。\n")
    let ft str = join(dir, "twin.txt")
    fs.write_text(ft, "第一章 起\n同文。\n")
    let om = json.parse(import_book_json(fm, "", false))
    check(om.code == "ok", "md twin import ok")
    let ot = json.parse(import_book_json(ft, "", false))
    // 内容逐字相同 → 判重（与扩展名无关；格式差异不是独立档案依据）
    check(ot.code == "duplicate", "identical content across extensions deduplicated")

    log("SPEC t05 done fails=" + fails.to_string())
    if fails > 0 {
        hash.file_sha256("__spec_failure__")
    }
}
