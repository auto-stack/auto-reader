#!/usr/bin/env python3
"""gen_product_corpus.py — READER-007 产品语料生成器（T-02 冻结）。

用法：python gen_product_corpus.py --out-dir <隔离目录>

产出（确定性可重算 hash）：
  product-alpha.epub    真实风格 10 章 EPUB：标题/段落/列表/简单表格/代码块、
                        2 PNG、nav 目录、脚注/跨章链接、重复句甲(全书3次/第1章2次)、
                        重复句乙(跨章2次)、跨段引文（段尾+下段首）、长章 ch3(~1.5MiB)、
                        emoji/多字节。
  product-beta.epub     变体书（双实例/串书隔离用；重复句乙 2 次）。
  negative-malformed.epub  坏 container（结构性拒绝负例）。
  corpus-manifest.json  每文件 sha256 + 预期（章标题/重复句出现位次/跨段/图片数）。

oracle 与门侧唯一耦合点是本文件的冻结常量（REPEAT_A/B、CROSS_PARA*）。
"""
import argparse
import hashlib
import json
import os
import struct
import zipfile
import zlib

# ── 冻结常量（与 verify_epub_product.py 一致） ──
REPEAT_A = "产品重复句甲🦊：琥珀色的狐狸跃过懒狗时携带三枚星形饼干，并轻声数到十七✨，随后沿对角线穿过整段跨度以便在窄栏里真实换行。"
REPEAT_B = "产品重复句乙🐙：深蓝色的章鱼在暗礁之间整理十二枚贝壳🫧，把第七枚留给回声，然后沉入更深的走廊。"
CROSS_PARA = "跨段引文甲：这段文字的上半句落在段落末尾，"
CROSS_PARA2 = "下半句则跨进下一段的开头继续，形成真实跨段范围。"

FILLER = [
    "页边留白处有一行淡淡的批注，墨迹已经泛褐，像是多年以前某位读者留下的脚印。",
    "雨点敲在遮棚上，节奏忽快忽慢；桌上那盏油灯把两个影子投在墙上，一个在写字，一个在打盹。",
    "📜 远行的行囊里只有半块干粮、一枚指南针和一封没有署名的信。信封上的火漆完好如初。",
    "风从山谷另一头吹来，带来潮湿的苔藓气味，也带来远处钟楼的第七次报时。",
    "暮色四合时，渡口的灯笼次第亮起，船夫解开缆绳，把这一夜交给流水。",
]
CH_TITLES = ["山月", "潮声", "林径", "驿路", "灯影", "石桥", "雾海", "檐雨",
             "纸鸢", "归途"]


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


def chapter_xhtml(n, body):
    return (f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            f"<html xmlns=\"http://www.w3.org/1999/xhtml\" xmlns:epub=\"http://www.idpf.org/2007/ops\" xml:lang=\"zh\">\n"
            f"<head><title>第{n}章 {CH_TITLES[n-1]}</title>"
            f"<link rel=\"stylesheet\" type=\"text/css\" href=\"style.css\"/></head>\n"
            f"<body>\n{body}</body></html>\n")


