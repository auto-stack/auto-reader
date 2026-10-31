// t00_epub_cap_probe8.as — CAP-01 判别：FFI 列表元素毒化是值携带还是表达式形态。
// 结果写 %TEMP%/t00-epub-cap8.log。

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-epub-cap8.log")
}

fn log(msg str) {
    var prev str = ""
    if file.exists(crumb_path()) {
        prev = file.read_text(crumb_path())
    }
    file.write_text(crumb_path(), prev + msg + "\n")
}

/// fn 边界加法（模块代码的自然形态）。
fn add2(a int, b int) int {
    return a + b
}

fn mul2(a int, b int) int {
    return a * b
}

fn main() {
    file.delete(crumb_path())
    log("EPUB-CAP8 start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")
    let p1 str = fs.join(base, "s1.bin")

    try {
        let bs []int = file.read_bytes(p1)
        // W1: 直接类型化提取 + 表达式内算术
        let e0 int = bs[0]
        let r1 int = e0 + 1
        log("W1 e0+1=" + r1.to_string() + "（期望 73；721=毒化）")
        let e1 int = bs[1]
        let r2 int = e0 + e1
        log("W2 e0+e1=" + r2.to_string() + "（期望 177）")
        // W3: fn 边界算术
        let r3 int = add2(bs[0], bs[1])
        log("W3 add2(b0,b1)=" + r3.to_string() + "（期望 177）")
        let r4 int = mul2(bs[9], 256)
        log("W4 mul2(b9,256)=" + r4.to_string() + "（b9=0 期望 0）")
        // W5: fn 内求和（传列表不行——VM 缺陷——改传标量循环）
        let r5 int = add2(add2(bs[0], bs[1]), add2(bs[2], add2(bs[3], bs[4])))
        log("W5 nested add2 all5=" + r5.to_string() + "（期望 560）")
        // W6: while 循环内 let 提取再累加（每元素先入新 let）
        var acc int = 0
        var k int = 0
        while k < 5 {
            let e int = bs[k]
            acc = acc + e
            k = k + 1
        }
        log("W6 loop let-then-add=" + acc.to_string() + "（期望 560）")
    } catch {
        log("W raise")
    }

    log("EPUB-CAP8 done")
}
