use src.back.inflatex: selftest_module_read

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-mread.log")
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
    log("MRD start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")
    let bin_p str = fs.join(base, "vec_fixed.bin")
    let v int = selftest_module_read(bin_p)
    log("MRD check:")
    if v == 1120193 {
        log("PASS 11,201,93")
    } else {
        log("FAIL mismatch")
    }
    log("MRD done")
}
