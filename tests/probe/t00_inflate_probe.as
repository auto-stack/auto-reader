// t00_inflate_probe.as — inflatex.inflate 正确性验证（Python zlib 生成向量）。
// 向量（外部生成到 %TEMP%/t00-epub-cap-probe/）：
//   raw_deflate.bin          = zlib.compressobj(9, DEFLATED, -15) 裸 deflate 流
//   raw_deflate_expected.txt = 原文
// oracle：解压字节写盘（种子字节规避 N-003-1）→ read_text → substr(1,·)
// 与期望全文逐字比较。覆盖：动态/静态哈夫曼、存储块、多块。
// 运行：auto tests/probe/t00_inflate_probe.as

use src.back.inflatex: inflate_file

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-inflate.log")
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
    log("INFLATE start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")
    let bin_p str = fs.join(base, "vec_fixed.bin")
    let exp_p str = fs.join(base, "vec_fixed_expected.txt")
    let sz int = fs.file_size(bin_p)
    log("vector compressed size:")
    if sz > 0 {
        log("size-ok")
    }
    var out = List<int>.new([0])
    let st int = inflate_file(bin_p, 0, sz, 12 * 1048576, out)
    let stn int = out.len() - 1
    if st < 0 {
        log("FAIL inflate status:")
        let olen int = out.len()
        if olen > 3 {
            let t1 int = out[1]
            let t2 int = out[2]
            let t3 int = out[3]
            if t1 == 3 {
                log("trace bi=3")
            } else {
                log("trace bi other")
            }
            if t2 == 33944 {
                log("trace code=33944")
            } else {
                log("trace code other")
            }
            if t3 == 16 {
                log("trace cl=16")
            } else {
                log("trace cl other")
            }
        } else {
            log("no trace pushed")
        }
        if st == -1 {
            log("code -1 bad block type")
        }
        if st == -2 {
            log("code -2 bad length code")
        }
        if st == -3 {
            log("code -3 bad distance")
        }
        if st == -4 {
            log("code -4 out budget")
        }
        if st == -5 {
            log("code -5 bad code lengths")
        }
        if st == -6 {
            log("code -6 input exhausted")
        }
        if st == -7 {
            log("code -7 stored LEN/NLEN")
        }
        if st >= 0 {
            log("code unknown")
        }
    } else {
        log("PASS inflate status-0")
        let exp str = file.read_text(exp_p)
        let ebl int = exp.byte_len()
        log("expected byte_len check:")
        if ebl == stn {
            log("PASS len equal")
        } else {
            log("FAIL len differs")
        }
        // 种子字节写侧规避（N-003-1）：out[0] 为种子占位 0，替换为解压首字节
        let first int = out[1]
        var ob = List<int>.new([first])
        var k2 int = 2
        while k2 < stn + 1 {
            ob.push(out[k2])
            k2 = k2 + 1
        }
        let out_p str = fs.join(base, "inflate_out.bin")
        file.delete(out_p)
        let wrc int = file.write_bytes(out_p, ob)
        let back str = file.read_text(out_p)
        let body str = back.substr(1, back.len() - 1)
        if body == exp {
            log("PASS 全文逐字一致（write+read_text oracle）")
        } else {
            log("FAIL 全文不一致")
            let bl int = body.byte_len()
            log("body-len-vs-exp:")
            if bl < ebl {
                log("body shorter")
            } else {
                if bl > ebl {
                    log("body longer")
                } else {
                    log("same len diff content")
                }
            }
            // 首个失配点
            var i int = 0
            var n int = ebl
            if bl < n {
                n = bl
            }
            var logged int = 0
            while i < n {
                if logged == 0 {
                    if body.substr(i, 1) != exp.substr(i, 1) {
                        log("NOTE first-diff byte offset below")
                        log("offset-mark")
                        logged = 1
                        i = n
                    }
                }
                i = i + 1
            }
        }
        if wrc != 0 {
            log("NOTE write rc nonzero")
        }
    }
    log("INFLATE done")
}
