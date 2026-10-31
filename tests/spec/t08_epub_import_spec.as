// t08_epub_import_spec.as — READER-003 T-01 EPUB 导入事务规格（脚本模式）。
// 前置：python 生成 fixture %TEMP%/plan897/book1.epub（见 tests/fixtures 说明，
// 生成器 tests/spec/plan897_make_epub.py 提交）；隔离数据目录（AUTO_READER_DATA
// 由运行环境注入；本探针只读回自身导入结果，不清他人书库）。
// 运行：auto tests/spec/t08_epub_import_spec.as
// 判据双门：日志 %TEMP%/t08-spec.log PASS/FAIL 计数 + 进程退出码。

use src.back.epub: epub_import_json, epub_toc_json
use src.back.library: toc_json, chapter_json, book_json

fn log_path() str {
    return fs.join(Env.get("TEMP"), "t08-spec.log")
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
    file.delete(log_path())
    log("T08 start")
    let base str = fs.join(Env.get("TEMP"), "plan897")
    let ep str = fs.join(base, "book1.epub")
    // 夹具就位
    check(file.exists(ep), "fixture exists")

    // I-01 首次导入：code ok、book_id 非空
    let r1 str = epub_import_json(ep, "测试作者", false)
    log(r1)
    check(r1.find("\"code\":\"ok\"") >= 0, "i01 first import ok")
    check(r1.find("\"book_id\":\"\"") < 0, "i01 book_id non-empty")

    // I-02 重复导入（同 sha256）→ duplicate + existing_id
    let r2 str = epub_import_json(ep, "", false)
    check(r2.find("\"code\":\"duplicate\"") >= 0, "i02 duplicate detected")
    check(r2.find("\"existing_id\":\"\"") < 0, "i02 existing_id present")

    // I-03 force 导入独立副本 → ok
    let r3 str = epub_import_json(ep, "", true)
    check(r3.find("\"code\":\"ok\"") >= 0, "i03 force import ok")

    // T-02：目录与章读取
    var bid str = ""
    try {
        let v = json.parse(r1)
        bid = "" + v.book_id
    } catch {
        bid = ""
    }
    check(bid != "", "t02 book_id parsed")
    let toc str = toc_json(bid)
    log("TOC-RAW")
    log(toc)
    log("TOC-DIRECT")
    log(epub_toc_json("|ch1.xhtml|ch2.xhtml|", "|ch1.xhtml`第一章 山月|ch2.xhtml`第二章 心底事|"))
    let meta str = book_json(bid)
    check(toc.find("\"number\":1") >= 0, "t02 toc entry 1")
    check(toc.find("\"number\":2") >= 0, "t02 toc entry 2")
    check(toc.find("第一章 山月") >= 0, "t02 toc label c1")
    let c1 str = chapter_json(bid, 1)
    check(c1.find("山月不知心底事。") >= 0, "t02 ch1 text")
    check(c1.find("img:OEBPS/images/cover.png") >= 0, "t02 ch1 img marker")
    check(c1.find("水调歌头，明月几时有。") >= 0, "t02 ch1 para2")
    let c2 str = chapter_json(bid, 2)
    check(c2.find("第二 chapter 内容。") >= 0, "t02 ch2 text")
    // 缓存命中：二读一致
    let c1b str = chapter_json(bid, 1)
    check(c1b.find("山月不知心底事。") >= 0, "t02 ch1 cached text")
    check(c1b.find("\"images\":[") >= 0, "t02 ch1 cached has images")
    // 越界章
    let c9 str = chapter_json(bid, 9)
    check(c9.find("章节不存在") >= 0, "t02 ch9 out of range")
    // TXT 旧路不回归
    let txt str = fs.join(base, "txtbook.txt")
    file.write_text(txt, "第一章 A
段落甲。

第二章 B
段落乙。")
    let tr str = epub_import_json(txt, "", false)
    check(tr.find("\"code\":\"epub_invalid\"") >= 0, "t02 txt not epub-dispatched (epub fn rejects)")

    // I-04 非 EPUB（ZIP 无 container）→ epub_invalid
    let bad str = fs.join(base, "zipfx.zip")
    if file.exists(bad) {
        let r4 str = epub_import_json(bad, "", false)
        check(r4.find("\"code\":\"epub_invalid\"") >= 0, "i04 non-epub rejected")
    }

    // I-05 缺文件 → epub_invalid（路径层）
    let r5 str = epub_import_json(fs.join(base, "no-such.epub"), "", false)
    check(r5.find("\"code\":\"epub_invalid\"") >= 0, "i05 missing file rejected")

    log("T08 done")
    if fails > 0 {
        log("RESULT fails>0")
        let boom List<int> = List<int>.new([])
        log(boom[9999].to_string())
        return
    }
    log("RESULT all-pass")
}
