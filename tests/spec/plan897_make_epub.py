#!/usr/bin/env python3
# plan897_make_epub.py — READER-003 T-01 EPUB 导入夹具生成（确定性内容）。
# 条目：mimetype(stored) container.xml OEBPS/content.opf(nav+c1+c2+img1)
# OEBPS/nav.xhtml OEBPS/ch1.xhtml OEBPS/ch2.xhtml OEBPS/images/cover.png。
import os, zipfile

base = os.path.join(os.environ.get("TEMP", "/tmp"), "plan897")
os.makedirs(base, exist_ok=True)
ep = os.path.join(base, "book1.epub")
container = ('<?xml version="1.0"?><container version="1.0" '
             'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
             '<rootfile full-path="OEBPS/content.opf" '
             'media-type="application/oebps-package+xml"/></rootfiles></container>')
opf = ('<?xml version="1.0" encoding="UTF-8"?>\n'
       '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">\n'
       '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>山月小说</dc:title>'
       '<dc:creator>测试作者</dc:creator></metadata>\n<manifest>\n'
       '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>\n'
       '<item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/>\n'
       '<item id="c2" href="ch2.xhtml" media-type="application/xhtml+xml"/>\n'
       '<item id="img1" href="images/cover.png" media-type="image/png"/>\n'
       '</manifest>\n<spine><itemref idref="c1"/><itemref idref="c2"/></spine>\n</package>')
nav = ('<?xml version="1.0" encoding="UTF-8"?>\n'
       '<html xmlns="http://www.w3.org/1999/xhtml" '
       'xmlns:epub="http://www.idpf.org/2007/ops"><body>\n<nav epub:type="toc"><ol>\n'
       '<li><a href="ch1.xhtml">第一章 山月</a></li>\n'
       '<li><a href="ch2.xhtml">第二章 心底事</a></li>\n'
       '</ol></nav></body></html>')
ch1 = ('<?xml version="1.0" encoding="UTF-8"?>\n'
       '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>c1</title></head><body>\n'
       '<h1>第一章 山月</h1>\n<p>山月不知心底事。</p><p>水调歌头，明月几时有。</p>\n'
       '<p><img src="images/cover.png" alt="cover"/></p>\n</body></html>')
ch2 = ('<?xml version="1.0" encoding="UTF-8"?>\n'
       '<html xmlns="http://www.w3.org/1999/xhtml"><body>\n'
       '<h1>第二章 心底事</h1>\n<p>第二 chapter 内容。<a href="ch1.xhtml">回第一章</a></p>\n'
       '</body></html>')
cover = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A] + [(i % 251) for i in range(64)])
with zipfile.ZipFile(ep, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)
    z.writestr("META-INF/container.xml", container)
    z.writestr("OEBPS/content.opf", opf)
    z.writestr("OEBPS/nav.xhtml", nav)
    z.writestr("OEBPS/ch1.xhtml", ch1)
    z.writestr("OEBPS/ch2.xhtml", ch2)
    z.writestr("OEBPS/images/cover.png", cover)
print(ep)
