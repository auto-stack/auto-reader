// t00_epub_cap_probe7.as — CAP-01 最终：FFI 列表→VM 列表一次拷贝，算术只在 VM 列表上。
// 结果写 %TEMP%/t00-epub-cap7.log。

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-epub-cap7.log")
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
    log("EPUB-CAP7 start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")

    // ── V1: FFI 列表逐元素 to_int → VM 列表，之后全部算术在 VM 列表 ──
    try {
        let p1 str = fs.join(base, "s1.bin")
        let bs []int = file.read_bytes(p1)
        let sz int = fs.file_size(p1)
        var vm = List<int>.new([0])
        var k int = 0
        while k < sz {
            let e int = ("" + bs[k]).to_int()
            vm.push(e)
            k = k + 1
        }
        var acc int = 0
        var j int = 0
        while j < vm.len() {
            acc = acc + vm[j]
            j = j + 1
        }
        log("V1 vm-list sum=" + acc.to_string() + "（期望 560）")
    } catch {
        log("V1 raise")
    }

    // ── V2: 真实 ZIP 头经 VM 列表解析（method/局部头字段）──
    try {
        let zp str = fs.join(base, "real.zip")
        let sz int = fs.file_size(zp)
        let zb []int = file.read_bytes(zp)
        var vm2 = List<int>.new([0])
        var k2 int = 0
        while k2 < sz {
            let e2 int = ("" + zb[k2]).to_int()
            vm2.push(e2)
            k2 = k2 + 1
        }
        log("V2 copied len=" + vm2.len().to_string() + "（期望 417=1种子+416）")
        // magic PK\x03\x04 @0..3（vm2[0] 是种子 0，真实字节从 [1] 起）
        let b0 int = vm2[1]
        let b1 int = vm2[2]
        let b2 int = vm2[3]
        let b3 int = vm2[4]
        log("V2 magic=" + b0.to_string() + "," + b1.to_string() + "," + b2.to_string() + "," + b3.to_string() + "（期望 80,75,3,4）")
        // method @8..9 LE → vm2[9], vm2[10]
        let m int = vm2[9] + vm2[10] * 256
        log("V2 method=" + m.to_string() + "（期望 8=deflate）")
        // CRC32 @14..17 LE → vm2[15..18]
        let c int = vm2[15] + vm2[16] * 256 + vm2[17] * 65536 + vm2[18] * 16777216
        log("V2 crc32=" + c.to_string())
    } catch {
        log("V2 raise")
    }

    // ── V3: 拷贝+校验和吞吐微测（416B ZIP → 64KB 级文件）──
    try {
        let p3 str = fs.join(base, "t3.bin") // 64KB（探针5产物）
        let sz int = fs.file_size(p3)
        let zb []int = file.read_bytes(p3)
        var vm3 = List<int>.new([0])
        var k3 int = 0
        while k3 < sz {
            let e3 int = ("" + zb[k3]).to_int()
            vm3.push(e3)
            k3 = k3 + 1
        }
        var acc3 int = 0
        var j3 int = 0
        while j3 < vm3.len() {
            acc3 = acc3 + vm3[j3]
            j3 = j3 + 1
        }
        log("V3 64KB copy+sum=" + acc3.to_string())
    } catch {
        log("V3 raise")
    }

    log("EPUB-CAP7 done")
}
