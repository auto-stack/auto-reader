// t00_idx_assign_probe.as — 堆列表索引赋值在当前 CLI 是否可用（inflatex 依赖）。
fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-idx.log")
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
    log("IDX start")
    try {
        var a = List<int>.new([0, 0, 0])
        a[1] = 42
        log("A1 a[1]=42 → " + a[1].to_string())
        var i int = 2
        a[i] = a[i] + 1
        log("A2 a[2]=a[2]+1 → " + a[2].to_string())
        var b = List<int>.new([5])
        b.push(0)
        b[1] = 9
        log("A3 push后赋值 b[1]=" + b[1].to_string())
    } catch {
        log("A raise")
    }
    log("IDX done")
}
