// t00_mod_selftest.as — 模块内回读 vs 脚本回读对账（count[7] 期望 24）。
use src.back.inflatex: selftest_fixed_count7, build_huffman

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-mst.log")
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
    log("MST start")
    let v int = selftest_fixed_count7()
    log("MST module-read count7:")
    if v == 24 {
        log("PASS module-internal count7=24")
    } else {
        if v == -1 {
            log("FAIL build failed")
        } else {
            log("FAIL module count7 not 24")
        }
    }
    // 脚本侧重建同一表并回读（对照）
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
    let w int = ht[7]
    log("MST script-read count7:")
    if st != 0 {
        log("FAIL script build failed")
    } else {
        if w == 24 {
            log("PASS script count7=24")
        } else {
            log("FAIL script count7 not 24")
        }
    }
    log("MST done")
}
