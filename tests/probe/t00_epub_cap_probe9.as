// t00_epub_cap_probe9.as — CAP-01 收口：let 提取 + var 累加循环（inflate 核心形态）。
// 结果写 %TEMP%/t00-epub-cap9.log。

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-epub-cap9.log")
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
    log("EPUB-CAP9 start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")
    let p1 str = fs.join(base, "s1.bin")

    // ── X1: while 循环 let 提取 + var 累加（期望 560）──
    try {
        let bs []int = file.read_bytes(p1)
        var acc int = 0
        var k int = 0
        while k < 5 {
            let e int = bs[k]
            acc = acc + e
            k = k + 1
        }
        log("X1 loop sum=" + acc.to_string() + "（期望 560）")
    } catch {
        log("X1 raise")
    }

    // ── X2: 真实 ZIP 字段算术——typed 提取形态（期望 method=8）──
    try {
        let zp str = fs.join(base, "real.zip")
        let zb []int = file.read_bytes(zp)
        let b8 int = zb[8]
        let b9 int = zb[9]
        let method int = b8 + b9 * 256
        log("X2 method=" + method.to_string() + "（期望 8）")
        let b15 int = zb[15]
        let b16 int = zb[16]
        let b17 int = zb[17]
        let b18 int = zb[18]
        let crc int = b15 + b16 * 256 + b17 * 65536 + b18 * 16777216
        log("X2 crc32=" + crc.to_string() + "（mimetype deflate 的 CRC，对照 Python）")
        // 压缩大小 @18..21?（local header: offsets: 18=comp size）——对照字段：
        let c0 int = zb[22]
        let c1 int = zb[23]
        let comp int = c0 + c1 * 256
        log("X2 local-hdr comp-size-lo16=" + comp.to_string())
    } catch {
        log("X2 raise")
    }

    // ── X3: var 累加 + 表达式右值（acc = acc + bs[k] * 2 形态）──
    try {
        let bs []int = file.read_bytes(p1)
        var acc int = 0
        var k int = 0
        while k < 5 {
            acc = acc + bs[k] * 2
            k = k + 1
        }
        log("X3 weighted sum=" + acc.to_string() + "（期望 1120）")
    } catch {
        log("X3 raise")
    }

    log("EPUB-CAP9 done")
}
