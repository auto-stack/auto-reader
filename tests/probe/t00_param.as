use src.back.inflatex: selftest_param_read

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-param.log")
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
    log("PRM start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")
    let bin_p str = fs.join(base, "vec_fixed.bin")
    let data []int = file.read_bytes(bin_p)
    let v int = selftest_param_read(data)
    log("PRM check:")
    if v == 11211 {
        log("PASS 11,201")
    } else {
        log("FAIL mismatch")
    }
    log("PRM done")
}
