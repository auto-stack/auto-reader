// t00_epub_cap_probe10.as — file.copy VM 轨探针（受管原件拷贝候选）。
fn crumb_path() str {
    return fs.join(Env.get("TEMP"), "t00-epub-cap10.log")
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
    log("EPUB-CAP10 start")
    let base str = fs.join(Env.get("TEMP"), "t00-epub-cap-probe")
    let src str = fs.join(base, "real.zip")
    let dst str = fs.join(base, "real-copy.zip")
    file.delete(dst)
    let rc int = file.copy(src, dst)
    if file.exists(dst) {
        let s1 int = fs.file_size(src)
        let s2 int = fs.file_size(dst)
        let h1 str = hash.file_sha256(src)
        let h2 str = hash.file_sha256(dst)
        if s1 == s2 {
            if h1 == h2 {
                log("PASS file.copy 二进制逐字节（sha256 相同，size=" + s1.to_string() + "）")
            } else {
                log("FAIL file.copy sha256 不一致")
            }
        } else {
            log("FAIL file.copy size 不一致 " + s1.to_string() + " vs " + s2.to_string())
        }
    } else {
        log("FAIL file.copy rc=" + rc.to_string() + " 未落盘")
    }
    log("EPUB-CAP10 done")
}
