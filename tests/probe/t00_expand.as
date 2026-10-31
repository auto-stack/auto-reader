use src.back.inflatex: selftest_expand_roundtrip

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-exp.log")
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
    log("EXP start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")
    let bin_p str = fs.join(base, "vec_fixed.bin")
    let out_p str = base + "/expand_out.bin"
    file.delete(out_p)
    let v int = selftest_expand_roundtrip(bin_p, out_p)
    log("EXP count-check:")
    if v == 744 {
        log("PASS 744 bits")
    } else {
        log("FAIL count")
    }
    log("EXP done")
}
