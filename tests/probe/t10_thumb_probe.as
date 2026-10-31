// t10_thumb_probe.as — image.thumb 在 VM 轨脚本上下文可用性（CAP-02 首探针）。
fn log_path() str {
    return fs.join(Env.get("TEMP"), "t10.log")
}
fn main() {
    let base str = fs.join(Env.get("TEMP"), "plan897")
    let png str = fs.join(base, "cover_ext.png")
    let uri str = image.thumb(png, 400)
    file.write_text(log_path(), "uri=" + uri + "\n")
}
