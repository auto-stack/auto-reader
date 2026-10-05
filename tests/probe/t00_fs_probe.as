// t00_fs_probe.as — READER-001 T-00 能力探针（AutoVM 轨直跑入口）。
// 用法：`auto tests/probe/t00_fs_probe.as`
// 输出：面包屑与 PASS/FAIL/NOTE 各行写入 %TEMP%/t00-breadcrumb.log
// （print 在 VM 崩溃/静默退出时会因缓冲丢失，故全部走文件）。
// 覆盖：fs/file native 读写、编码检测（read_text_range envelope）、
//       hash.file_sha256、fs 路径工具、json.parse 读取侧回环、大文本读回。
// 已知并在此探针中规避/记录的 VM 限制：
//   1) 裸列表字面量直接传 native（如 file.write_bytes(p, [1,2])）崩：
//      Invalid list ID —— 必须用 List<int>.new([...])。
//   2) `== null` 比较崩：Invalid list ID —— 用 envelope 原文子串探测。
//   3) json.to_string/json.encode 对动态 map 返回内部句柄数字（不可用作
//      持久化写侧）—— 持久化改用「手工转义写 JSON」方案，读取侧
//      json.parse + 字段访问可用（本探针 P8/P9 验证）。
//   4) file.append_text 在 Windows VM 轨报 os error 123 —— 用 read+write 拼接。
//   5) hash.file_sha256 对缺失文件抛 RuntimeError（非文档所称返回空串）——
//      调用前必须 file.exists 门控。
//   6) 180k 次线性字符串拼接曾致 VM 静默退出（exit 0 无输出）—— 大内容
//      用倍增拼接；应用导入避免逐段拼接超长文本。

fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-breadcrumb.log")
}

fn log(msg str) {
    // VM 轨 file.append_text 路径报 os error 123（见头注 4）——用 read+write 拼接
    var prev str = ""
    if file.exists(crumb_path()) {
        prev = file.read_text(crumb_path())
    }
    file.write_text(crumb_path(), prev + msg + "\n")
}

