// t00_seed_callee_probe.as — callee push 到「已种子」列表的游标语义。
fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-sc.log")
}

fn log(msg str) {
    var prev str = ""
    if file.exists(crumb_path()) {
        prev = file.read_text(crumb_path())
    }
    file.write_text(crumb_path(), prev + msg + "\n")
}

fn callee_add(l List<int>) {
    l.push(71)
    l.push(72)
}

fn main() {
    file.delete(crumb_path())
    log("SC start")
    try {
        var l = List<int>.new([9])
        callee_add(l)
        let n int = l.len()
        log("SC len:")
        if n == 3 {
            log("PASS len=3 (seed+2)")
        } else {
            if n == 2 {
                log("FAIL len=2 (覆盖种子)")
            } else {
                log("FAIL other len")
            }
        }
        let v0 int = l[0]
        let v1 int = l[1]
        let v2 int = l[2]
        log("SC v0-check:")
        if v0 == 9 {
            log("PASS v0=9 seed kept")
        } else {
            log("FAIL v0 not 9")
        }
        log("SC v1-check:")
        if v1 == 71 {
            log("PASS v1=71")
        } else {
            log("FAIL v1 not 71")
        }
        log("SC v2-check:")
        if v2 == 72 {
            log("PASS v2=72")
        } else {
            log("FAIL v2 not 72")
        }
    } catch {
        log("SC raise")
    }
    log("SC done")
}