def build_alpha():
    ch = []
    # ch1：标题/段落/重复句甲×2/列表/表格/代码块/图1
    b1 = (f"<h1 id=\"ch1\">第一章 {CH_TITLES[0]}</h1>\n"
          f"<p>山月不知心底事，水风空落眼前花。这是全书的第一段正文，用来承载书架导入后的首屏与目录跳转目标。</p>\n"
          f"<p>{REPEAT_A}</p>\n"
          f"<p>这一段与上一段之间隔着空行，形成第二个自然段。重复句甲的第一次出现就在本段。</p>\n"
          f"<ul><li>列表项一：星形饼干的配方。</li><li>列表项二：狐狸的步幅记录。</li><li>列表项三：十七的来历。</li></ul>\n"
          f"<p>{REPEAT_A}</p>\n"
          f"<p>重复句甲第二次出现在本章；全书第三次出现在第二章。</p>\n"
          f"<table><thead><tr><th>条目</th><th>数值</th></tr></thead>"
          f"<tbody><tr><td>琥珀</td><td>3</td></tr><tr><td>饼干</td><td>17</td></tr></tbody></table>\n"
          f"<pre><code>const step = 17;\nconsole.log('✨' + step);</code></pre>\n"
          f"<p><img src=\"images/img1.png\" alt=\"山月插图\"/></p>\n")
    ch.append(chapter_xhtml(1, b1))
    # ch2：重复句甲（第3次）、脚注、跨章链接
    b2 = (f"<h1 id=\"ch2\">第二章 {CH_TITLES[1]}</h1>\n"
          f"<p>潮声由远及近，岸边的石子被反复淘洗。本章承载跨章链接与脚注往返。</p>\n"
          f"<p>{REPEAT_A}</p>\n"
          f"<p>这是重复句甲在全书第三次、也是最后一次出现。</p>\n"
          f"<p>跨章链接示例：参见<a href=\"ch3.xhtml#sec-3\">第三章 林径</a>。</p>\n"
          f"<p>脚注示例<sup><a id=\"fnref1\" href=\"#fn1\">[1]</a></sup>：正文引用见章尾。</p>\n"
          f"<p id=\"fn1\" epub:type=\"footnote\">脚注一：琥珀色狐狸的三枚饼干分别来自三家不同的铺子。</p>\n")
    ch.append(chapter_xhtml(2, b2))
    # ch3：长章（~1.5MiB）+ 跨段引文 + 图2 + 锚点
    parts = [f"<h1 id=\"ch3\">第三章 {CH_TITLES[2]}</h1>\n",
             f"<p id=\"sec-3\">林径在雨后格外潮湿，苔藓覆盖了石板缝。本段是跨章链接的落点。</p>\n"]
    for i in range(12000):
        parts.append(f"<p>{FILLER[i % len(FILLER)]}（第{i + 1}行）</p>\n")
    parts.append(f"<p>{CROSS_PARA}</p>\n")
    parts.append(f"<p>{CROSS_PARA2}</p>\n")
    parts.append(f"<p><img src=\"images/img2.png\" alt=\"林径插图\"/></p>\n")
    ch.append(chapter_xhtml(3, "".join(parts)))
    # ch4..ch10：重复句乙 ch4（第1次）/ ch9（第2次），其余填充
    for n in range(4, 11):
        body = f"<h1 id=\"ch{n}\">第{n}章 {CH_TITLES[n-1]}</h1>\n"
        if n == 4:
            body += (f"<p>{REPEAT_B}</p>\n"
                     f"<p>重复句乙第一次出现，位于第四章。</p>\n")
        elif n == 9:
            body += (f"<p>{REPEAT_B}</p>\n"
                     f"<p>重复句乙第二次出现，位于第九章——与第四章形成跨章重复。</p>\n")
        for i in range(6):
            body += f"<p>{FILLER[(n + i) % len(FILLER)]}（第{n}章第{i + 1}行）</p>\n"
        ch.append(chapter_xhtml(n, body))
    return ch


def build_beta():
    b1 = (f"<h1 id=\"b1\">甲卷 潮汐</h1>\n"
          f"<p>这是变体书的第一章，内容与 alpha 全不相同，用于双实例/串书隔离。</p>\n"
          f"<p>{REPEAT_B}</p>\n"
          f"<p>重复句乙在变体书中第一次出现。</p>\n")
    b2 = (f"<h1 id=\"b2\">乙卷 暗礁</h1>\n"
          f"<p>变体书第二章。</p>\n"
          f"<p>{REPEAT_B}</p>\n"
          f"<p>重复句乙在变体书中第二次出现。</p>\n")
    return [chapter_xhtml(1, b1), chapter_xhtml(2, b2)]


def opf(book_id, title, creator, chapters, images):
    items = ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
             '<item id="css" href="style.css" media-type="text/css"/>']
    for i in range(1, len(chapters) + 1):
        items.append(f'<item id="c{i}" href="ch{i}.xhtml" media-type="application/xhtml+xml"/>')
    for j in range(1, len(images) + 1):
        items.append(f'<item id="img{j}" href="images/img{j}.png" media-type="image/png"/>')
    spine = "".join(f'<itemref idref="c{i}"/>' for i in range(1, len(chapters) + 1))
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="zh">\n'
            f'  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
            f'    <dc:identifier id="bookid">urn:uuid:{book_id}</dc:identifier>\n'
            f'    <dc:title>{esc(title)}</dc:title>\n'
            f'    <dc:language>zh</dc:language>\n'
            f'    <dc:creator>{esc(creator)}</dc:creator>\n'
            f'    <meta property="dcterms:modified">2026-11-03T00:00:00Z</meta>\n'
            f'  </metadata>\n'
            f'  <manifest>\n    ' + "\n    ".join(items) + '\n  </manifest>\n'
            f'  <spine>\n    ' + spine + '\n  </spine>\n</package>\n')


