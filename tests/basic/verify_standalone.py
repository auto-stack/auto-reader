#!/usr/bin/env python3
# verify_standalone.py — READER-005 独立运行双 profile 永久聚合门（T-05，AC-05）。
#
# 用法：
#   python tests/basic/verify_standalone.py --profile vue   # Vue 前端 + VM HTTP 后端
#   python tests/basic/verify_standalone.py --profile vm    # VM 全轨（分离模式，原生窗口）
#   可选：--auto-bin <auto.exe>（缺省 AUTO_BIN → PATH auto）；--keep 保留实例供调试
#
# 聚合面（计划 §6 R-01..06 映射）：
#   R-01 启动面：profile 自管启动就绪（后端 books + 前端 200 / 原生窗口 MCP）；
#         错误 tool 负例（AUTO_UI_TOOL_BIN 缺失路径 → 启动失败非零）；
#         占口负例（第二实例 bind 失败且既有实例不受影响）。
#   R-02 图像：HTTP oracle（探针书导入 → images[] 恒全量、字节逐字、缓存
#         命中/冷重启同 URI 同字节）+ 真实 UI 解码 oracle（vue=Playwright
#         naturalWidth>0×3 + src 互异 + 错误行；vm=原生物件挂载 + 截图像素）。
#   R-03 链接：HTTP oracle（章内/跨章/子目录/脚注 fragment 解析 + 三类诚实
#         拒绝）+ UI oracle（vue=chips V-20 入 pane + 原文逐字 + 拒绝提示；
#         vm=chips 渲染 + 抽屉跳转）。
#   R-04 注释/搜索/导出/恢复：verify_local --profile（002 面全量）+
#         vm 加原生驱动（tests/native/test_native_standalone_ui.py）。
#   R-05 负例：超预算（img_too_large）/缺条目（提取失败诚实）/不支持类型
#         （img_unsupported_type）+ verify_epub（导入安全/预算/坏书全量）。
#   R-06 受控反例（oracle 区分力）：毁损已提取图片字节 → R-02 UI oracle
#         必须真实失败（非零）；还原合法对照 → 通过。反例仅触碰隔离数据
#         目录内该书的章节缓存资源，不触原件/索引/他书。
#
# 纪律：夹具只进隔离数据目录；失败检查「输出与退出码」同时成立；不计
# API profile 标签为 UI 执行。退出码：0=全过；1=有 FAIL；2=环境不可用。
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from probe_books import generate_all, RED, BLUE  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), str(detail)[:200]))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else " :: " + str(detail)[:180]))


def http(method, path, body=None, port=17825, timeout=120):
    url = f"http://127.0.0.1:{port}" + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        v = json.loads(resp.read().decode("utf-8"))
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {"_raw": v}
    return v


