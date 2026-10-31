// t00_epub_cap_probe3.as — CAP-01 跟进2：定位 Q2/Q5 raise 点与 Q1 len=7 疑点。
// 结果写 %TEMP%/t00-epub-cap3.log。每步先落 crumb 再做动作。

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-epub-cap3.log")
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
    log("EPUB-CAP3 start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")
    fs.mkdir_all(base)

    // ── R1: Q1 疑点复测——5 字节写入后逐项 dump ──
    try {
        let p1 str = fs.join(base, "r1.bin")
        file.delete(p1)
        let lst = List<int>.new([72, 105, 0, 255, 128])
        log("R1 new len=" + lst.len().to_string())
        let wrc int = file.write_bytes(p1, lst)
        log("R1 write rc=" + wrc.to_string() + " size=" + fs.file_size(p1).to_string())
        let bs []int = file.read_bytes(p1)
        log("R1 read len=" + bs.len().to_string())
        var acc str = ""
        var k int = 0
        while k < bs.len() {
            acc = acc + bs[k].to_string() + " "
            k = k + 1
        }
        log("R1 bytes=" + acc)
    } catch {
        log("R1 raise")
    }

    // ── R2: Q2 分解——空 new + push 256 + write ──
    try {
        let p2 str = fs.join(base, "r2.bin")
        file.delete(p2)
        log("R2 begin")
        var lst2 = List<int>.new([])
        log("R2 new-empty ok len=" + lst2.len().to_string())
        var i int = 0
        while i < 256 {
            lst2.push(i)
            i = i + 1
        }
        log("R2 push256 ok len=" + lst2.len().to_string())
        let wrc int = file.write_bytes(p2, lst2)
        log("R2 write rc=" + wrc.to_string())
    } catch {
        log("R2 raise")
    }
    try {
        let p2 str = fs.join(base, "r2.bin")
        if file.exists(p2) {
            log("R2 size=" + fs.file_size(p2).to_string())
            let back []int = file.read_bytes(p2)
            log("R2 read len=" + back.len().to_string())
            var ok2 bool = back.len() == 256
            var k int = 0
            while k < back.len() {
                if back[k] != k {
                    ok2 = false
                    log("R2 first-mismatch at " + k.to_string() + " got " + back[k].to_string())
                }
                k = k + 1
            }
            if ok2 {
                log("R2 PASS 0..255 回环")
            }
        } else {
            log("R2 file not created")
        }
    } catch {
        log("R2 read phase raise")
    }

    // ── R3: file_sha256 对已存在二进制文件 ──
    try {
        let p2b str = fs.join(base, "r2.bin")
        if file.exists(p2b) {
            let h str = hash.file_sha256(p2b)
            log("R3 file_sha256(bin)=" + h)
        } else {
            log("R3 skip (r2.bin missing)")
        }
    } catch {
        log("R3 raise")
    }

    // ── R4: 1MiB 分解——push 1M 到 List（不含 IO）──
    try {
        log("R4 begin")
        var lst5 = List<int>.new([])
        var i5 int = 0
        while i5 < 1048576 {
            lst5.push(i5 - (i5 / 251) * 251)
            i5 = i5 + 1
        }
        log("R4 push1M ok len=" + lst5.len().to_string())
    } catch {
        log("R4 raise (push phase)")
    }

    log("EPUB-CAP3 done")
}
