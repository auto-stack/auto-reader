use src.back.inflatex: selftest_first_sym, selftest_first_code, selftest_first_cl

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-comp.log")
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
    log("COMP start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")
    let bin_p str = fs.join(base, "vec_fixed.bin")
    let data []int = file.read_bytes(bin_p)
    let s int = selftest_first_sym(data)
    log("COMP sym:")
    if s == 84 {
        log("PASS sym=84")
    } else {
        log("FAIL sym != 84")
    }
    let c int = selftest_first_code(data)
    log("COMP code:")
    if c == 132 {
        log("PASS code=132")
    } else {
        log("FAIL code != 132")
    }
    let l int = selftest_first_cl(data)
    log("COMP cl:")
    if l == 8 {
        log("PASS cl=8")
    } else {
        log("FAIL cl != 8")
    }
    log("COMP done")
}
