use src.back.inflatex: selftest_multiread

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-mr.log")
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
    log("MR start")
    let v int = selftest_multiread()
    log("MR check:")
    if v == 1393 {
        log("PASS acc match")
    } else {
        log("FAIL acc differs")
    }
    log("MR done")
}
