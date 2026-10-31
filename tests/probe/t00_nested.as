use src.back.inflatex: selftest_nested_read

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-nst.log")
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
    log("NST start")
    let v int = selftest_nested_read()
    log("NST check:")
    if v == 288288288 {
        log("PASS 288 x3")
    } else {
        log("FAIL nested reads")
    }
    log("NST done")
}
