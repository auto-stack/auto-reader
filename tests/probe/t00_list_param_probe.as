// t00_list_param_probe.as — List 形参在 fn 内 push 是否对调用方可见（inflatex 新契约）。
fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-lp.log")
}

fn log(msg str) {
    var prev str = ""
    if file.exists(crumb_path()) {
        prev = file.read_text(crumb_path())
    }
    file.write_text(crumb_path(), prev + msg + "\n")
}

fn add_to(l List<int>, v int) {
    l.push(v)
}

fn main() {
    file.delete(crumb_path())
    log("LP start")
    try {
        var l = List<int>.new([])
        add_to(l, 7)
        add_to(l, 8)
        let n int = l.len()
        let n0 int = l[0]
        let n1 int = l[1]
        log("LP len-grow:")
        if n == 2 {
            log("PASS len=2")
        } else {
            log("FAIL len not 2")
        }
        if n0 == 7 {
            log("PASS l0=7")
        } else {
            log("FAIL l0 not 7")
        }
        if n1 == 8 {
            log("PASS l1=8")
        } else {
            log("FAIL l1 not 8")
        }
    } catch {
        log("LP raise")
    }
    log("LP done")
}
