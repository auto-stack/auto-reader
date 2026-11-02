#!/usr/bin/env python3
# probe_books.py — READER-005 standalone 探针书生成（确定性最小 EPUB3）。
# R-02/R-03 UI oracle 的夹具源：verify_standalone.py 与交互调试共用。
# 生成物进隔离数据根（tests/fixtures 之外的运行时目录），不入库。
import os
import zipfile

_CONTAINER = ('<?xml version="1.0"?><container version="1.0" '
              'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
              '<rootfile full-path="OEBPS/content.opf" '
              'media-type="application/oebps-package+xml"/></rootfiles></container>')


def _png(w, h, rgb):
    """确定性可解码 PNG（真字节，8bit RGB）。"""
    import struct
    import zlib
    sig = b'\x89PNG\r\n\x1a\n'

    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)

    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    raw = b''
    for _ in range(h):
        raw += b'\x00'
        for _ in range(w):
            raw += bytes(rgb)
    return sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')


RED = _png(8, 8, (200, 30, 30))
BLUE = _png(8, 8, (30, 30, 200))


def _write(path, opf_title, files):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype', 'application/epub+zip', zipfile.ZIP_STORED)
        for name, data in files:
            z.writestr(name, data)
    return path


def probe_images(out_dir, overwrite=True):
    """R-02：双扁平碰撞 + 含空格名 + 不支持类型。标题 Probe Book 2。
    overwrite=False：文件已存在时不重写（R-06(vm) 反例夹具副本注入）。"""
    path = os.path.join(out_dir, 'probe-images.epub')
    if not overwrite and os.path.exists(path):
        return path
    opf = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Probe Book 2</dc:title>'
           '<dc:creator>T02</dc:creator></metadata>'
           '<manifest>'
           '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
           '<item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/>'
           '<item id="i1" href="a/b_c.png" media-type="image/png"/>'
           '<item id="i2" href="a_b/c.png" media-type="image/png"/>'
           '<item id="i3" href="img with space.png" media-type="image/png"/>'
           '<item id="i4" href="bad.svg" media-type="image/svg+xml"/>'
           '</manifest>'
           '<spine><itemref idref="c1"/></spine></package>')
    nav = ('<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml" '
           'xmlns:epub="http://www.idpf.org/2007/ops"><body><nav epub:type="toc"><ol>'
           '<li><a href="ch1.xhtml">C1</a></li></ol></nav></body></html>')
    ch1 = ('<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml"><body>'
           '<h1>C1</h1>'
           '<p>Red first.</p><p><img src="a/b_c.png" alt="red"/></p>'
           '<p>Blue second.</p><p><img src="a_b/c.png" alt="blue"/></p>'
           '<p>Space third.</p><p><img src="img with space.png" alt="space"/></p>'
           '<p>SVG fourth (unsupported).</p><p><img src="bad.svg" alt="svg"/></p>'
           '</body></html>')
    return _write(path, 'Probe Book 2', [
        ('META-INF/container.xml', _CONTAINER),
        ('OEBPS/content.opf', opf), ('OEBPS/nav.xhtml', nav), ('OEBPS/ch1.xhtml', ch1),
        ('OEBPS/a/b_c.png', RED), ('OEBPS/a_b/c.png', BLUE),
        ('OEBPS/img with space.png', RED), ('OEBPS/bad.svg', '<svg xmlns="http://www.w3.org/2000/svg"/>'),
    ])


def probe_links(out_dir, overwrite=True):
    """R-03：同章锚/跨章 fragment/子目录相对基准/诚实拒绝面（外部、缺章、
    未知 fragment）。标题 Probe Book 4。
    overwrite=False：文件已存在时不重写（R-06(vm) 反例夹具副本注入）。"""
    path = os.path.join(out_dir, 'probe-links.epub')
    if not overwrite and os.path.exists(path):
        return path
    opf = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Probe Book 4</dc:title>'
           '<dc:creator>T03</dc:creator></metadata>'
           '<manifest>'
           '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
           '<item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/>'
           '<item id="c2" href="ch2.xhtml" media-type="application/xhtml+xml"/>'
           '<item id="c3" href="sub/ch3.xhtml" media-type="application/xhtml+xml"/>'
           '</manifest>'
           '<spine><itemref idref="c1"/><itemref idref="c2"/><itemref idref="c3"/></spine></package>')
    nav = ('<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml" '
           'xmlns:epub="http://www.idpf.org/2007/ops"><body><nav epub:type="toc"><ol>'
           '<li><a href="ch1.xhtml">第一章</a></li><li><a href="ch2.xhtml">第二章</a></li>'
           '<li><a href="sub/ch3.xhtml">第三章</a></li></ol></nav></body></html>')
    ch1 = ('<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml"><body>'
           '<h1>第一章</h1>'
           '<p>脚注引用<a href="#fn1">[1]</a>在此。</p>'
           '<p>跨章引用<a href="ch2.xhtml#dup">到第二章重复段</a>在此。</p>'
           '<p>子目录引用<a href="sub/ch3.xhtml#target">到第三章</a>在此。</p>'
           '<p>同章锚<a href="#para-x">到本章末段</a>在此。</p>'
           '<p>坏外链<a href="https://example.net/x">外部</a>与<a href="ch9.xhtml#nope">缺章</a>与'
           '<a href="#no-such-frag">坏锚</a>。</p>'
           '<p id="para-x">本章末段（锚目标）。</p>'
           '</body></html>')
    ch2 = ('<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml"><body>'
           '<h1>第二章</h1>'
           '<p>第二章开头段。</p>'
           '<p id="dup">重复段落文本目标（两章同 id 名）。</p>'
           '<p>第二章末段。</p>'
           '</body></html>')
    ch3 = ('<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml"><body>'
           '<h1>第三章</h1>'
           '<p id="target">第三章目标段（子目录锚）。</p>'
           '<p>回引第一章<a href="../ch1.xhtml#fn1">脚注一</a>在此。</p>'
           '</body></html>')
    return _write(path, 'Probe Book 4', [
        ('META-INF/container.xml', _CONTAINER),
        ('OEBPS/content.opf', opf), ('OEBPS/nav.xhtml', nav),
        ('OEBPS/ch1.xhtml', ch1), ('OEBPS/ch2.xhtml', ch2), ('OEBPS/sub/ch3.xhtml', ch3),
    ])


def generate_all(out_dir, overwrite=True):
    """生成全部探针书 → [(path, title, author), ...]（导入清单）。
    overwrite=False：已存在的夹具不重写——R-06(vm) 反例以此把毁损
    夹具副本原样交给驱动导入（驱动自管 out-dir，默认重生成会还原
    变异使负控失效，026 R-06vm rc=0 根因）。"""
    os.makedirs(out_dir, exist_ok=True)
    return [
        (probe_images(out_dir, overwrite), 'Probe Book 2', 'T02'),
        (probe_links(out_dir, overwrite), 'Probe Book 4', 'T03'),
    ]


if __name__ == '__main__':
    import sys
    for p, t, a in generate_all(sys.argv[1] if len(sys.argv) > 1 else '.'):
        print(p, '->', t)
