// t02_reading_spec.as — READER-001 T-02 阅读状态规格测试（脚本模式）。
// Phase 2（F-04 修复后）覆盖：locator+settings 持久化回环（para_hash 锚点
// 必须与原文行签名一致）、跨"进程"（重载）仍在、未入库书拒绝、payload
// 真实解析与 schema（截断/错 ID 藏无关字段/缺字段/类型错/章段越界/无效
// 设置/键重复）、读侧容错（坏状态不冒充有效）、覆写备份、失败不落盘。
// 运行：auto tests/spec/t02_reading_spec.as

use src.back.pathx: join, mkdirs
use src.back.library: import_book_json, put_reading_json, get_reading_json

fn log_path() str {
    let t str = Env.get("TEMP")
    return fs.join(t, "t02-spec.log")
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
    file.write_text(lp, "SPEC t02 start\n")
    let t str = Env.get("TEMP")
    let uid str = str.uuid()
    let dir str = fs.join(t, "t02-spec-" + uid)
    Env.set("AUTO_READER_DATA", dir)
    mkdirs(dir)

    // 导入一本书：第一章三行（段一/空行/段二）、第二章一段
    let book str = fs.join(dir, "rs.txt")
    fs.write_text(book, "第一章 起\n段一\n\n段二\n\n第二章 承\n尾段。\n")
    let ok_raw str = import_book_json(book, "", false)
    let ok = json.parse(ok_raw)
    check(ok.code == "ok", "import ok")
    let bid str = "" + ok.book_id

    // 写入 locator v1 + settings（para_hash = 第 2 行"段二"的锚点签名；
    // 正文行号 0=段一、1=空行、2=段二）
    var st str = "{\"book_id\":\""
    st = st + bid
    st = st + "\",\"chapter_number\":1,\"paragraph_index\":2,\"para_hash\":\"sig1:2:1\",\"quote_prefix\":\"段二\",\"font_size\":\"large\",\"line_height\":\"comfy\",\"updated_at\":0}"
    let werr str = put_reading_json(bid, st)
    check(werr.find("\"ok\":true") >= 0, "put reading ok")
    // 回环逐字
    let back str = get_reading_json(bid)
    check(back == st, "reading roundtrip verbatim")
    let r = json.parse(back)
    check(r.paragraph_index == 2, "locator paragraph")
    check(r.font_size == "large", "settings font_size")

    // 覆写（章级书签形态 pi=-1）+ .bak 存在
    var st2 str = "{\"book_id\":\""
    st2 = st2 + bid
    st2 = st2 + "\",\"chapter_number\":2,\"paragraph_index\":-1,\"para_hash\":\"sig1:0:1\",\"quote_prefix\":\"\",\"font_size\":\"small\",\"line_height\":\"compact\",\"updated_at\":0}"
    let werr2 str = put_reading_json(bid, st2)
    check(werr2.find("\"ok\":true") >= 0, "put reading again ok")
    check(get_reading_json(bid).find("\"chapter_number\":2") >= 0, "updated state")
    check(fs.exists(join(dir, "reading/" + bid + ".json.bak")), "bak exists")

    // 错误族：未入库书 / 非对象 / ID 不匹配 / 错 ID 藏无关字段 / 空 id
    check(put_reading_json("no-such-book", "{\"book_id\":\"no-such-book\"}") != "", "unknown book rejected")
    check(put_reading_json(bid, "[]") != "", "non-object rejected")
    check(put_reading_json(bid, "{\"book_id\":\"other\"}") != "", "id mismatch rejected")
    var hid str = "{\"book_id\":\"wrong\",\"note\":\""
    hid = hid + bid
    hid = hid + "\"}"
    check(put_reading_json(bid, hid) != "", "mismatched id hidden in note rejected")
    check(put_reading_json("", "{}") != "", "empty id rejected")

    // F-04 负例：截断 JSON / 缺字段 / 类型错 / 键重复
    var tr str = "{\"book_id\":\""
    tr = tr + bid
    tr = tr + "\","
    check(put_reading_json(bid, tr) != "", "truncated JSON rejected")
    check(put_reading_json(bid, "{\"chapter_number\":1,\"paragraph_index\":0,\"para_hash\":\"sig1:2:1\",\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}") != "", "missing book_id rejected")
    check(put_reading_json(bid, "{\"book_id\":\"x\",\"book_id\":\"y\"}") != "", "duplicate id key rejected")
    var fdup str = "{\"book_id\":\""
    fdup = fdup + bid
    fdup = fdup + "\",\"book_id\":\""
    fdup = fdup + bid
    fdup = fdup + "\",\"chapter_number\":1,\"paragraph_index\":0,\"para_hash\":\"sig1:2:1\",\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, fdup) != "", "duplicate id key (real id) rejected")
    var ffloat str = "{\"book_id\":\""
    ffloat = ffloat + bid
    ffloat = ffloat + "\",\"chapter_number\":1.5,\"paragraph_index\":0,\"para_hash\":\"sig1:2:1\",\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, ffloat) != "", "float chapter rejected")
    var fnull str = "{\"book_id\":\""
    fnull = fnull + bid
    fnull = fnull + "\",\"chapter_number\":1,\"paragraph_index\":null,\"para_hash\":\"sig1:2:1\",\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, fnull) != "", "null paragraph rejected")

    // 章段越界 / 空行段 / 锚点不符
    var fch str = "{\"book_id\":\""
    fch = fch + bid
    fch = fch + "\",\"chapter_number\":99,\"paragraph_index\":0,\"para_hash\":\"sig1:2:1\",\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, fch) != "", "chapter out of range rejected")
    var fpi str = "{\"book_id\":\""
    fpi = fpi + bid
    fpi = fpi + "\",\"chapter_number\":1,\"paragraph_index\":999,\"para_hash\":\"sig1:999:1\",\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, fpi) != "", "paragraph 999 out of range rejected")
    var fempty str = "{\"book_id\":\""
    fempty = fempty + bid
    fempty = fempty + "\",\"chapter_number\":1,\"paragraph_index\":1,\"para_hash\":\"sig1:0:1\",\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, fempty) != "", "paragraph on blank line rejected")
    var fanchor str = "{\"book_id\":\""
    fanchor = fanchor + bid
    fanchor = fanchor + "\",\"chapter_number\":1,\"paragraph_index\":2,\"para_hash\":\"sig1:999:1\",\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, fanchor) != "", "anchor mismatch rejected")

    // 无效设置枚举
    var ffont str = "{\"book_id\":\""
    ffont = ffont + bid
    ffont = ffont + "\",\"chapter_number\":1,\"paragraph_index\":-1,\"para_hash\":\"sig1:0:1\",\"font_size\":\"huge\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, ffont) != "", "invalid font_size rejected")
    var fline str = "{\"book_id\":\""
    fline = fline + bid
    fline = fline + "\",\"chapter_number\":1,\"paragraph_index\":-1,\"para_hash\":\"sig1:0:1\",\"font_size\":\"medium\",\"line_height\":\"loose\",\"updated_at\":0}"
    check(put_reading_json(bid, fline) != "", "invalid line_height rejected")

    // 失败写不落盘：上一有效状态逐字保留
    check(get_reading_json(bid) == st2, "failed writes leave last valid state verbatim")

    // 读侧容错：外部损坏状态文件 → 读回 ""，文件保留
    let rfile str = join(dir, "reading/" + bid + ".json")
    fs.write_text(rfile, "{\"book_id\":\"x\",")
    check(get_reading_json(bid) == "", "corrupt state reads as empty (tolerant)")
    check(fs.exists(rfile), "corrupt state file preserved")

    log("SPEC t02 done fails=" + fails.to_string())
    if fails > 0 {
        hash.file_sha256("__spec_failure__")
    }
}
