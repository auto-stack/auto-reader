use src.back.inflatex: selftest_tworead

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-two.log")
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
    log("TWO start")
    let v int = selftest_tworead()
    log("TWO check:")
    if v == 65248 {
        log("PASS 2-read ok")
    } else {
        log("FAIL 2-read differs")
    }
    log("TWO done")
}
