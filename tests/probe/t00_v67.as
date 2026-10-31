use src.back.inflatex: selftest_v6_header, selftest_v7_firstsym_safe

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-v67.log")
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
    log("V67 start")
    let h int = selftest_v6_header()
    log("V6 header-check:")
    if h == 11015 {
        log("PASS header state 11015")
    } else {
        if h == 11105 {
            log("VAL 11105")
        } else {
            if h == 11005 {
                log("VAL 11005")
            } else {
                if h == 11115 {
                    log("VAL 11115")
                } else {
                    if h == 11011 {
                        log("VAL 11011")
                    } else {
                        if h == 1015 {
                            log("VAL 1015")
                        } else {
                            log("VAL other")
                        }
                    }
                }
            }
        }
    }
    let y int = selftest_v7_firstsym_safe()
    log("V7 firstsym-check:")
    if y == 84 {
        log("PASS first sym 84")
    } else {
        if y == -1 {
            log("FAIL build")
        } else {
            log("FAIL first sym wrong")
        }
    }
    log("V67 done")
}
