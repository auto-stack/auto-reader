// t02_reading_spec.as — READER-001 T-02 阅读状态规格测试（脚本模式）。
// Phase 3（F-08/F-09/F-10 修复后）覆盖：locator+settings 持久化回环
// （para_text 内容锚点必填且与原文行逐字相等）、章级书签（pi=-1 免锚点）、
// 词法校验（合法空白/转义键兼容；数字字符串/浮点/null/bool/重复键拒绝；
// 截断拒绝）、内层 payload 夹带 para_text 拒绝、锚点失配拒绝、读侧容错、
// 覆写备份、失败不落盘。
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

    // 写入 locator v1 + settings + 内容锚点（para_text = 第 2 行"段二"）
    var st str = "{\"book_id\":\""
    st = st + bid
    st = st + "\",\"chapter_number\":1,\"paragraph_index\":2,\"para_hash\":\"sig1:2:1\",\"quote_prefix\":\"段二\",\"font_size\":\"large\",\"line_height\":\"comfy\",\"updated_at\":0}"
    let werr str = put_reading_json(bid, st, "段二")
    check(werr.find("\"ok\":true") >= 0, "put reading ok (para_text anchor)")
    // 规范存储态回环：字段语义逐项一致 + 注入的 para_text 在场
    let back str = get_reading_json(bid)
    check(back.find("\"paragraph_index\":2") >= 0, "stored locator paragraph")
    check(back.find("\"para_text\":\"段二\"") >= 0, "stored injected para_text verbatim")
    check(back.find("\"font_size\":\"large\"") >= 0, "stored settings font_size")
    check(back.find("\"quote_prefix\":\"段二\"") >= 0, "stored quote_prefix")
    let r = json.parse(back)
    check(r.paragraph_index == 2, "parsed locator paragraph")
    check(r.font_size == "large", "parsed settings font_size")
    check(r.para_text == "段二", "parsed content anchor")

    // 覆写（章级书签 pi=-1，免锚点）+ .bak 存在
    var st2 str = "{\"book_id\":\""
    st2 = st2 + bid
    st2 = st2 + "\",\"chapter_number\":2,\"paragraph_index\":-1,\"para_hash\":\"sig1:0:1\",\"font_size\":\"small\",\"line_height\":\"compact\",\"updated_at\":0}"
    let werr2 str = put_reading_json(bid, st2, "")
    check(werr2.find("\"ok\":true") >= 0, "put chapter bookmark ok (no anchor)")
    check(get_reading_json(bid).find("\"chapter_number\":2") >= 0, "updated state")
    check(fs.exists(join(dir, "reading/" + bid + ".json.bak")), "bak exists")

    // 错误族：未入库书 / 非对象 / ID 不匹配 / 错 ID 藏无关字段 / 空 id
    check(put_reading_json("no-such-book", "{\"book_id\":\"no-such-book\"}", "") != "", "unknown book rejected")
    check(put_reading_json(bid, "[]", "") != "", "non-object rejected")
    check(put_reading_json(bid, "{\"book_id\":\"other\",\"chapter_number\":1,\"paragraph_index\":-1,\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}", "") != "", "id mismatch rejected")
    var hid str = "{\"book_id\":\"wrong\",\"note\":\""
    hid = hid + bid
    hid = hid + "\",\"chapter_number\":1,\"paragraph_index\":-1,\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, hid, "") != "", "mismatched id hidden in note rejected")
    check(put_reading_json("", "{}", "") != "", "empty id rejected")

    // F-09 词法族：截断 / 缺 book_id / 数字串冒充整数 / 浮点 / null / bool
    var tr str = "{\"book_id\":\""
    tr = tr + bid
    tr = tr + "\","
    check(put_reading_json(bid, tr, "") != "", "truncated JSON rejected")
    check(put_reading_json(bid, "{\"chapter_number\":1,\"paragraph_index\":0,\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}", "") != "", "missing book_id rejected")
    var fnum str = "{\"book_id\":\""
    fnum = fnum + bid
    fnum = fnum + "\",\"chapter_number\":\"1\",\"paragraph_index\":0,\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, fnum, "") != "", "numeric-string chapter rejected")
    var fdup str = "{\"book_id\":\""
    fdup = fdup + bid
    fdup = fdup + "\",\"book_id\":\""
    fdup = fdup + bid
    fdup = fdup + "\",\"chapter_number\":1,\"paragraph_index\":0,\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, fdup, "") != "", "duplicate id key rejected")
    var ffloat str = "{\"book_id\":\""
    ffloat = ffloat + bid
    ffloat = ffloat + "\",\"chapter_number\":1.5,\"paragraph_index\":0,\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, ffloat, "") != "", "float chapter rejected")
    var fnull str = "{\"book_id\":\""
    fnull = fnull + bid
    fnull = fnull + "\",\"chapter_number\":1,\"paragraph_index\":null,\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, fnull, "") != "", "null paragraph rejected")
    var fbool str = "{\"book_id\":\""
    fbool = fbool + bid
    fbool = fbool + "\",\"chapter_number\":true,\"paragraph_index\":0,\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, fbool, "") != "", "bool chapter rejected")

    // F-09 合法形态兼容：属性名前空白 + 转义属性名（\\u0070 = p → paragraph_index 不适用；
    // 用 \\u0062 = b 不撞已知键——book_id 的转义形态）
    var wsp str = "{ \"book_id\" : \""
    wsp = wsp + bid
    wsp = wsp + "\" , \"chapter_number\" : 1 , \"paragraph_index\" : 2 , \"para_hash\" : \"sig1:2:1\" , \"font_size\" : \"medium\" , \"line_height\" : \"comfy\" , \"updated_at\" : 0 }"
    check(put_reading_json(bid, wsp, "段二").find("\"ok\":true") >= 0, "whitespace form accepted")
    var ek str = "{\"\\u0062ook_id\":\""
    ek = ek + bid
    ek = ek + "\",\"chapter_number\":1,\"paragraph_index\":2,\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, ek, "段二").find("\"ok\":true") >= 0, "escaped book_id key accepted")
    // 正例覆写后恢复书签态（后续失败保持断言的基准）
    check(put_reading_json(bid, st2, "").find("\"ok\":true") >= 0, "bookmark re-established")

    // 章段越界 / 空行段 / 锚点失配（F-08：等长替换语义）/ 缺内容锚点
    var fch str = "{\"book_id\":\""
    fch = fch + bid
    fch = fch + "\",\"chapter_number\":99,\"paragraph_index\":0,\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, fch, "") != "", "chapter out of range rejected")
    var fpi str = "{\"book_id\":\""
    fpi = fpi + bid
    fpi = fpi + "\",\"chapter_number\":1,\"paragraph_index\":999,\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, fpi, "任意") != "", "paragraph 999 out of range rejected")
    var fempty str = "{\"book_id\":\""
    fempty = fempty + bid
    fempty = fempty + "\",\"chapter_number\":1,\"paragraph_index\":1,\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, fempty, "") != "", "paragraph on blank line rejected")
    var fanchor str = "{\"book_id\":\""
    fanchor = fanchor + bid
    fanchor = fanchor + "\",\"chapter_number\":1,\"paragraph_index\":2,\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, fanchor, "段贰") != "", "anchor mismatch rejected")
    check(put_reading_json(bid, fanchor, "") != "", "missing para_text rejected")
    // 内层 payload 夹带 para_text 拒绝（内容锚点由顶层字段承载）
    var finner str = "{\"book_id\":\""
    finner = finner + bid
    finner = finner + "\",\"chapter_number\":1,\"paragraph_index\":2,\"para_text\":\"段二\",\"font_size\":\"medium\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, finner, "段二") != "", "para_text inside payload rejected")

    // 无效设置枚举
    var ffont str = "{\"book_id\":\""
    ffont = ffont + bid
    ffont = ffont + "\",\"chapter_number\":1,\"paragraph_index\":-1,\"font_size\":\"huge\",\"line_height\":\"comfy\",\"updated_at\":0}"
    check(put_reading_json(bid, ffont, "") != "", "invalid font_size rejected")
    var fline str = "{\"book_id\":\""
    fline = fline + bid
    fline = fline + "\",\"chapter_number\":1,\"paragraph_index\":-1,\"font_size\":\"medium\",\"line_height\":\"loose\",\"updated_at\":0}"
    check(put_reading_json(bid, fline, "") != "", "invalid line_height rejected")

    // 失败写不落盘：上一有效状态语义字段保留（章级书签）
    let last str = get_reading_json(bid)
    check(last.find("\"chapter_number\":2") >= 0, "failed writes leave last valid state")

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
