#!/usr/bin/env python3
# corpus_oracle.py — PLAN-026 T-01 独立原文/出现序 oracle。
#
# 独立性纪律：本模块对「产出的 EPUB 文件」直接重读重算（zipfile + 标签剥取
# + 纯 Python PNG 解码），不复用 gen_corpus 的任何构建期状态；引擎/驱动两侧
# 只共享重复句常量。任何 locator 断言必须经本模块对受管原文重算后成立。
import hashlib
import io
import re
import struct
import zipfile
import zlib

RE_TAGS = re.compile(r"<[^>]+>")
RE_PARA = re.compile(r"<p(?:\s[^>]*)?>(.*?)</p>", re.S)


class BookScan:
    """一本书的独立扫描结果：章节段落原文 + 全书字符流。"""

    def __init__(self, path):
        self.path = path
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            opf_name = next(n for n in names if n.endswith(".opf"))
            opf = z.read(opf_name).decode("utf-8")
            opf_dir = opf_name.rsplit("/", 1)[0] + "/"
            spine = re.findall(r'<itemref idref="([^"]+)"', opf)
            idmap = dict(re.findall(r'<item id="([^"]+)" href="([^"]+)"', opf))
            self.chapters = []          # [{href, paras:[str]}]
            for sp in spine:
                href = idmap[sp]
                x = z.read(opf_dir + href).decode("utf-8")
                body = x.split("<body", 1)[1]
                paras = [RE_TAGS.sub("", m).strip() for m in RE_PARA.findall(body)]
                paras = [p for p in paras if p]
                self.chapters.append({"href": href, "paras": paras})
            self.image = {"href": "images/probe.png"}
            blob = z.read(opf_dir + "images/probe.png")
            self.image["sha256"] = hashlib.sha256(blob).hexdigest()
            self.image["size"] = len(blob)
            self.image["pixels"] = _png_corners(blob)
        # 全书（按 spine 阅读序）段落流：[(chapter_href, para_idx, text)]
        self.para_stream = []
        for ch in self.chapters:
            for i, p in enumerate(ch["paras"]):
                self.para_stream.append((ch["href"], i, p))

    # ── 出现序 oracle ──
    def find_sentence(self, sentence):
        """全书按阅读序返回每处出现：{chapter, para_index, offset_in_para}。"""
        hits = []
        for href, i, text in self.para_stream:
            start = 0
            while True:
                off = text.find(sentence, start)
                if off < 0:
                    break
                hits.append({"chapter": href, "para_index": i, "offset_in_para": off})
                start = off + 1
        return hits

    def expected_occurrence(self, sentence, n):
        """第 n 次出现（1-based）的期望锚；不存在则 None。"""
        hits = self.find_sentence(sentence)
        return hits[n - 1] if 0 < n <= len(hits) else None

    def sentence_occurrence_count(self, sentence):
        return len(self.find_sentence(sentence))

    # ── quote 校验（消费端身份核验的 oracle 口径）──
    def verify_quote(self, quote, occurrence):
        hits = self.find_sentence(quote)
        if not hits:
            return {"ok": False, "reason": "quote_not_found", "occurrences": 0}
        if not 0 < occurrence <= len(hits):
            return {"ok": False, "reason": "occurrence_out_of_range",
                    "occurrences": len(hits)}
        return {"ok": True, "position": hits[occurrence - 1],
                "occurrences": len(hits)}


def _png_corners(blob):
    """纯 Python 解 PNG 左上/右下角像素（探针图均为 8bit RGB 单 IDAT）。"""
    if blob[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a png")
    pos, idat, ihdr = 8, b"", None
    while pos < len(blob):
        ln = struct.unpack(">I", blob[pos:pos + 4])[0]
        typ = blob[pos + 4:pos + 8]
        data = blob[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", data)
        elif typ == b"IDAT":
            idat += data
        pos += 12 + ln
    w, h, depth, ctype = ihdr[0], ihdr[1], ihdr[2], ihdr[3]
    assert depth == 8 and ctype == 2, "probe png profile"
    raw = zlib.decompress(idat)
    stride = w * 3

    def pixel(x, y):
        off = y * (stride + 1) + 1 + x * 3
        assert raw[y * (stride + 1)] == 0, "filter must be 0 (solid png)"
        return (raw[off], raw[off + 1], raw[off + 2])

    return {"top_left": pixel(0, 0), "bottom_right": pixel(w - 1, h - 1),
            "w": w, "h": h}
