// t00_epub_cap_probe.as — READER-003 T-00 CAP-01 能力探针（当前 CLI 实测）。
// 只回答「本 CLI 是否提供某能力、以什么形态提供」，不承载业务语义。
// 结果写入 %TEMP%/t00-epub-cap.log；每项独立 try/catch，失败不终止后续项。
// 运行：D:/autostack/auto-man/target/debug/auto.exe tests/probe/t00_epub_cap_probe.as

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-epub-cap.log")
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
    log("EPUB-CAP start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")
    fs.mkdir_all(base)

    // ── P1: 真实 sha256（文本入参）——EPUB 二进制身份候选 ──
    try {
        let h str = hash.sha256("abc")
        if h == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" {
            log("PASS hash.sha256(text) known-vector")
        } else {
            log("FAIL hash.sha256 got=" + h)
        }
    } catch {
        log("FAIL hash.sha256 raise")
    }

    // ── P2: hash.file_sha256（文件入参）──
    try {
        let p2 str = fs.join(base, "abc.txt")
        file.write_text(p2, "abc")
        let h2 str = hash.file_sha256(p2)
        if h2 == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" {
            log("PASS hash.file_sha256 known-vector")
        } else {
            log("FAIL hash.file_sha256 got=" + h2)
        }
    } catch {
        log("FAIL hash.file_sha256 raise")
    }

    // ── P3: File.read_bytes 形态（返回什么类型？）──
    try {
        let p3 str = fs.join(base, "bin1.bin")
        file.write_text(p3, "Hi") // 0x48 0x69
        let bs = File.read_bytes(p3)
        let t3 str = type_of(bs)
        log("NOTE read_bytes type_of=" + t3)
        if t3 == "list" {
            log("NOTE read_bytes len=" + bs.len().to_string() + " b0=" + bs[0].to_string() + " b1=" + bs[1].to_string())
        }
    } catch {
        log("FAIL File.read_bytes raise: 不可用或崩溃")
    }

    // ── P4: File.write_bytes 在 VM 轨是否真落盘（001 曾报静默失败）──
    try {
        let p4 str = fs.join(base, "bin2.bin")
        let lst = List<int>.new([72, 105])
        let wrc int = File.write_bytes(p4, lst)
        var back str = ""
        if file.exists(p4) {
            back = file.read_text(p4)
        }
        if back == "Hi" {
            log("PASS File.write_bytes vm 落盘 rc=" + wrc.to_string())
        } else {
            log("FAIL File.write_bytes vm rc=" + wrc.to_string() + " back=[" + back + "] exists=" + file.exists(p4).to_string())
        }
    } catch {
        log("FAIL File.write_bytes raise")
    }

    // ── P5: file.write_bytes 小写形态 ──
    try {
        let p5 str = fs.join(base, "bin3.bin")
        let lst5 = List<int>.new([72, 105])
        let wrc5 int = file.write_bytes(p5, lst5)
        var back5 str = ""
        if file.exists(p5) {
            back5 = file.read_text(p5)
        }
        if back5 == "Hi" {
            log("PASS file.write_bytes vm 落盘 rc=" + wrc5.to_string())
        } else {
            log("FAIL file.write_bytes vm rc=" + wrc5.to_string() + " back=[" + back5 + "]")
        }
    } catch {
        log("FAIL file.write_bytes raise")
    }

    // ── P6: base64 形态 ──
    try {
        let b6 str = base64.encode("Hi")
        log("NOTE base64.encode vm got=" + b6)
    } catch {
        log("FAIL base64.encode raise")
    }

    // ── P7: Zip 候选名不可用——已在脚本编译层证实：`zip.open`/`Zip.open`
    // 触发 "Undefined variable: zip" 编译错误（exit 1，首次运行实测）。
    // 未知模块名是编译错而非运行时 raise，不能进同一脚本 try/catch。

    // ── P8: type_of / byte_len（PLAN-781 已用，回归确认）──
    try {
        let t8a str = type_of(1)
        let t8b str = type_of("s")
        let bl int = "山山".byte_len()
        log("NOTE type_of(1)=" + t8a + " type_of('s')=" + t8b + " byte_len(山山)=" + bl.to_string())
    } catch {
        log("FAIL type_of/byte_len raise")
    }

    // ── P9: List<int> 微基准（纯 .at inflate 可行性输入）──
    try {
        let lst9 = List<int>.new([])
        var i int = 0
        while i < 200000 {
            lst9.push(i - (i / 256) * 256)
            i = i + 1
        }
        var sum int = 0
        var j int = 0
        while j < lst9.len() {
            sum = sum + lst9[j]
            j = j + 1
        }
        log("NOTE list-perf 200k push+read sum=" + sum.to_string())
    } catch {
        log("FAIL list-perf raise")
    }

    // ── P10: 字符串逐字节走查原语（inflate 位流读入候选）──
    try {
        let s10 str = "ABC"
        var acc int = 0
        var k int = 0
        while k < s10.byte_len() {
            let ch10 str = s10.substr(k, 1)
            acc = acc + ch10.substr(0, 1).to_int()
            k = k + 1
        }
        log("NOTE substr-byte-walk acc=" + acc.to_string())
    } catch {
        log("FAIL substr-byte-walk raise")
    }

    log("EPUB-CAP done")
}