def nav(title, chapters):
    lis = "".join(f'<li><a href="ch{i + 1}.xhtml">{i + 1} {CH_TITLES[i]}</a></li>'
                  for i in range(len(chapters)))
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh">\n'
            f'<head><title>{esc(title)} 目录</title></head>\n'
            f'<body epub:type="frontmatter"><nav epub:type="toc"><h1>目录</h1><ol>{lis}</ol></nav></body>\n'
            f'</html>\n')


STYLE = "body{font-family:serif;line-height:1.7}p{margin:0.6em 0}"


def write_epub(path, chapters, images, book_id, title, creator):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo("mimetype", date_time=(2026, 11, 3, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_STORED
        z.writestr(zi, "application/epub+zip")
        for name, data in [
            ("META-INF/container.xml", container_xml()),
            ("OEBPS/content.opf", opf(book_id, title, creator, chapters, images)),
            ("OEBPS/nav.xhtml", nav(title, chapters)),
            ("OEBPS/style.css", STYLE),
        ]:
            zi = zipfile.ZipInfo(name, date_time=(2026, 11, 3, 0, 0, 0))
            z.writestr(zi, data)
        for i, ch in enumerate(chapters, 1):
            zi = zipfile.ZipInfo(f"OEBPS/ch{i}.xhtml", date_time=(2026, 11, 3, 0, 0, 0))
            z.writestr(zi, ch)
        for j, blob in enumerate(images, 1):
            zi = zipfile.ZipInfo(f"OEBPS/images/img{j}.png", date_time=(2026, 11, 3, 0, 0, 0))
            z.writestr(zi, blob)


def write_malformed(path):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo("mimetype", date_time=(2026, 11, 3, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_STORED
        z.writestr(zi, "application/epub+zip")
        zi = zipfile.ZipInfo("META-INF/container.xml", date_time=(2026, 11, 3, 0, 0, 0))
        z.writestr(zi, '<?xml version="1.0"?><container version="1.0"><broken/></container>')
        zi = zipfile.ZipInfo("OEBPS/content.opf", date_time=(2026, 11, 3, 0, 0, 0))
        z.writestr(zi, "<not-an-opf/>")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    imgs = [png_bytes(64, 48, (220, 120, 90)), png_bytes(48, 64, (90, 140, 110))]
    alpha_ch = build_alpha()
    beta_ch = build_beta()

    a_path = os.path.join(args.out_dir, "product-alpha.epub")
    b_path = os.path.join(args.out_dir, "product-beta.epub")
    m_path = os.path.join(args.out_dir, "negative-malformed.epub")
    write_epub(a_path, alpha_ch, imgs, "aaaaaaaa-bbbb-cccc-dddd-000000000001",
               "山月与潮声", "产品语料生成器")
    write_epub(b_path, beta_ch, imgs[:1], "bbbbbbbb-bbbb-cccc-dddd-000000000002",
               "变体书：暗礁", "产品语料生成器")
    write_malformed(m_path)

    manifest = {
        "schema_version": 1,
        "engine_revision": "foliate-js@3d7941954a98b136316a795e8200d60c9643b141",
        "files": {
            "product-alpha.epub": {
                "sha256": sha256(a_path), "chapters": 10,
                "repeat_a_occurrences_book": 3, "repeat_a_in_ch1": 2,
                "repeat_b_occurrences_book": 2,
                "cross_para_text": CROSS_PARA + CROSS_PARA2,
                "images": 2, "long_chapter": 3,
                "titles": [f"{i + 1} {CH_TITLES[i]}" for i in range(10)],
            },
            "product-beta.epub": {
                "sha256": sha256(b_path), "chapters": 2,
                "repeat_b_occurrences_book": 2, "images": 1,
            },
            "negative-malformed.epub": {"sha256": sha256(m_path)},
        },
    }
    with open(os.path.join(args.out_dir, "corpus-manifest.json"), "w",
              encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
