use src.back.inflatex: selftest_ifbranch_read

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-ifb.log")
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
    log("IFB start")
    let v int = selftest_ifbranch_read()
    log("IFB check:")
    if v == 288 {
        log("PASS 288")
    } else {
        log("FAIL ifbranch reads")
    }
    log("IFB done")
}
