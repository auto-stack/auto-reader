// t00_dynlit.as — 动态 vs 字面量索引回读一致性（期望 acc=288, lit=288）。
use src.back.inflatex: selftest_dyn_vs_lit

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-dl.log")
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
    log("DL start")
    let v int = selftest_dyn_vs_lit()
    // 期望 288*100000 + 288 = 28800288
    log("DL result-check:")
    if v == 28800288 {
        log("PASS dyn==lit==288")
    } else {
        if v == -1 {
            log("FAIL build failed")
        } else {
            log("FAIL mismatch")
        }
    }
    log("DL done")
}