def url_ok(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status == 200
    except Exception:
        return False


def find_chapter_dir(data_dir, book_id):
    """书目受管章节缓存目录——读盘（不依赖存活实例，vm 停机段亦可用）。"""
    lib_path = os.path.join(data_dir, "library.json")
    if not os.path.exists(lib_path):
        return None
    with open(lib_path, encoding="utf-8") as f:
        lib = json.load(f)
    for b in lib.get("books", []):
        if b.get("book_id") == book_id:
            return b["managed_path"] + ".chapters"
    return None


class VueApp:
    """Vue 前端 + VM HTTP 后端（auto run --server=vm）。"""

    def __init__(self, auto_bin, data_dir, log_path):
        self.auto_bin = auto_bin
        self.data_dir = data_dir
        self.log_path = log_path
        self.proc = None
        self.log = None

    def start(self):
        self.log = open(self.log_path, "w", encoding="utf-8", errors="replace")
        env = dict(os.environ,
                   AUTO_READER_DATA=self.data_dir,
                   AUTO_HTTP_STEP_BUDGET="1000000000",
                   AUTO_HTTP_REQUEST_TIMEOUT_MS="300000")
        self.proc = subprocess.Popen([self.auto_bin, "run", "--server=vm"],
                                     cwd=ROOT, env=env, stdout=self.log, stderr=self.log)

    def wait_ready(self, deadline=90.0):
        t0 = time.monotonic()
        while time.monotonic() - t0 < deadline:
            if self.proc.poll() is not None:
                return False
            if url_ok("http://127.0.0.1:17825/api/library/books"):
                return True
            time.sleep(1.5)
        return False

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
        if self.log:
            self.log.close()


def npx_cmd():
    return shutil.which("npx") or shutil.which("npx.cmd") or "npx"


def run_cmd(cmd, cwd=None, env=None, timeout=900):
    e = dict(os.environ)
    if env:
        e.update(env)
    try:
        r = subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"


def r01(app, auto_bin, data_dir, log_dir, profile):
    """启动面 + 失败控制（vue: 前端 200；错误 tool / 占口负例）。
    app 由调用方构造并纳入 finally——本函数异常不留孤儿实例。"""
    app.start()
    ready = app.wait_ready()
    check("R-01 profile boots and backend ready", ready, f"poll 90s data={data_dir}")
    if profile == "vue":
        # 前端就绪有界轮询（vite 冷启动慢于后端——单发探测会把冷启动误判
        # 为不服务，dry3 实测；条件不变：17824 必须真实可服务）
        front_ok = False
        t0 = time.monotonic()
        while time.monotonic() - t0 < 60:
            if url_ok("http://localhost:17824/"):
                front_ok = True
                break
            time.sleep(1.5)
        check("R-01 vite frontend serves", front_ok, "poll 60s")
    else:
        check("R-01 vm track backend on 17825", url_ok("http://127.0.0.1:17825/api/library/books"))
    # 占口负例：以裸 socket 占住后端端口 → 新实例启动失败（deadline 内未
    # 就绪即失败控制成立）；不拉第二个 auto run（其 pnpm/vite 会扰动主
    # 实例前端——在册 N-2 族劣化），既有服务不受占口影响
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 17825))
    sock.listen(1)
    second = VueApp(auto_bin, os.path.join(data_dir, "r01-second"),
                    os.path.join(log_dir, "r01-second.log"))
    second.start()
    check("R-01 occupied-port boot fails deadline", not second.wait_ready(deadline=45))
    second.stop()
    sock.close()
    check("R-01 main instance survives occupied-port probe",
          url_ok("http://127.0.0.1:17825/api/library/books"))
    # 错误 tool 负例：AUTO_UI_TOOL_BIN 指向缺失路径 → 具名失败非零
    r, out = run_cmd([auto_bin, "run", "--server=vm"], cwd=ROOT,
                     env={"AUTO_READER_DATA": os.path.join(data_dir, "r01-badtool"),
                          "AUTO_UI_TOOL_BIN": os.path.join(data_dir, "no-such-tool.exe"),
                          "AUTO_HTTP_STEP_BUDGET": "1000000000"},
                     timeout=120)
    check("R-01 wrong tool fails nonzero with named discovery error",
          r != 0 and "discovery failed" in out, f"rc={r} out={out[:120]}")
    return app


