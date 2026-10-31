use src.back.inflatex: selftest_count7_after_expand

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-axe.log")
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
    log("AXE start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")
    let bin_p str = fs.join(base, "vec_fixed.bin")
    let v int = selftest_count7_after_expand(bin_p)
    log("AXE count7:")
    if v == 24 {
        log("PASS 24")
    } else {
        log("FAIL not 24")
    }
    log("AXE done")
}
