#!/usr/bin/env python3
# gen_corpus.py — PLAN-026 T-01 固定语料生成器（探针 profile，不替代 reader 产品导入预算）。
#
# 产出（全部确定性：固定 id/内容/字节，无随机源）：
#   probe-alpha.epub  探针甲（主书，V-01..V-07 主链）
#   probe-beta.epub   探针乙（V-08 双实例第二书）
#   negative-malformed.epub  截断损伤书（V-07 拒绝对照）
#   negative-oversize.epub   超 1MiB profile 书（V-07 拒绝对照；仍 < reader 30MiB 产品线）
#   corpus-manifest.json     指纹清单（sha256 + 关键身份）
#
# 每本合法书含（计划 §5.1 profile）：中文+emoji 段、同一章三处重复句（长句可
# 跨行）、跨行长段、1 张合法 PNG、CSS 样式、章内脚注 + 跨章脚注、3 章。
#
# 用法：python gen_corpus.py --out-dir <隔离目录>
import argparse
import hashlib
import json
import os
import struct
import sys
import zipfile
import zlib

# ── 冻结的重复句（oracle 与引擎两侧的唯一耦合点是这些常量本身）──
REPEAT_A = "探针重复句甲🦊：琥珀色的狐狸跃过懒狗时携带三枚星形饼干，并轻声数到十七✨，随后沿对角线穿过整段跨度以便在窄栏里真实换行。"
REPEAT_B = "探针重复句乙🐙：深蓝色的章鱼在暗礁之间整理十二枚贝壳🫧，把第七枚留给回声，然后沉入更深的走廊。"
REPEAT_A2 = "探针复现句甲贰🔑：三十七只萤火虫按逆时针绕过石灯笼，把影子叠成第九种形状。"

FILLER = [
    "页边留白处有一行淡淡的批注，墨迹已经泛褐，像是多年以前某位读者留下的脚印。",
    "雨点敲在遮棚上，节奏忽快忽慢；桌上那盏油灯把两个影子投在墙上，一个在写字，一个在打盹。",
    "📜 远行的行囊里只有半块干粮、一枚指南针和一封没有署名的信。信封上的火漆完好如初。",
    "风从山谷另一头吹来，带来潮湿的苔藓气味，也带来远处钟楼的第七次报时。",
]

CROSS_LINE = ("这一段刻意写得很长并且不在中途使用任何句读分隔符因此在窄栏排版时必然跨越多行形成一条"
              "连续的选择路径适合用来验证跨行拖选时引擎给出的范围定位是否与原文字符流一致而不会在换行处"
              "产生错位或者把同一行的两个不同片段拼接成看似连续实则断裂的假锚点这是探针甲专门准备的第三类样本。")


def png_bytes(w, h, rgb):
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    row = b"\x00" + bytes(rgb) * w
    raw = row * h
    sig = b"\x89PNG\r\n\x1a\n"
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def container_xml():
    return ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<container version=\"1.0\" xmlns=\"urn:oasis:names:tc:opendocument:xmlns:container\">\n"
            "  <rootfiles><rootfile full-path=\"OEBPS/content.opf\" media-type=\"application/oebps-package+xml\"/></rootfiles>\n"
            "</container>\n")


def opf(book_id, title, creator):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="zh">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:{book_id}</dc:identifier>
    <dc:title>{esc(title)}</dc:title>
    <dc:language>zh</dc:language>
    <dc:creator>{esc(creator)}</dc:creator>
    <meta property="dcterms:modified">2026-11-02T00:00:00Z</meta>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="css" href="style.css" media-type="text/css"/>
    <item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
    <item id="c2" href="ch2.xhtml" media-type="application/xhtml+xml"/>
    <item id="c3" href="ch3.xhtml" media-type="application/xhtml+xml"/>
    <item id="img1" href="images/probe.png" media-type="image/png"/>
  </manifest>
  <spine>
    <itemref idref="c1"/><itemref idref="c2"/><itemref idref="c3"/>
  </spine>
</package>
'''


def nav(book_id, title):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh">
<head><title>{esc(title)} 目录</title><link rel="stylesheet" type="text/css" href="style.css"/></head>
<body epub:type="frontmatter">
  <nav epub:type="toc" id="toc">
    <h1>目录</h1>
    <ol>
      <li><a href="ch1.xhtml">第一章 三次重复</a></li>
      <li><a href="ch2.xhtml">第二章 图像与脚注</a></li>
      <li><a href="ch3.xhtml">第三章 跨章注与复现</a></li>
    </ol>
  </nav>
</body>
</html>
'''


CSS = ("body{font-family:serif;line-height:1.7;margin:1.2em}"
       "h1{color:#23415e;border-bottom:2px solid #23415e}"
       "p.probe-repeat{background:#fdf6e3;padding:0.4em;border-left:4px solid #b58900}"
       ".probe-img{max-width:60%;border:1px solid #93a1a1}"
       "aside.note{font-size:0.85em;color:#586e75}")


def ch1(para_repeat, para_repeat2, note_target, cross_note):
    """三处重复句（p2/p6/p9）+ 跨行长段 + emoji 段 + 跨章注引用。"""
    r = f'<p class="probe-repeat">{esc(para_repeat)}</p>'
    r2 = f'<p class="probe-repeat">{esc(para_repeat2)}</p>' if para_repeat2 else ""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh">
