use src.back.inflatex: selftest_v8a_first_byte, selftest_v8b_b0, selftest_v8c_cur_cnt

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-v8.log")
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
    log("V8 start")
    let a int = selftest_v8a_first_byte()
    log("V8a first byte:")
    if a == 11 {
        log("PASS 11")
    } else {
        log("FAIL not 11")
    }
    let b int = selftest_v8b_b0()
    log("V8b b0:")
    if b == 1 {
        log("PASS 1")
    } else {
        log("FAIL not 1")
    }
    let c int = selftest_v8c_cur_cnt()
    log("V8c packed:")
    if c == 110015 {
        log("PASS b0=1,btype=1,cur=1,cnt=5")
    } else {
        log("FAIL packed mismatch")
    }
    log("V8 done")
}
