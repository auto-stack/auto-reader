// t00_cap_probe.as — 验证大写 File.* 与 str.uuid/Env.get 在 VM 轨的运行时可用性。
fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-cap.log")
}

fn log(msg str) {
    var prev str = ""
    if file.exists(crumb_path()) {
        prev = file.read_text(crumb_path())
    }
    file.write_text(crumb_path(), prev + msg + "\n")
}

fn main() {
    log("CAP start")
    let base str = fs.join(Env.get("TEMP"), "t00-cap-probe")
    fs.mkdir_all(base)
    let p str = fs.join(base, "c.txt")
    file.write_text(p, "山月不知心底事")
    // C1 大写 File.read_text_range
    let rng str = File.read_text_range(p, 0, 64)
    let env = json.parse(rng)
    if env.total == 21 {
        log("PASS File.read_text_range vm total=21")
    } else {
        log("FAIL File.read_text_range vm env=" + rng)
    }
    // C2 str.uuid
    let u str = str.uuid()
    if u.len() >= 32 {
        log("PASS str.uuid vm len=" + u.len().to_string())
    } else {
        log("FAIL str.uuid vm got=" + u)
    }
    // C3 Env.get
    let t str = Env.get("TEMP")
    if t != "" {
        log("PASS Env.get vm")
    } else {
        log("FAIL Env.get vm empty")
    }
    // C4 for-in 遍历 str（字符迭代语义——章节切分依赖）
    var count int = 0
    for ch in "山月ab" {
        count = count + 1
        if count > 10 {
            break
        }
    }
    log("NOTE str-iteration count=" + count.to_string() + " (5=char-wise, 7=byte-wise)")
    // C5 substr 方法形态
    let s str = "山月不知心底事".substr(0, 2)
    if s == "山月" {
        log("PASS substr char-indexed")
    } else {
        log("NOTE substr got=" + s)
    }
    log("CAP done")
}
