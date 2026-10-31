use src.back.inflatex: selftest_first_tri

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-tri.log")
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
    log("TRI start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")
    let bin_p str = fs.join(base, "vec_fixed.bin")
    let data []int = file.read_bytes(bin_p)
    let v int = selftest_first_tri(data)
    // 期望：首符号 'T'=84, code=132, cl=8 → 84132000
    log("TRI check:")
    if v == 84132008 {
        log("PASS sym84/code132/cl8")
    } else {
        if v == -51 {
            log("FAIL btype!=1")
        } else {
            if v == -5 {
                log("FAIL table build")
            } else {
                if v == 84132000 {
                    log("VAL cl=0!")
                } else {
                    log("FAIL tri other")
                }
            }
        }
    }
    log("TRI done")
}
