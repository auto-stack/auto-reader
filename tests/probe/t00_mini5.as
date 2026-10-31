use src.back.inflatex: selftest_v5

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-mini5.log")
}

fn log(msg str) {
    var prev str = ""
    if file.exists(crumb_path()) {
        prev = file.read_text(crumb_path())
    }
    file.write_text(crumb_path(), prev + msg + "\n")
}

fn main() {
    file.delete(crumb_path())
    log("V5 start")
    let v int = selftest_v5()
    log("V5 first-byte-check:")
    // 期望 84*10000 + 0 = 840000
    if v == 840000 {
        log("PASS b1=84 wrc=0")
    } else {
        if v < 0 {
            log("FAIL status")
        } else {
            log("FAIL other (b1 or wrc off)")
        }
    }
    log("V5 done")
}
