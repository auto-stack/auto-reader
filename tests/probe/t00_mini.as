// t00_mini.as — 模块内全解压自检（期望 84*1000+2280 = 842280）。
use src.back.inflatex: selftest_mini_decode

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-mini.log")
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
    log("MINI start")
    let v int = selftest_mini_decode()
    log("MINI result-check:")
    if v == 842280 {
        log("PASS decode ok 84/2280")
    } else {
        if v < -1000 {
            log("FAIL inflate status negative")
        } else {
            log("FAIL wrong result")
        }
    }
    log("MINI done")
}
