// t00_fn_list_probe.as — fn 返回 List 在当前 CLI 的可用性（inflatex 表构建依赖）。
fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-fnlist.log")
}

fn log(msg str) {
    var prev str = ""
    if file.exists(crumb_path()) {
        prev = file.read_text(crumb_path())
    }
    file.write_text(crumb_path(), prev + msg + "\n")
}

/// 字面量列表 fn 返回
fn mk_lit() List<int> {
    return List<int>.new([3, 1, 4, 1, 5])
}

/// push 构建 fn 返回
fn mk_push() List<int> {
    var l = List<int>.new([9])
    l.push(8)
    l.push(7)
    return l
}

fn main() {
    file.delete(crumb_path())
    log("FNLIST start")
    // B1: 字面量返回
    try {
        let a = mk_lit()
        log("B1 type=" + type_of(a) + " len=" + a.len().to_string() + " a0=" + a[0].to_string() + " a4=" + a[4].to_string())
    } catch {
        log("B1 raise（字面量 fn 返回坏）")
    }
    // B2: push 返回
    try {
        let b = mk_push()
        log("B2 type=" + type_of(b) + " len=" + b.len().to_string() + " b0=" + b[0].to_string())
    } catch {
        log("B2 raise（push fn 返回坏）")
    }
    // B3: fn 内直接索引（不经返回）
    try {
        let c0 int = mk_lit()[2]
        log("B3 mk_lit()[2]=" + c0.to_string())
    } catch {
        log("B3 raise")
    }
    log("FNLIST done")
}