fn main() {
    log("PROBE start")
    let base str = fs.join(Env.get("TEMP"), "t00-reader-probe")
    log("PROBE base=" + base)

    // P1 目录创建
    file.delete(fs.join(base, "deep/probe.txt"))
    let made int = fs.mkdir_all(fs.join(base, "deep"))
    if made == 0 {
        if file.is_dir(fs.join(base, "deep")) {
            log("PASS mkdir_all+is_dir")
        } else {
            log("FAIL mkdir_all: dir missing after rc=0")
        }
    } else {
        log("FAIL mkdir_all rc=" + made.to_string())
    }

    // P2 UTF-8 中文写入/读回（read_text 全文）
    let book_path str = fs.join(base, "deep/probe.txt")
    let content str = "第一行：山月不知心底事\n第二行：水风空落眼前花\n第三章 摇曳碧云斜\n"
    let wrc int = file.write_text(book_path, content)
    if wrc == 0 {
        let back str = file.read_text(book_path)
        if back == content {
            log("PASS write_text+read_text utf8 roundtrip bytes=" + back.len().to_string())
        } else {
            log("FAIL read_text mismatch bytes=" + back.len().to_string())
        }
    } else {
        log("FAIL write_text rc=" + wrc.to_string())
    }

    // P3 编码检测：read_text_range envelope 对合法 UTF-8 的形状
    //    envelope = {"text":...,"total":N,"next_offset":null|N}；total:-1 = 解码/IO 失败
    let env_str str = file.read_text_range(book_path, 0, file.size(book_path))
    let env = json.parse(env_str)
    let total int = env.total
    if total > 0 {
        if env_str.find("\"next_offset\":null") >= 0 {
            log("PASS read_text_range ok-shape total=" + total.to_string())
        } else {
            log("FAIL read_text_range: next_offset not null at EOF")
        }
    } else {
        log("FAIL read_text_range valid-utf8 flagged invalid total=" + total.to_string())
    }

    // P4 编码检测：GBK 双字节（0xD6 0xD0 = "中" 的 GBK 编码）必须判 invalid。
    // T-01 修正：file.write_bytes / File.write_bytes 在 VM 轨均 rc=0 但不落盘
    // （静默失败）——早期版本此处把「文件缺失→total:-1」误判为编码拒绝。
    // 写侧校验如实降级为 NOTE；真实 GBK 字节的拒绝证据由应用级 HTTP 验证交付
    // （测试驱动侧用外部工具构造真 GBK 文件）。
    let gbk_path str = fs.join(base, "gbk.bin")
    file.write_bytes(gbk_path, List<int>.new([0xD6, 0xD0, 0xCE, 0xC4]))
    if file.exists(gbk_path) {
        let gbk_env = json.parse(file.read_text_range(gbk_path, 0, 4))
        if gbk_env.total == -1 {
            log("PASS encoding-detect gbk rejected")
        } else {
            log("FAIL encoding-detect gbk accepted total=" + gbk_env.total.to_string())
        }
    } else {
        log("NOTE write_bytes silently failed on VM (capability debt, see report); gbk rejection verified at app level")
    }
    // read_text 对同一 GBK 文件静默回 ""（不可单独用作编码判据——记录为能力边界）
    let silent str = file.read_text(gbk_path)
    if silent == "" {
        log("NOTE read_text gbk returns empty silently (must use read_text_range for validation)")
    } else {
        log("NOTE read_text gbk returned bytes=" + silent.len().to_string())
    }

    // P5 hash.file_sha256（存在文件；缺失文件会 raise，见头注 5）
    let h str = hash.file_sha256(book_path)
    if h.len() == 64 {
        log("PASS file_sha256 len=64 head=" + h.substr(0, 12))
    } else {
        log("FAIL file_sha256 len=" + h.len().to_string())
    }

    // P6 fs 路径工具：parent/filename/ext（与 join 产生的实际分隔符比对）
    let p str = fs.join(base, "deep/probe.txt")
    let parent str = fs.parent(p)
    let fname str = fs.filename(p)
    let ext str = fs.ext(p)
    if parent == fs.join(base, "deep") {
        if fname == "probe.txt" {
            if ext == ".txt" {
                log("PASS fs.path-tools")
            } else {
                log("FAIL fs.ext got=" + ext)
            }
        } else {
            log("FAIL fs.filename got=" + fname)
        }
    } else {
        log("FAIL fs.parent got=" + parent)
    }

    // P7 file.copy + exists + size
    let copy_path str = fs.join(base, "copy.txt")
    file.delete(copy_path)
    let crc int = file.copy(book_path, copy_path)
    if crc == 0 {
        if file.exists(copy_path) {
            if file.size(copy_path) == file.size(book_path) {
                log("PASS copy+exists+size")
            } else {
                log("FAIL copy size mismatch")
            }
        } else {
            log("FAIL copy: target missing")
        }
    } else {
        log("FAIL copy rc=" + crc.to_string())
    }

    // P8 json 读取侧：解析含中文/转义的书目记录并逐字段取回。
    //    （写侧 json.to_string/json.encode 对动态 map 只回内部句柄——见头注 3，
    //    此处用原文 JSON 字面量代表持久化文件内容。）
    let record_json str = "{\"title\":\"山月记\",\"author\":\"中岛敦\",\"chapters\":3,\"quote\":\"他说：\\\"山月\\\"\"}"
    let parsed = json.parse(record_json)
    if parsed.title == "山月记" {
        if parsed.chapters == 3 {
            if parsed.quote == "他说：\"山月\"" {
                log("PASS json.parse record fields utf8+escapes")
            } else {
                log("FAIL json.parse quote got=" + ("" + parsed.quote))
            }
        } else {
            log("FAIL json.parse chapters got=" + parsed.chapters.to_string())
        }
    } else {
        log("FAIL json.parse title got=" + ("" + parsed.title))
    }

    // P9 json 读取侧：数组字段逐元素访问（目录/章节表形态）
    let lib_json str = "{\"books\":[{\"id\":\"b1\",\"title\":\"沉默的大多数\",\"chapters\":[\"一\",\"二\"]}]}"
    let lib = json.parse(lib_json)
    if lib.books[0].chapters[1] == "二" {
        log("PASS json.parse nested-array utf8")
    } else {
        log("FAIL json.parse nested-array got=" + ("" + lib.books[0].chapters[1]))
    }

    // P10 大文本（约 10MiB）写盘 + read_text 全文读回 + file_sha256。
    //     倍增拼接避免 O(n²) 循环拼接（线性拼接曾致 VM 静默退出，见头注 6）。
    let big_path str = fs.join(base, "big.txt")
    let para str = "山月不知心底事，水风空落眼前花。摇曳碧云斜。江上柳如烟，雁飞残月天。\n"
    var big str = para
    var i int = 0
    while i < 18 {
        big = big + big
        i = i + 1
    }
    file.write_text(big_path, big)
    let big_back str = file.read_text(big_path)
    if big_back == big {
        let bh str = hash.file_sha256(big_path)
        log("PASS big-read bytes=" + big.len().to_string() + " sha_head=" + bh.substr(0, 12))
    } else {
        log("FAIL big-read bytes=" + big_back.len().to_string() + " want=" + big.len().to_string())
    }

    // 清理探针产物（保留 %TEMP%/t00-breadcrumb.log 供报告引用）
    file.delete(copy_path)
    file.delete(gbk_path)
    file.delete(big_path)
    file.delete(book_path)
    log("PROBE done")
}
