// t05_semantics_probe.as — Phase 2 修复前提实测（VM 轨脚本模式），第2轮。
// 规避：bool/float 不做 str 拼接（第1轮实测 bool→"-2147483648"、float 拼接 raise）。
// 运行：auto tests/probe/t05_semantics_probe.as
// 结果：%TEMP%/t05-semantics.log

fn log_path() str {
    return fs.join(Env.get("TEMP"), "t05-semantics.log")
}

fn log(msg str) {
    var prev str = ""
    if file.exists(log_path()) {
        prev = file.read_text(log_path())
    }
    file.write_text(log_path(), prev + msg + "\n")
}

// bool → "1"/"0"（VM bool.to_string 不可靠的规避）
fn b2s(b bool) str {
    if b {
        return "1"
    }
    return "0"
}

fn main() {
    file.write_text(log_path(), "T05 round2\n")
    let t str = Env.get("TEMP")
    let dir str = fs.join(t, "t05-probe-" + str.uuid())
    fs.mkdir_all(dir)

    // P5 整数回环判别：s.to_int().to_string() == s
    let r12 str = "12".to_int().to_string()
    log("P5 12 -> [" + r12 + "] eq=" + b2s(r12 == "12"))
    let rabc str = "abc".to_int().to_string()
    log("P5 abc -> [" + rabc + "] eq=" + b2s(rabc == "abc"))
    let r15 str = "1.5".to_int().to_string()
    log("P5 1.5 -> [" + r15 + "] eq=" + b2s(r15 == "1.5"))
    let rneg str = "-1".to_int().to_string()
    log("P5 -1 -> [" + rneg + "] eq=" + b2s(rneg == "-1"))
    let rmpty str = "".to_int().to_string()
    log("P5 empty -> [" + rmpty + "]")

    // P6b null 字段拼接是否 raise
    var p6 = json.parse("{\"nl\":null,\"n\":12}")
    var nl_raised bool = false
    var nl_val str = ""
    try {
        nl_val = "" + p6.nl
    } catch {
        nl_raised = true
    }
    log("P6b null-concat raised=" + b2s(nl_raised) + " val=[" + nl_val + "]")
    log("P6b int-concat val=[" + ("" + p6.n) + "]")

    // P7 write_text 到目录路径的返回码
    let subdir str = fs.join(dir, "bakdir")
    fs.mkdir_all(subdir)
    var p7_rc int = -999
    var p7_raised bool = false
    try {
        p7_rc = fs.write_text(subdir, "x")
    } catch {
        p7_raised = true
    }
    log("P7 write-to-dir rc=" + p7_rc.to_string() + " raised=" + b2s(p7_raised))

    // P8 read_text 目录路径行为
    var p8_val str = "unset"
    var p8_raised bool = false
    try {
        p8_val = fs.read_text(subdir)
    } catch {
        p8_raised = true
    }
    log("P8 read-dir raised=" + b2s(p8_raised) + " val=[" + p8_val + "]")

    // P9 fs.exists 对目录
    log("P9 exists-dir=" + b2s(fs.exists(subdir)))
    log("P9 is-dir=" + b2s(fs.is_dir(subdir)))

    // P10 write 正常返回码 + 读回
    let fp str = fs.join(dir, "ok.txt")
    let wrc int = fs.write_text(fp, "hello")
    let back str = fs.read_text(fp)
    log("P10 write rc=" + wrc.to_string() + " readback=[" + back + "]")

    // P11 json.parse 键重复
    var p11 = json.parse("{\"k\":1,\"k\":2}")
    log("P11 dup-key val=[" + ("" + p11.k) + "]")

    // P12 嵌套键干扰下的顶层严格取值
    var p12 = json.parse("{\"book_id\":\"wrong\",\"note\":\"target\"}")
    log("P12 top-book_id=[" + ("" + p12.book_id) + "]")

    // P13 trim/find 基线
    log("P13 find-sub=[" + ("abcjson".find("json")).to_string() + "]")

    // P14 字符串 == 对含转义内容
    var p14 = json.parse("{\"s\":\"line1\\nline2\"}")
    log("P14 escape-roundtrip eq=" + b2s(("" + p14.s) == "line1\nline2"))

    // P15 json.parse 数组元素为对象时取字段（toc 形状）
    var p15 = json.parse("{\"books\":[{\"n\":1},{\"n\":2}]}")
    var cnt int = 0
    for b in p15.books {
        cnt = cnt + ("" + b.n).to_int()
    }
    log("P15 arr-sum=[" + cnt.to_string() + "]")

    log("T05 round2 done")
}
