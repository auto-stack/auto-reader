// t00_epub_cap_probe6.as — CAP-01 收口：read_bytes 元素类型 + 真实 ZIP 头读取。
// 结果写 %TEMP%/t00-epub-cap6.log。

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-epub-cap6.log")
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
    log("EPUB-CAP6 start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")

    // ── U1: read_bytes 元素 type_of + to_int ──
    try {
        let p1 str = fs.join(base, "s1.bin") // 内容 72,105,0,255,128（探针4产物）
        let bs []int = file.read_bytes(p1)
        let sz int = fs.file_size(p1)
        let e0 = bs[0]
        log("U1 type_of(e0)=" + type_of(e0) + " e0=" + ("" + e0))
        let n0 int = ("" + e0).to_int()
        log("U1 to_int=" + n0.to_string())
        var acc int = 0
        var k int = 0
        while k < sz {
            acc = acc + ("" + bs[k]).to_int()
            k = k + 1
        }
        log("U1 walk-to_int sum=" + acc.to_string() + "（期望 560）")
    } catch {
        log("U1 raise")
    }

    // ── U2: 真实 ZIP（Python zipfile 产物）头读取——PK\x03\x04 魔数 ──
    try {
        let zp str = fs.join(base, "real.zip")
        let sz int = fs.file_size(zp)
        let zb []int = file.read_bytes(zp)
        log("U2 zip size=" + sz.to_string())
        var magic str = ""
        var k2 int = 0
        while k2 < 4 {
            magic = magic + ("" + zb[k2]).to_int().to_string() + ","
            k2 = k2 + 1
        }
        log("U2 first4=" + magic + "（期望 80,75,3,4）")
        // 本地文件头 method 字段 @8（2 字节 LE）：deflate=8 / stored=0
        let m0 int = ("" + zb[8]).to_int()
        let m1 int = ("" + zb[9]).to_int()
        let method int = m0 + m1 * 256
        log("U2 first-entry method=" + method.to_string() + "（0=stored 8=deflate）")
        let h str = hash.file_sha256(zp)
        log("U2 file_sha256=" + h)
    } catch {
        log("U2 raise")
    }

    log("EPUB-CAP6 done")
}