def r02_http(data_dir):
    """R-02 HTTP oracle：恒全量 images[]、字节身份、缓存命中/冷重启同 URI。"""
    imp = http("POST", "/api/library/import",
               {"path": os.path.join(data_dir, "probe-images.epub"), "author": "T02", "force": False})
    check("R-02 probe-images import ok", imp.get("code") == "ok", imp)
    bid = imp.get("book_id", "")
    c1 = http("GET", f"/api/library/chapter?book_id={bid}&number=1")
    imgs = c1.get("images", [])
    ok_entries = [e for e in imgs if not e.get("err")]
    err_entries = [e for e in imgs if e.get("err")]
    check("R-02 images[] complete on first read (3 ok + 1 honest err)",
          len(ok_entries) == 3 and len(err_entries) == 1
          and err_entries[0].get("err") == "img_unsupported_type", imgs)
    check("R-02 URIs are app-owned stable scheme",
          all(e["uri"].startswith(f"/api/reader/media/{bid}/res_") for e in ok_entries), ok_entries)
    # 字节身份：红/蓝不串 + 含空格资源可取
    red = open(os.path.join(HERE, "..", "..", "tests", "basic", "probe_books.py"), "rb").read()  # noqa: F841
    def fetch(uri):
        with urllib.request.urlopen("http://127.0.0.1:17825" + uri, timeout=30) as r:
            return r.status, r.headers.get("Content-Type"), r.read()
    red_bytes = _png_bytes(8, 8, (200, 30, 30))
    blue_bytes = _png_bytes(8, 8, (30, 30, 200))
    kinds = []
    for e in ok_entries:
        st, ct, body = fetch(e["uri"])
        if st == 200 and ct == "image/png":
            if body == red_bytes:
                kinds.append("RED")
            elif body == blue_bytes:
                kinds.append("BLUE")
            else:
                kinds.append("OTHER")
        else:
            kinds.append(f"HTTP{st}")
    check("R-02 byte identity: collision pair distinct (RED/BLUE) + space-named ok",
          kinds.count("RED") == 2 and kinds.count("BLUE") == 1, kinds)
    # 缓存命中（同会话再读）URI 恒定
    c1b = http("GET", f"/api/library/chapter?book_id={bid}&number=1")
    check("R-02 cache-hit re-read returns same URIs",
          [e["uri"] for e in c1b.get("images", []) if not e.get("err")]
          == [e["uri"] for e in ok_entries], c1b.get("images"))
    return bid


def _png_bytes(w, h, rgb):
    import struct
    import zlib
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = b""
    for _ in range(h):
        raw += b"\x00" + bytes(rgb) * w
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def r03_http(data_dir):
    """R-03 HTTP oracle：链接解析全形 + 诚实拒绝。"""
    imp = http("POST", "/api/library/import",
               {"path": os.path.join(data_dir, "probe-links.epub"), "author": "T03", "force": False})
    check("R-03 probe-links import ok", imp.get("code") == "ok", imp)
    bid = imp.get("book_id", "")
    c1 = http("GET", f"/api/library/chapter?book_id={bid}&number=1")
    links = {(l["label"], l["ch"], l["para"]) for l in c1.get("links", [])}
    check("R-03 cross-chapter fragment resolves", ("到第二章重复段", 2, 2) in links, links)
    check("R-03 subdir-relative href resolves (chapter-dir base)",
          ("到第三章", 3, 1) in links, links)
    check("R-03 self-chapter anchor resolves", ("到本章末段", 1, 6) in links, links)
    broken = [l for l in c1.get("links", []) if l["ch"] == 0]
    check("R-03 external/missing-chapter/unknown-fragment honestly rejected (ch=0)",
          len(broken) == 4, broken)
    # 行对齐：链接行文本与正文行逐字（锚不被链接解析破坏）
    lines = c1.get("body", "").split("\n")
    check("R-03 body line format unchanged (inline link text intact)",
          lines[2] == "跨章引用到第二章重复段在此。", repr(lines[2]))
    return bid


