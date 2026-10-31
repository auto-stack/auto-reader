// t00_epub_cap_probe4.as — CAP-01 跟进3：读列表真实边界 / 大写形态 / 追加语义。
// 结果写 %TEMP%/t00-epub-cap4.log。

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-epub-cap4.log")
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
    log("EPUB-CAP4 start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")
    fs.mkdir_all(base)

    // ── S1: 读列表边界——按 fs.file_size 走查 vs 按 len 走查 ──
    try {
        let p1 str = fs.join(base, "s1.bin")
        file.delete(p1)
        let lst = List<int>.new([72, 105, 0, 255, 128])
        file.write_bytes(p1, lst)
        let bs []int = file.read_bytes(p1)
        let sz int = fs.file_size(p1)
        log("S1 size=" + sz.to_string() + " readlen=" + bs.len().to_string())
        // 按 size 走查
        var ok bool = true
        var k int = 0
        while k < sz {
            if bs[k] != [72, 105, 0, 255, 128][k] {
                ok = false
            }
            k = k + 1
        }
        log("S1 walk-by-size ok=" + ok.to_string())
        // 越界探测：index = size（预期 raise）
        try {
            let v int = bs[sz]
            log("S1 bs[size]=" + v.to_string() + "（未 raise，越界可读）")
        } catch {
            log("S1 bs[size] raise（越界即 raise）")
        }
        // index = len-1
        try {
            let v2 int = bs[bs.len() - 1]
            log("S1 bs[len-1]=" + v2.to_string())
        } catch {
            log("S1 bs[len-1] raise")
        }
    } catch {
        log("S1 raise")
    }

    // ── S2: 大写 File.read_bytes 形态 ──
    try {
        let p1 str = fs.join(base, "s1.bin")
        let bs2 []int = File.read_bytes(p1)
        log("S2 File.read_bytes typed len=" + bs2.len().to_string())
    } catch {
        log("S2 File.read_bytes typed raise")
    }

    // ── S3: write_bytes 追加语义（两次调用）──
    try {
        let p3 str = fs.join(base, "s3.bin")
        file.delete(p3)
        let a = List<int>.new([1, 2])
        let b = List<int>.new([3, 4])
        let rc1 int = file.write_bytes(p3, a)
        let rc2 int = file.write_bytes(p3, b)
        let sz int = fs.file_size(p3)
        log("S3 rc1=" + rc1.to_string() + " rc2=" + rc2.to_string() + " size=" + sz.to_string() + "（4=追加 2=截断）")
    } catch {
        log("S3 raise")
    }

    // ── S4: push-built 列表给 write_bytes 的最小复现（框架缺陷证据）──
    try {
        let p4 str = fs.join(base, "s4.bin")
        file.delete(p4)
        var l4 = List<int>.new([9])
        l4.push(8)
        log("S4 list ready len=" + l4.len().to_string())
        let rc int = file.write_bytes(p4, l4)
        log("S4 write rc=" + rc.to_string() + "（push-built 列表写成功与否）")
    } catch {
        log("S4 raise（push-built 列表 write_bytes 复现）")
    }

    // ── S5: 字面量列表写入后 push 再写（混合形态）──
    try {
        let p5 str = fs.join(base, "s5.bin")
        file.delete(p5)
        var l5 = List<int>.new([9])
        log("S5 literal ok len=" + l5.len().to_string())
        let rc int = file.write_bytes(p5, l5)
        log("S5 literal-list write rc=" + rc.to_string())
    } catch {
        log("S5 raise")
    }

    log("EPUB-CAP4 done")
}
