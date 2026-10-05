// t03_importers_spec.as — importers 切分规格（脚本模式，F-07 迁移面）。
// 原 #[test] 5 例因「use 进 VM 测试装置编译失败」框架缺陷迁来此处；断言
// 语义经 JSON 面（parse_book_json，与 parse_book 共享 is_heading/heading_
// title 判定）逐字校验。中文实参直传（t02 规格同形态实测可靠）。
// 运行：auto tests/spec/t03_importers_spec.as

use src.back.importers: parse_book_json, format_of

fn log_path() str {
    let t str = Env.get("TEMP")
    return fs.join(t, "t03-spec.log")
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
    file.write_text(lp, "SPEC t03 start\n")

    // S1 TXT 两章（原 t_txt_chapters）
    let s1 str = parse_book_json("第一章 山月\n山月不知心底事。\n\n第二章 水风\n水风空落眼前花。\n", "txt", "f")
    let w1 = json.parse(s1)
    check(w1.chapters.len() == 2, "txt two chapters")
    check(w1.chapters[0].title == "第一章 山月", "txt ch1 title")
    check(w1.chapters[0].body == "山月不知心底事。", "txt ch1 body verbatim")
    check(w1.chapters[1].number == 2, "txt ch2 number")
    check(w1.chapters[1].title == "第二章 水风", "txt ch2 title")

    // S2 章头变体：第X节 / Chapter N / 楔子（原 t_txt_chapter_variants）
    let s2a = json.parse(parse_book_json("第一节 起\n甲\n第二节 承\n乙\n", "txt", "f"))
    check(s2a.chapters.len() == 2, "jie variant two chapters")
    let s2b = json.parse(parse_book_json("Chapter 1 Dawn\nhello\nChapter 2 Dusk\nworld\n", "txt", "f"))
    check(s2b.chapters.len() == 2, "chapter variant two chapters")
    check(s2b.chapters[1].title == "Chapter 2 Dusk", "chapter ch2 title")
    let s2c = json.parse(parse_book_json("楔子\n旧事\n第一章 起\n正文\n", "txt", "f"))
    check(s2c.chapters.len() == 2, "prologue variant two chapters")
    check(s2c.chapters[0].title == "楔子", "prologue ch1 title")

    // S3 章头前内容 → 开篇章；无章头 → 单章 fallback 标题（原
    // t_txt_prelude_and_no_heading）
    let s3a = json.parse(parse_book_json("引言\n旧事\n\n第一章 起\n正文\n", "txt", "f"))
    check(s3a.chapters.len() == 2, "prelude two chapters")
    check(s3a.chapters[0].title == "开篇", "prelude chapter titled 开篇")
    check(s3a.chapters[0].body == "引言\n旧事", "prelude body verbatim")
    let s3b = json.parse(parse_book_json("只是普通文本\n没有章节标记\n", "txt", "书名"))
    check(s3b.chapters.len() == 1, "no-heading single chapter")
    check(s3b.chapters[0].title == "书名", "fallback title")
    check(s3b.chapters[0].body.find("没有章节标记") >= 0, "no-heading body intact")

    // S4 Markdown：#/## 开章、"###" 留正文（原 t_md_chapters）
    let s4a = json.parse(parse_book_json("# 上卷\n引言正文\n## 小节\n细节\n# 下卷\n尾声\n", "md", "f"))
    check(s4a.chapters.len() == 3, "md three chapters")
    check(s4a.chapters[0].title == "上卷", "md ch1 title")
    check(s4a.chapters[1].title == "小节", "md ch2 title")
    check(s4a.chapters[2].title == "下卷", "md ch3 title")
    let s4b = json.parse(parse_book_json("# 章\nintro\n### 深标题\nbody\n", "md", "f"))
    check(s4b.chapters.len() == 1, "md deep heading stays in body")
    check(s4b.chapters[0].body.find("### 深标题") >= 0, "md ### body verbatim")

    // S5 format_of（原 t_format_of）
    check(format_of("a/b.md") == "md", "format md")
    check(format_of("b.MD") == "md", "format MD case-insensitive")
    check(format_of("c.txt") == "txt", "format txt")
    check(format_of("d") == "txt", "format default txt")

    log("SPEC t03 done fails=" + fails.to_string())
    if fails > 0 {
        hash.file_sha256("__spec_failure__")
    }
}