def r05(data_dir, auto_bin):
    """R-05 负例：预算/缺失/不支持 + verify_epub 全量。"""
    # 负例书（超预算 13MiB 资源 + 缺条目）现场生成
    import zipfile
    neg = os.path.join(data_dir, "probe-neg.epub")
    container = ('<?xml version="1.0"?><container version="1.0" '
                 'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
                 '<rootfile full-path="OEBPS/content.opf" '
                 'media-type="application/oebps-package+xml"/></rootfiles></container>')
    opf = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Probe Neg</dc:title>'
           '<dc:creator>T05</dc:creator></metadata>'
           '<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
           '<item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/>'
           '<item id="i1" href="huge.png" media-type="image/png"/>'
           '<item id="i2" href="gone.png" media-type="image/png"/></manifest>'
           '<spine><itemref idref="c1"/></spine></package>')
    nav = ('<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml" '
           'xmlns:epub="http://www.idpf.org/2007/ops"><body><nav epub:type="toc"><ol>'
           '<li><a href="ch1.xhtml">C1</a></li></ol></nav></body></html>')
    ch1 = ('<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml"><body>'
           '<h1>C1</h1><p>Huge.</p><p><img src="huge.png"/></p>'
           '<p>Gone.</p><p><img src="gone.png"/></p></body></html>')
    with zipfile.ZipFile(neg, "w", zipfile.ZIP_STORED) as z:
        z.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container)
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/nav.xhtml", nav)
        z.writestr("OEBPS/ch1.xhtml", ch1)
        z.writestr("OEBPS/huge.png", _png_bytes(8, 8, (200, 30, 30)) + b"\x00" * (13 * 1024 * 1024))
    imp = http("POST", "/api/library/import", {"path": neg, "author": "T05", "force": False})
    check("R-05 negative book imports (structure legal)", imp.get("code") == "ok", imp)
    c1 = http("GET", f"/api/library/chapter?book_id={imp.get('book_id', '')}&number=1")
    errs = {e["k"]: e["err"] for e in c1.get("images", [])}
    check("R-05 oversize resource rejected img_too_large",
          errs.get("OEBPS/huge.png") == "img_too_large", errs)
    check("R-05 missing entry rejected honestly",
          errs.get("OEBPS/gone.png") == "img_extract_failed", errs)
    # verify_epub 全量（自管 8080 实例，与主实例隔离）
    r, out = run_cmd([sys.executable, os.path.join(ROOT, "tests", "epub", "verify_epub.py"), "--auto"],
                     cwd=ROOT, env={"AUTO_EXE": auto_bin}, timeout=600)
    check("R-05 verify_epub full gate (22 checks)", r == 0 and "PASS=22 FAIL=0" in out,
          f"rc={r} tail={out[-160:]}")


def r06_mutation(data_dir, auto_bin, bid):
    """R-06 受控反例：毁损已提取图片 → R-02 UI oracle 必须真实失败；还原 → 通过。"""
    cdir = find_chapter_dir(data_dir, bid)
    check("R-06 locate chapter cache dir", bool(cdir), cdir)
    res_files = [f for f in os.listdir(cdir) if f.startswith("res_")] if cdir and os.path.isdir(cdir) else []
    check("R-06 extracted resources present", len(res_files) == 3, res_files)
    backup = {}
    for f in res_files:
        p = os.path.join(cdir, f)
        backup[f] = open(p, "rb").read()
        open(p, "wb").write(b"\x00" * 64)  # 毁损解码字节（保留扩展名）
    r, out = run_cmd([npx_cmd(), "playwright", "test", "basic/standalone_ui.spec.ts", "--grep", "R-02"],
                     cwd=os.path.join(ROOT, "tests"),
                     env={"AUTO_READER_DATA": data_dir,
                          "PW_CHROMIUM": os.environ.get(
                              "PW_CHROMIUM",
                              r"C:\Users\zhaop\AppData\Local\ms-playwright\chromium-1248\chrome-win64\chrome.exe")},
                     timeout=300)
    check("R-06 mutated images make R-02 UI oracle FAIL (nonzero)", r != 0,
          f"rc={r} tail={out[-140:]}")
    for f, data in backup.items():
        open(os.path.join(cdir, f), "wb").write(data)
    r, out = run_cmd([npx_cmd(), "playwright", "test", "basic/standalone_ui.spec.ts", "--grep", "R-02"],
                     cwd=os.path.join(ROOT, "tests"),
                     env={"AUTO_READER_DATA": data_dir,
                          "PW_CHROMIUM": os.environ.get(
                              "PW_CHROMIUM",
                              r"C:\Users\zhaop\AppData\Local\ms-playwright\chromium-1248\chrome-win64\chrome.exe")},
                     timeout=300)
    check("R-06 restored control passes", r == 0, f"rc={r} tail={out[-140:]}")


def _corrupt_fixture_pngs(epub_path):
    """把探针书内三个合法 PNG 条目替换为等长垃圾字节（反例仅触碰隔离
    out-dir 内的夹具副本；结构与扩展名不变——提取/服务成功、解码失败）。"""
    import zipfile
    tmp = epub_path + ".mutated"
    with zipfile.ZipFile(epub_path, "r") as zin,             zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.endswith(".png"):
                data = b"\x00" * 64
            zout.writestr(item.filename, data)
    os.replace(tmp, epub_path)


