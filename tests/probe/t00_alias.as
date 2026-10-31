// t00_alias.as — var 别名 + 条件重赋值 + 消费 形态判别（inflate 表选择形态）。
use src.back.inflatex: build_huffman

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-al.log")
}

fn log(msg str) {
    var prev str = ""
    if file.exists(crumb_path()) {
        prev = file.read_text(crumb_path())
    }
    file.write_text(crumb_path(), prev + msg + "\n")
}

fn fill42(t List<int>) {
    t.push(42)
}

fn main() {
    file.delete(crumb_path())
    log("AL start")
    // 形态1：别名 + callee 填充 + 消费（无重赋值）
    var a = List<int>.new([0])
    var t = a
    fill42(t)
    let v1 int = t[1]
    log("AL shape1 (alias+fill):")
    if v1 == 42 {
        log("PASS 42")
    } else {
        log("FAIL")
    }
    // 形态2：别名 + 条件重赋值 + 消费
    var b = List<int>.new([7])
    var u = a
    var cond bool = true
    if cond {
        u = b
    }
    let v2 int = u[1]
    log("AL shape2 (alias+reassign):")
    if v2 == 7 {
        log("PASS 7")
    } else {
        log("FAIL")
    }
    // 形态3：跨模块被调填充后别名消费（inflate 形态：fixed 表由 build_huffman 填充）
    var lens = List<int>.new([0])
    var s int = 1
    while s < 5 {
        lens.push(1)
        s = s + 1
    }
    var ht = List<int>.new([0])
    let st int = build_huffman(lens, 1, 4, ht)
    var h2 = ht
    let v3 int = h2[2]
    log("AL shape3 (modfill+alias):")
    if st == 0 {
        if v3 == 4 {
            log("PASS count1=4")
        } else {
            log("FAIL count1")
        }
    } else {
        log("FAIL build")
    }
    log("AL done")
}
