// t00_epub_cap_probe2.as — CAP-01 跟进：read_bytes 消费形态 / 字节回环 / VM 吞吐。
// 结果写 %TEMP%/t00-epub-cap2.log。

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-epub-cap2.log")
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
    log("EPUB-CAP2 start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")
    fs.mkdir_all(base)

    // ── Q1: file.read_bytes 小写形态 + 类型化绑定 []int ──
    try {
        let p1 str = fs.join(base, "bin4.bin")
        let lst = List<int>.new([72, 105, 0, 255, 128])
        file.write_bytes(p1, lst)
        let bs []int = file.read_bytes(p1)
        log("PASS file.read_bytes typed len=" + bs.len().to_string() + " b=" + bs[0].to_string() + "," + bs[1].to_string() + "," + bs[2].to_string() + "," + bs[3].to_string() + "," + bs[4].to_string())
    } catch {
        log("FAIL file.read_bytes typed raise")
    }

    // ── Q2: write_bytes 全值域回环（0..255，含 0x00/0xFF）──
    try {
        let p2 str = fs.join(base, "bin5.bin")
        var lst2 = List<int>.new([])
        var i int = 0
        while i < 256 {
            lst2.push(i)
            i = i + 1
        }
        let wrc int = file.write_bytes(p2, lst2)
        let back []int = file.read_bytes(p2)
        var ok2 bool = back.len() == 256
        var k int = 0
        while k < back.len() {
            if back[k] != k {
                ok2 = false
            }
            k = k + 1
        }
        if ok2 {
            log("PASS write_bytes/read_bytes 0..255 回环 rc=" + wrc.to_string())
        } else {
            log("FAIL 0..255 回环 len=" + back.len().to_string())
        }
    } catch {
        log("FAIL 0..255 回环 raise")
    }

    // ── Q3: file_sha256 对二进制文件（EPUB 身份链候选）──
    try {
        let p3 str = fs.join(base, "bin5.bin")
        let h3 str = hash.file_sha256(p3)
        log("NOTE file_sha256(bin5)=" + h3)
    } catch {
        log("FAIL file_sha256 binary raise")
    }

    // ── Q4: VM 吞吐微基准——4M 次简单算术循环（inflate 位操作量级参考）──
    try {
        var acc int = 0
        var i int = 0
        while i < 4000000 {
            acc = acc + (i - (i / 7) * 7)
            i = i + 1
        }
        log("NOTE vm-loop 4M iters acc=" + acc.to_string())
    } catch {
        log("FAIL vm-loop raise")
    }

    // ── Q5: List<int> 大容量（2M 字节 ≈ 小型 EPUB 资源）读取求和 ──
    try {
        let p5 str = fs.join(base, "bin6.bin")
        var lst5 = List<int>.new([])
        var i5 int = 0
        while i5 < 1048576 {
            lst5.push(i5 - (i5 / 251) * 251)
            i5 = i5 + 1
        }
        file.write_bytes(p5, lst5)
        let back5 []int = file.read_bytes(p5)
        var sum int = 0
        var k5 int = 0
        while k5 < back5.len() {
            sum = sum + back5[k5]
            k5 = k5 + 1
        }
        log("NOTE 1MiB bytes read+sum len=" + back5.len().to_string() + " sum=" + sum.to_string())
    } catch {
        log("FAIL 1MiB raise")
    }

    log("EPUB-CAP2 done")
}