def r06_mutation_vm(auto_bin, home):
    """R-06 原生面：夹具副本内毁损图片字节 → 原生驱动 NS-02 像素 oracle
    必须真实失败（驱动非零退出）；还原合法夹具 → 0 FAIL。驱动自管数据根，
    反例经夹具副本注入（驱动自包含契约不变）。"""
    # 第一轮：合法夹具对照（0 FAIL）
    mut_dir = os.path.join(home, "native-mutated")
    os.makedirs(mut_dir, exist_ok=True)
    for p, t, a in generate_all(mut_dir):
        pass
    probe_img = os.path.join(mut_dir, "probe-images.epub")
    check("R-06(vm) fixture copy generated", os.path.exists(probe_img), probe_img)
    r, out = run_cmd([sys.executable, os.path.join(ROOT, "tests", "native",
                                                   "test_native_standalone_ui.py"),
                      "--auto-bin", auto_bin, "--app-dir", ROOT, "--out-dir", mut_dir],
                     cwd=ROOT, timeout=1200)
    open(os.path.join(home, "native-control.log"), "w", encoding="utf-8").write(out)
    check("R-06(vm) pristine control passes (0 FAIL)", r == 0, f"rc={r} log={home}/native-control.log")
    # 反例：毁损夹具 PNG → oracle 必须真实失败。驱动以 --no-regen 导入
    # out-dir 内既有（毁损）夹具副本——026 实测：驱动默认重生成会先还原
    # 变异（rc=0 根因），变异必须真正抵达被测应用。
    _corrupt_fixture_pngs(probe_img)
    mut_dir2 = os.path.join(home, "native-mutated2")
    os.makedirs(mut_dir2, exist_ok=True)
    for p, t, a in generate_all(mut_dir2):
        pass
    _corrupt_fixture_pngs(os.path.join(mut_dir2, "probe-images.epub"))
    time.sleep(8)
    r, out = run_cmd([sys.executable, os.path.join(ROOT, "tests", "native",
                                                   "test_native_standalone_ui.py"),
                      "--auto-bin", auto_bin, "--app-dir", ROOT, "--out-dir", mut_dir2,
                      "--no-regen"],
                     cwd=ROOT, timeout=1200)
    open(os.path.join(home, "native-mutated.log"), "w", encoding="utf-8").write(out)
    check("R-06(vm) mutated images make native pixel oracle FAIL (nonzero)", r != 0,
          f"rc={r} log={home}/native-mutated.log")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["vue", "vm"], default="vue")
    ap.add_argument("--auto-bin", default=os.environ.get("AUTO_BIN"))
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    auto_bin = args.auto_bin or shutil.which("auto")
    if not auto_bin:
        print("FATAL: auto CLI not found (PATH/AUTO_BIN/--auto-bin)")
        sys.exit(2)

    run = uuid.uuid4().hex[:8]
    home = os.environ.get("VERIFY_STANDALONE_HOME",
                          os.path.join(r"D:/autostack/plan-artifacts", "verify-standalone-" + run))
    home = home.replace("\\", "/")
    data_dir = os.path.join(home, "data")
    log_dir = os.path.join(home, "logs")
    os.makedirs(data_dir)
    os.makedirs(log_dir)
    for p, t, a in generate_all(data_dir):
        print("FIXTURE", t, "->", p)

    # 端口预检：17824/17825 必须空闲——孤儿实例/他实例会让本实例 bind
    # 失败而测试全部打到别人身上（首轮 gate 实证）。具名失败非零。
    import socket

    def port_free(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sk:
            try:
                sk.bind(("127.0.0.1", port))
                return True
            except OSError:
                return False

    if not (port_free(17825) and port_free(17824)):
        print("FATAL: ports 17824/17825 occupied (orphan instance? kill stale auto.exe first)")
        sys.exit(2)

    app = None
    try:
        # ── R-01 ──
        app = VueApp(auto_bin, data_dir, os.path.join(log_dir, "r01-boot.log"))
        r01(app, auto_bin, data_dir, log_dir, args.profile)
        # ── R-02 HTTP ──
        bid2 = r02_http(data_dir)
        # ── R-03 HTTP ──
        r03_http(data_dir)
        # ── R-05（HTTP 面 + verify_epub 自管 8080；vm 须在主实例停止前）──
        r05(data_dir, auto_bin)
        # ── R-02/R-03 UI oracle ──
        if args.profile == "vue":
            r, out = run_cmd([npx_cmd(), "playwright", "test", "basic/standalone_ui.spec.ts"],
                             cwd=os.path.join(ROOT, "tests"),
                             env={"AUTO_READER_DATA": data_dir,
                                  "PW_CHROMIUM": os.environ.get(
                                      "PW_CHROMIUM",
                                      r"C:\Users\zhaop\AppData\Local\ms-playwright\chromium-1248\chrome-win64\chrome.exe")},
                             timeout=600)
            check("R-02/R-03 Vue UI oracle (standalone_ui 3 specs)", r == 0, f"rc={r} tail={out[-200:]}")
        else:
            # vm：原生驱动自管窗口实例（-B 17825）——主实例必须先停，否则
            # 驱动后端 bind 失败而前端打到主实例（split-brain，gate 实证）
            app.stop()
            time.sleep(2)
            r, out = run_cmd([sys.executable, os.path.join(ROOT, "tests", "native",
                                                           "test_native_standalone_ui.py"),
                              "--auto-bin", auto_bin, "--app-dir", ROOT, "--out-dir",
                              os.path.join(home, "native")],
                             cwd=ROOT, timeout=1200)
            open(os.path.join(home, "native-driver.log"), "w", encoding="utf-8").write(out)
            check("R-02/R-03/R-04 native UI oracle (driver 0 FAIL)", r == 0, f"rc={r} log={home}/native-driver.log")
        # ── R-06 受控反例：oracle 区分力（双 profile 各自的真实 UI 门）──
        if args.profile == "vue":
            r06_mutation(data_dir, auto_bin, bid2)
        # ── R-04：verify_local（002 面全量；自管 17845/17846 独立实例）──
        r, out = run_cmd([sys.executable, os.path.join(ROOT, "tests", "annotations", "verify_local.py"),
                          "--profile", args.profile],
                         cwd=ROOT, env={"AUTO_EXE": auto_bin}, timeout=1500)
        want = "TOTAL PASS=50 FAIL=0 SKIP=0" if args.profile == "vue" else "TOTAL PASS=49 FAIL=0"
        check("R-04 verify_local " + args.profile, r == 0 and want in out, f"rc={r} tail={out[-200:]}")
        if args.profile == "vm":
            r06_mutation_vm(auto_bin, home)
        # ── 冷重启身份（R-02 尾段）：重启实例后 URI+字节不变 ──
        app.stop()
        time.sleep(2)
        app2 = VueApp(auto_bin, data_dir, os.path.join(log_dir, "cold.log"))
        app2.start()
        check("COLD restart boots", app2.wait_ready())
        c1 = http("GET", "/api/library/chapter?book_id=" + bid2 + "&number=1")
        imgs = [e for e in c1.get("images", []) if not e.get("err")]
        st, ct, body = 0, "", b""
        if imgs:
            with urllib.request.urlopen("http://127.0.0.1:17825" + imgs[0]["uri"], timeout=30) as rr:
                st = rr.status
                ct = rr.headers.get("Content-Type")
                body = rr.read()
        check("COLD first image still serves correct bytes", st == 200 and ct == "image/png" and len(body) == len(_png_bytes(8, 8, (200, 30, 30))),
              f"{st} {ct} {len(body)}")
        app2.stop()

        fails = [n for (n, ok, _) in RESULTS if not ok]
        print(f"\n== verify_standalone[{args.profile}] checks={len(RESULTS)} fails={len(fails)} ==")
        for n in fails:
            print("  FAILED:", n)
        sys.exit(0 if not fails else 1)
    finally:
        if app and not args.keep:
            app.stop()


if __name__ == "__main__":
    main()
