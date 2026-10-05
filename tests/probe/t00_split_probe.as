// t00_split_probe.as — 章节切分路径的 VM 运行时探针：split/starts_with/trim。
fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-split.log")
}

fn log(msg str) {
    var prev str = ""
    if file.exists(crumb_path()) {
        prev = file.read_text(crumb_path())
    }
    file.write_text(crumb_path(), prev + msg + "\n")
}

fn main() {
    log("SPLIT start")
    // S1 str.split 基本形态
    let lines = "第一行\n第二行\n\n第三行".split("\n")
    log("NOTE split count=" + lines.len().to_string() + " first=<" + ("" + lines[0]) + ">")
    // S2 starts_with 中文前缀
    if "第一章 山月".starts_with("第一章") {
        log("PASS starts_with utf8")
    } else {
        log("FAIL starts_with utf8")
    }
    // S3 trim
    let t str = "  第一章  ".trim()
    if t == "第一章" {
        log("PASS trim")
    } else {
        log("FAIL trim got=<" + t + ">")
    }
    // S4 大文本 split 性能（约 5MB / 10 万行）
    let para str = "山月不知心底事，水风空落眼前花。\n"
    var big str = para
    var i int = 0
    while i < 16 {
        big = big + big
        i = i + 1
    }
    let parts = big.split("\n")
    log("NOTE big-split bytes=" + big.len().to_string() + " lines=" + parts.len().to_string())
    // S5 空串 split 行为
    let e = "".split("\n")
    log("NOTE empty-split len=" + e.len().to_string())
    // S6 List 字符串 join？
    log("SPLIT done")
}