<head><title>第一章 三次重复</title><link rel="stylesheet" type="text/css" href="style.css"/></head>
<body>
  <h1>第一章 三次重复</h1>
  <p>{esc(FILLER[0])}</p>
  {r}
  <p>{esc(FILLER[1])}</p>
  <p>🦊✨🍰 这里有一段带表情符号的引入文本，用于验证多字节安全与 UTF-16 偏移纪律。</p>
  {r2}
  <p>{esc(CROSS_LINE)}</p>
  <p>{esc(FILLER[2])}</p>
  {r}
  <p>后文的跨章注见<a epub:type="noteref" href="{note_target}"><sup>①</sup></a>，本句之后还有一段普通文字用来隔开选区边界。</p>
  <p>{esc(FILLER[3])}</p>
</body>
</html>
'''


def ch2(img_alt):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh">
<head><title>第二章 图像与脚注</title><link rel="stylesheet" type="text/css" href="style.css"/></head>
<body>
  <h1>第二章 图像与脚注</h1>
  <p>下图是一张确定性生成的纯色探针图，用于验证图像解码与资源所有权。</p>
  <img class="probe-img" src="images/probe.png" alt="{esc(img_alt)}"/>
  <p>本章带一条章内注<a epub:type="noteref" href="#local-note"><sup>②</sup></a>。</p>
  <aside class="note" epub:type="footnote" id="local-note">章内注：这张图只属于本书，跨书读取属于 path-escape 负例。</aside>
</body>
</html>
'''


def ch3(para_repeat3_list):
    ps = "".join(f'<p class="probe-repeat">{esc(p)}</p>' for p in para_repeat3_list)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh">
<head><title>第三章 跨章注与复现</title><link rel="stylesheet" type="text/css" href="style.css"/></head>
<body>
  <h1>第三章 跨章注与复现</h1>
  <p>第一章的引用注落在本章末尾的注块中，正文在此继续。</p>
  <aside class="note" epub:type="footnote" id="cross-note">跨章注：来自第一章的引用落到本章，验证跨章脚注链。</aside>
  {ps}
  <p>全书完。</p>
</body>
</html>
'''


def build_epub(path, book_id, title, creator, para_repeat, para_repeat2, para_repeat3_list,
               img_rgb, img_alt, note_target):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip",
                   compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container_xml(), zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", opf(book_id, title, creator), zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/nav.xhtml", nav(book_id, title), zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/style.css", CSS, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/images/probe.png", png_bytes(96, 64, img_rgb), zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/ch1.xhtml", ch1(para_repeat, para_repeat2, note_target, True),
                   zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/ch2.xhtml", ch2(img_alt), zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/ch3.xhtml", ch3(para_repeat3_list), zipfile.ZIP_DEFLATED)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out = args.out_dir
    os.makedirs(out, exist_ok=True)

    produced = {}
    # 甲（主书）：REPEAT_A 全书 ×3（ch1 两处：第2、第8段；ch3 一处），V-02
    # 目标 = 阅读序第 2 处 = ch1 第二个重复段；另有 REPEAT_A2 ×2 作次锚。
    a = build_epub(
        os.path.join(out, "probe-alpha.epub"),
        book_id="11111111-2222-3333-4444-555555555555",
        title="探针甲：引擎表面样本", creator="PLAN-026 corpus",
        para_repeat=REPEAT_A, para_repeat2=REPEAT_A2,
        para_repeat3_list=[REPEAT_A, REPEAT_A2],
        img_rgb=(178, 60, 20), img_alt="探针甲琥珀图",
        note_target="ch3.xhtml#cross-note")
    produced["probe-alpha.epub"] = a

    # 乙（双实例第二书）：不同重复句/图色/身份。
    b = build_epub(
        os.path.join(out, "probe-beta.epub"),
        book_id="66666666-7777-8888-9999-000000000000",
        title="探针乙：引擎表面实例", creator="PLAN-026 corpus",
        para_repeat=REPEAT_B, para_repeat2=None,
        para_repeat3_list=[REPEAT_B],
        img_rgb=(30, 60, 200), img_alt="探针乙深海图",
        note_target="ch3.xhtml#cross-note")
    produced["probe-beta.epub"] = b

    # 负例一：截断损伤（合法甲的尾巴截掉 96 字节 → 中央目录破坏）。
    mal = os.path.join(out, "negative-malformed.epub")
    with open(a, "rb") as f:
        data = f.read()
    with open(mal, "wb") as f:
        f.write(data[:-96])
    produced["negative-malformed.epub"] = mal

    # 负例二：超 profile（>1MiB，仍远小于 reader 产品 30MiB 线）。
    ov = os.path.join(out, "negative-oversize.epub")
    build_epub(
        ov, book_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        title="探针超额样本", creator="PLAN-026 corpus",
        para_repeat=REPEAT_A, para_repeat2=None, para_repeat3_list=[REPEAT_A],
        img_rgb=(90, 90, 90), img_alt="超额图", note_target="ch3.xhtml#cross-note")
    with zipfile.ZipFile(ov, "a", zipfile.ZIP_STORED) as z:
        z.writestr("OEBPS/images/filler.bin", b"\x00" * (2 * 1024 * 1024))
    produced["negative-oversize.epub"] = ov

    manifest = {}
    for name, p in produced.items():
        with open(p, "rb") as f:
            blob = f.read()
        manifest[name] = {"sha256": hashlib.sha256(blob).hexdigest(),
                          "size": len(blob), "path": os.path.abspath(p)}
    with open(os.path.join(out, "corpus-manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    for name, m in manifest.items():
        print(f"GEN {name} {m['size']}B sha256={m['sha256'][:16]}…")
    # profile 断言：合法书 ≤1MiB。
    for name in ("probe-alpha.epub", "probe-beta.epub"):
        assert manifest[name]["size"] <= 1024 * 1024, f"{name} 超出探针 profile"
    assert manifest["negative-oversize.epub"]["size"] > 1024 * 1024
    return 0


if __name__ == "__main__":
    sys.exit(main())
