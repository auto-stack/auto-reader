use src.back.inflatex: selftest_write_out

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-mini2.log")
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
    log("MINI2 start")
    let v int = selftest_write_out()
    log("MINI2 write rc:")
    if v == 0 {
        log("PASS wrote")
    } else {
        log("FAIL write or decode")
    }
    log("MINI2 done")
}
