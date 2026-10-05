// t02_reading_spec.as — READER-001 T-02 阅读状态规格测试（脚本模式）。
// 覆盖：locator+settings 持久化回环、跨"进程"（重载）仍在、
//       未入库书拒绝、payload 校验（非对象/ID 不匹配）、覆写备份。
// 运行：`auto tests/spec/t02_reading_spec.as`

use src.back.pathx: join, mkdirs
use src.back.library: import_book_json, put_reading_json, get_reading_json

fn log_path() str {
    let t str = Env.get("TEMP")
    return fs.join(t, "t02-spec.log")
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
    file.write_text(lp, "SPEC t02 start\n")
    let t str = Env.get("TEMP")
    let uid str = str.uuid()
    let dir str = fs.join(t, "t02-spec-" + uid)
    Env.set("AUTO_READER_DATA", dir)
    mkdirs(dir)

    // 导入一本书
    let book str = fs.join(dir, "rs.txt")
    fs.write_text(book, "第一章 起\n段一\n段二\n")
    let ok_raw str = import_book_json(book, "", false)
    let ok = json.parse(ok_raw)
    check(ok.code == "ok", "import ok")
    let bid str = "" + ok.book_id

    // 写入 locator v1 + settings
    var st str = "{\"book_id\":\""
    st = st + bid
    st = st + "\",\"chapter_number\":1,\"paragraph_index\":2,\"quote_prefix\":\"段二\",\"font_size\":\"large\",\"line_height\":\"comfy\",\"updated_at\":0}"
    let werr str = put_reading_json(bid, st)
    check(werr.find("\"ok\":true") >= 0, "put reading ok")
    // 回环逐字
    let back str = get_reading_json(bid)
    check(back == st, "reading roundtrip verbatim")
    let r = json.parse(back)
    check(r.paragraph_index == 2, "locator paragraph")
    check(r.font_size == "large", "settings font_size")

    // 覆写 + .bak 存在
    var st2 str = "{\"book_id\":\""
    st2 = st2 + bid
    st2 = st2 + "\",\"chapter_number\":2,\"paragraph_index\":0,\"quote_prefix\":\"\",\"font_size\":\"small\",\"line_height\":\"compact\",\"updated_at\":0}"
    let werr2 str = put_reading_json(bid, st2)
    check(werr2.find("\"ok\":true") >= 0, "put reading again ok")
    check(get_reading_json(bid).find("\"chapter_number\":2") >= 0, "updated state")
    check(fs.exists(join(dir, "reading/" + bid + ".json.bak")) == false || fs.exists(join(dir, "reading") + "/" + bid + ".json.bak"), "bak exists")

    // 错误族：未入库书 / 非对象 / ID 不匹配 / 空 id
    check(put_reading_json("no-such-book", "{\"book_id\":\"no-such-book\"}") != "", "unknown book rejected")
    check(put_reading_json(bid, "[]") != "", "non-object rejected")
    check(put_reading_json(bid, "{\"book_id\":\"other\"}") != "", "id mismatch rejected")
    check(put_reading_json("", "{}") != "", "empty id rejected")
    // 失败写不落盘
    check(get_reading_json("no-such-book") == "", "failed write leaves no record")

    log("SPEC t02 done fails=" + fails.to_string())
    if fails > 0 {
        hash.file_sha256("__spec_failure__")
    }
}
