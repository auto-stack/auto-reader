// t00_epub_cap_probe5.as — CAP-01 跟进4：写列表种子规避法规模验证 + 读规模。
// 结果写 %TEMP%/t00-epub-cap5.log。

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-epub-cap5.log")
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
    log("EPUB-CAP5 start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")
    fs.mkdir_all(base)

    // ── T2: new([]) + push 最小复现（定位失败必要条件）──
    try {
        let p2 str = fs.join(base, "t2.bin")
        file.delete(p2)
        var l2 = List<int>.new([])
        l2.push(1)
        l2.push(2)
        log("T2 ready len=" + l2.len().to_string())
        let rc int = file.write_bytes(p2, l2)
        log("T2 write rc=" + rc.to_string())
    } catch {
        log("T2 raise（new([])+push 即坏）")
    }

    // ── T1: 种子法 new([0]) + push 到 256 + 写 + 读回（按 size）──
    try {
        let p1 str = fs.join(base, "t1.bin")
        file.delete(p1)
        var l1 = List<int>.new([0])
        var i int = 1
        while i < 256 {
            l1.push(i)
            i = i + 1
        }
        log("T1 ready len=" + l1.len().to_string())
        let rc int = file.write_bytes(p1, l1)
        log("T1 write rc=" + rc.to_string() + " size=" + fs.file_size(p1).to_string())
        let back []int = file.read_bytes(p1)
        var ok bool = fs.file_size(p1) == 256
        var k int = 0
        while k < 256 {
            if back[k] != k {
                ok = false
            }
            k = k + 1
        }
        if ok {
            log("T1 PASS 种子法 0..255 回环")
        } else {
            log("T1 FAIL 回环不符")
        }
    } catch {
        log("T1 raise")
    }

    // ── T3: 种子法 64KB ──
    try {
        let p3 str = fs.join(base, "t3.bin")
        file.delete(p3)
        var l3 = List<int>.new([0])
        var i3 int = 1
        while i3 < 65536 {
            l3.push(i3 - (i3 / 251) * 251)
            i3 = i3 + 1
        }
        log("T3 ready len=" + l3.len().to_string())
        let rc int = file.write_bytes(p3, l3)
        log("T3 write rc=" + rc.to_string() + " size=" + fs.file_size(p3).to_string())
    } catch {
        log("T3 raise")
    }

    // ── T4: 外部大文件读回（64KB，按 size 走查求和）──
    try {
        let p4 str = fs.join(base, "t3.bin")
        let sz int = fs.file_size(p4)
        let back []int = file.read_bytes(p4)
        var sum int = 0
        var k4 int = 0
        while k4 < sz {
            sum = sum + back[k4]
            k4 = k4 + 1
        }
        log("T4 read64k walk sum=" + sum.to_string())
    } catch {
        log("T4 raise")
    }

    log("EPUB-CAP5 done")
}
