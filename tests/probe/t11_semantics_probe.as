// t11_semantics_probe.as — Phase 3 修复前提实测（VM 轨脚本模式）。
// 覆盖：json 数组 vs 对象判别（F-11 books:{} 反例）、字段类型检测
// （F-09 数字字符串/bool/null）、字符串相等语义（F-08/F-10 内容锚点）、
// 嵌套结构 raise 行为。
// 运行：auto tests/probe/t11_semantics_probe.as
// 结果：%TEMP%/t11-semantics.log

fn log_path() str {
    let t str = Env.get("TEMP")
    return fs.join(t, "t11-semantics.log")
}

fn log(msg str) {
    var prev str = ""
    if file.exists(log_path()) {
        prev = file.read_text(log_path())
    }
    file.write_text(log_path(), prev + msg + "\n")
}

fn b2s(b bool) str {
    if b {
        return "1"
    }
    return "0"
}

fn main() {
    file.write_text(log_path(), "T11 start\n")

    // Q1 数组 vs 对象判别：len / ""+v / 索引访问 / for-in 行为
    var arr = json.parse("[1,2]")
    var obj = json.parse("{\"a\":1}")
    var earr = json.parse("[]")
    var eobj = json.parse("{}")
    log("Q1 len arr=" + arr.len().to_string() + " obj=" + obj.len().to_string() + " earr=" + earr.len().to_string() + " eobj=" + eobj.len().to_string())
    var s_arr = "unset"
    var s_obj = "unset"
    try {
        s_arr = "" + arr
    } catch {
        s_arr = "raised"
    }
    try {
        s_obj = "" + obj
    } catch {
        s_obj = "raised"
    }
    log("Q1 str arr=[" + s_arr + "] obj=[" + s_obj + "]")
    var q_arr = "unset"
    var q_eobj = "unset"
    try {
        q_arr = ("" + arr).find("[")
        q_eobj = ("" + eobj).find("{")
    } catch {
        q_arr = -999
        q_eobj = -999
    }
    log("Q1 bracket-find arr=" + q_arr.to_string() + " eobj=" + q_eobj.to_string())

    // Q2 字段类型检测：str 字段 vs int 字段 vs bool vs null
    var v = json.parse("{\"s\":\"3\",\"n\":3,\"b\":true,\"z\":null}")
    var vs = "unset"
    try {
        vs = "" + v.s
    } catch {
        vs = "raised"
    }
    log("Q2 str-field as-str=[" + vs + "]")
    var vn = "unset"
    try {
        vn = "" + v.n
    } catch {
        vn = "raised"
    }
    log("Q2 int-field as-str=[" + vn + "]")
    // str 字段做算术：Python str+int raise → 类型判别器候选
    var s_add = "no-raise"
    try {
        s_add = "" + (v.s + 0)
    } catch {
        s_add = "raised"
    }
    log("Q2 str+0=[" + s_add + "]")
    var n_add = "no-raise"
    try {
        n_add = "" + (v.n + 0)
    } catch {
        n_add = "raised"
    }
    log("Q2 int+0=[" + n_add + "]")
    var b_add = "no-raise"
    try {
        b_add = "" + (v.b + 0)
    } catch {
        b_add = "raised"
    }
    log("Q2 bool+0=[" + b_add + "]")
    var z_add = "no-raise"
    try {
        z_add = "" + (v.z + 0)
    } catch {
        z_add = "raised"
    }
    log("Q2 null+0=[" + z_add + "]")

    // Q3 字符串相等（内容锚点的跨轨安全基础）与中文/转义回环
    var esc = json.parse("{\"t\":\"A\\uD83D\\uDE00B\",\"c\":\"中文\\n行\"}")
    var t_val = "unset"
    try {
        t_val = "" + esc.t
    } catch {
        t_val = "raised"
    }
    log("Q3 astral-unescaped len=[" + t_val.len().to_string() + "]")
    var c_val = "unset"
    try {
        c_val = "" + esc.c
    } catch {
        c_val = "raised"
    }
    log("Q3 cjk-newline eq=" + b2s(c_val == "中文\n行") + " len=" + c_val.len().to_string())

    // Q4 json.parse 对合法空白/转义键的容忍（T-12 值提取基线）
    var ws = json.parse("{ \"book_id\" : \"abc\" , \"n\" : 5 }")
    var ws_bid = "unset"
    try {
        ws_bid = "" + ws.book_id
    } catch {
        ws_bid = "raised"
    }
    log("Q4 whitespace-parse bid=[" + ws_bid + "] n=[" + ("" + ws.n) + "]")
    var ek = json.parse("{\"\\u0062ook_id\":\"x\"}")
    var ek_val = "unset"
    try {
        ek_val = "" + ek.book_id
    } catch {
        ek_val = "raised"
    }
    log("Q4 escaped-key parse=[" + ek_val + "]")

    // Q5 重复键解析（已知后值覆盖——重复检测需词法层）
    var dup = json.parse("{\"k\":1,\"k\":2}")
    log("Q5 dup-key last-wins=[" + ("" + dup.k) + "]")

    // Q6 substr/find 对代理对（astral）的 VM 口径
    var emoji str = "A😀B"
    log("Q6 emoji len=" + emoji.len().to_string())
    var e_first = "unset"
    try {
        e_first = emoji.substr(0, 1)
    } catch {
        e_first = "raised"
    }
    log("Q6 emoji substr(0,1)=[" + e_first + "]")
    var cps int = 0
    for c in emoji {
        cps = cps + 1
        if cps > 16 {
            break
        }
    }
    log("Q6 emoji for-in count=" + cps.to_string())

    log("T11 done")
}
