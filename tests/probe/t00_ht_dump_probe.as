// t00_ht_dump_probe.as — build_huffman 固定表逐字段 dump（4 字节 LE 写盘）。
use src.back.inflatex: build_huffman

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-htdump.log")
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
    log("HTDUMP start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")
    // 固定字面量表（与 inflatex.inflate 内一致）
    var lens = List<int>.new([0])
    var s int = 1
    while s < 289 {
        let sym int = s - 1
        if sym < 144 {
            lens.push(8)
        } else {
            if sym < 256 {
                lens.push(9)
            } else {
                if sym < 280 {
                    lens.push(7)
                } else {
                    lens.push(8)
                }
            }
        }
        s = s + 1
    }
    var ht = List<int>.new([0])
    let st int = build_huffman(lens, 1, 288, ht)
    if st != 0 {
        log("build status nonzero")
    } else {
        log("build status 0")
    }
    let n int = ht.len()
    log("ht-len-marker")
    // 期望 46 + 288 = 334；dump 全表为 4 字节 LE
    var ob = List<int>.new([0])
    var i int = 1
    while i < n {
        let v int = ht[i]
        // 单字节 dump：值 mod 256（count/sym_base/symbol 全 < 256 可判；
        // first_code 大值仅低字节可判——足够对账）
        ob.push(v - (v / 256) * 256)
        i = i + 1
    }
    let out_p str = fs.join(base, "ht_dump.bin")
    file.delete(out_p)
    file.write_bytes(out_p, ob)
    log("dump written")
    log("HTDUMP done")
}
