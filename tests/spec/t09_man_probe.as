fn log_path() str {
    return fs.join(Env.get("TEMP"), "t09.log")
}
fn log(msg str) {
    var prev str = ""
    if file.exists(log_path()) {
        prev = file.read_text(log_path())
    }
    file.write_text(log_path(), prev + msg + "
")
}
fn main() {
    let man str = "nav\x01nav.xhtml|c1\x01ch1.xhtml|c2\x01ch2.xhtml|img1\x01images/cover.png|"
    file.write_text(log_path(), "man-bytes=" + man.byte_len().to_string() + "\n")
    var pos int = 0
    var guard int = 0
    while guard < 8192 {
        guard = guard + 1
        let s int = find_after(man, "|", pos)
        if s < 0 {
            file.write_text(log_path(), "scan-end\n")
            return
        }
        let e int = find_after(man, "|", s)
        if e < 0 {
            file.write_text(log_path(), "scan-end2\n")
            return
        }
        let rec str = man.substr(s + 1, e - s - 1)
        let sep int = rec.find("\x01")
        file.write_text(log_path(), "rec-sep " + sep.to_string() + "\n")
        if sep > 0 {
            let rid str = rec.substr(0, sep)
            if rid == "c1" {
                file.write_text(log_path(), "FOUND c1\n")
                return
            }
        }
        pos = e
    }
}
fn find_after(xml str, needle str, from int) int {
    if from <= 0 {
        return xml.find(needle)
    }
    if from >= xml.len() {
        return -1
    }
    let tail str = xml.substr(from, xml.len() - from)
    let p int = tail.find(needle)
    if p < 0 {
        return -1
    }
    return p + from
}
