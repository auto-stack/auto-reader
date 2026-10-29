#!/usr/bin/env python3
"""t26_deep_10mib_verify.py — READER-001 T-26 10MiB 成功导入 deep oracle（r8）。

覆盖（V-21 成功门）：
  1. 10MiB TXT 导入 ok；受管副本 SHA256 == 原件。
  2. 全章逐字（1..=2001 章，title 精确 + body 精确相等——非前缀抽样）。
  3. 冷重启（杀服务→同目录重启）后全章复扫逐字 + 书目记录一致。
  4. 阅读状态跨重启持久（chapter 1000 写入→重启→读回一致）。
  5. 低预算负例（缺省 10M 预算，独立实例）：导入显式失败且书库不变
     （错误保护证据；成功路径由 1-4 承担）。

前置：17825 空闲；`auto` 在 PATH。驱动自管服务实例（`auto service --server vm`，
无 UI），与 run_fresh_server.sh 同一预算 profile。
注意：781 交付的 test_reader_import_budget.py 在 auto-man CLI 下实例无法就绪
（登记 N-r8-4），本驱动为等价 deep oracle（业务终审口径）。
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid

BASE = "http://127.0.0.1:17825"
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PARA = "山月不知心底事，水风空落眼前花，摇曳碧云斜。江上柳如烟，雁飞残月天。\n"
FAILS = []


def check(cond, name, detail=""):
    if cond:
        print("PASS " + name, flush=True)
    else:
        FAILS.append(name)
        print("FAIL " + name + (" :: " + str(detail)[:200] if detail else ""), flush=True)


def curl(method, path, body=None, tries=4, timeout=180):
    for _ in range(tries):
        cmd = ["curl", "-s", "-m", str(timeout), "-X", method]
        if body is not None:
            cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(body, ensure_ascii=True)]
        cmd.append(BASE + path)
        out = subprocess.run(cmd, capture_output=True, encoding="utf-8").stdout
        if out.strip():
            v = json.loads(out)
            if isinstance(v, str) and v:
                try:
                    v = json.loads(v)
                except Exception:
                    pass
            return v
        time.sleep(0.5)
    return {"__empty__": True}


def gen_10mib(path, run):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"run:{run}\n" + PARA * 100)
        for c in range(1, 2001):
            f.write(f"第{c}章 长卷\n")
            f.write(PARA * 80)
    return path


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def expected_chapter(num):
    # 章节体合同 = 首行拆题 + trim（PLAN-781 SD-11 交付语义）——oracle 对
    # trim 后内容做全字相等（内部逐字不变即逐字）
    if num == 1:
        return "开篇", (f"run:{RUN}\n" + PARA * 100).rstrip("\n")
    return f"第{num - 1}章 长卷", (PARA * 80).rstrip("\n")


class Service:
    def __init__(self, data_dir, budget=True):
        self.data_dir = data_dir
        self.budget = budget
        self.proc = None

    def start(self):
        env = dict(os.environ, AUTO_READER_DATA=self.data_dir,
                   AUTO_HTTP_REQUEST_TIMEOUT_MS="300000")
        if self.budget:
            env["AUTO_HTTP_STEP_BUDGET"] = "1000000000"
        else:
            env.pop("AUTO_HTTP_STEP_BUDGET", None)
        self.proc = subprocess.Popen(
            [os.environ.get("AUTO_BIN", r"D:\autostack\auto-man\target\debug\auto.exe"),
             "run", "--server=vm", "-B", "17825"],
            cwd=REPO, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def wait_ready(self, deadline=60):
        t0 = time.monotonic()
        while time.monotonic() - t0 < deadline:
            if self.proc.poll() is not None:
                return False
            r = curl("GET", "/api/library/books", tries=1, timeout=5)
            if r != {"__empty__": True}:
                return True
            time.sleep(1.5)
        return False

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
        self.proc = None


RUN = uuid.uuid4().hex[:8]


def scan_all(bid, tag):
    bad = []
    for num in range(1, 2002):
        c = curl("GET", f"/api/library/chapter?book_id={bid}&number={num}", tries=2)
        exp_title, exp_body = expected_chapter(num)
        if str(c.get("title", "")) != exp_title:
            bad.append((num, "title", str(c.get("title", ""))[:40]))
        if str(c.get("body", "")) != exp_body:
            bad.append((num, "body", str(c.get("body", ""))[:40]))
        if len(bad) >= 5:
            break
    check(not bad, f"10MiB {tag} all 2001 chapters verbatim",
          bad[:3] if bad else "ok")


def main():
    data_dir = os.path.join(os.environ["TEMP"], f"reader001-review-t26deep-{RUN}")
    os.makedirs(data_dir, exist_ok=True)
    fx = gen_10mib(os.path.join(data_dir, f"deep-10mib-{RUN}.txt"), RUN)
    check(os.path.getsize(fx) >= 10 * 1024 * 1024, "10MiB fixture generated",
          os.path.getsize(fx))
    src_sha = sha256_file(fx)

    # ── 腿 1+2+3+4：预算 profile 下成功导入 + deep oracle + 冷重启 ──
    svc = Service(data_dir, budget=True)
    svc.start()
    booted = svc.wait_ready()
    booted = svc.wait_ready()
    check(booted, "service boots", f"poll={booted} proc={svc.proc.poll() if svc.proc else None}")
    o = curl("POST", "/api/library/import", {"path": fx, "author": "deep", "force": False},
             timeout=300)
    check(o.get("code") == "ok", "10MiB import ok", o)
    bid = o.get("book_id", "")
    rec = next((x for x in curl("GET", "/api/library/books").get("books", [])
                if x.get("book_id") == bid), {})
    check(rec.get("chapter_count") == 2001, "chapters=2001", rec.get("chapter_count"))
    managed = rec.get("managed_path", "")
    if managed and os.path.exists(managed):
        check(sha256_file(managed) == src_sha, "managed copy SHA256 == source", managed)
    else:
        check(False, "managed copy SHA256 == source", f"managed_path={managed!r}")

    t0 = time.monotonic()
    scan_all(bid, "pre-restart")
    print(f"# pre-restart scan took {time.monotonic() - t0:.0f}s", flush=True)

    # 阅读状态：chapter 1000 ¶5
    w = curl("POST", "/api/library/progress", {
        "book_id": bid,
        "payload": json.dumps({"book_id": bid, "chapter_number": 1000, "paragraph_index": 5,
                               "para_hash": "sig1:1:1", "font_size": "medium",
                               "line_height": "comfy", "updated_at": 0}),
        "para_text": PARA.strip()})
    check(w.get("ok") is True, "progress saved (ch1000)", w)

    # ── 冷重启 ──
    svc.stop()
    time.sleep(2)
    svc = Service(data_dir, budget=True)
    svc.start()
    check(svc.wait_ready() is True, "cold restart boots")
    rec2 = next((x for x in curl("GET", "/api/library/books").get("books", [])
                 if x.get("book_id") == bid), {})
    check(rec2.get("title") == rec.get("title") and
          rec2.get("chapter_count") == 2001, "library record survives restart", rec2)
    g = curl("GET", f"/api/library/progress?book_id={bid}")
    if isinstance(g, str):
        try:
            g = json.loads(g)
        except Exception:
            pass
    if not isinstance(g, dict):
        g = {}
    check(g.get("chapter_number") == 1000 and g.get("paragraph_index") == 5,
          "reading state survives restart", g)
    scan_all(bid, "cold-restart")

    # ── 腿 5：低预算负例（独立实例，缺省 10M） ──
    svc.stop()
    time.sleep(2)
    svc = Service(data_dir, budget=False)
    svc.start()
    check(svc.wait_ready() is True, "low-budget service boots")
    pre = {x.get("book_id") for x in curl("GET", "/api/library/books").get("books", [])}
    o2 = curl("POST", "/api/library/import", {"path": gen_10mib(
        os.path.join(data_dir, f"deep-10mib-neg-{RUN}.txt"), RUN + "neg"),
        "author": "deep", "force": False}, timeout=300)
    explicit = (o2.get("error") is not None) or (o2.get("code") in
                                                 ("io_error", "decode_error", "budget", "invalid_path")) or \
               ("预算" in str(o2.get("message", "")) or "budget" in str(o2.get("message", "")).lower())
    post = {x.get("book_id") for x in curl("GET", "/api/library/books").get("books", [])}
    check(explicit, "low-budget import rejected with explicit error", o2)
    check(post == pre, "low-budget attempt leaves library unchanged",
          {"pre": len(pre), "post": len(post)})

    svc.stop()
    print(json.dumps({"summary": {"fails": len(FAILS)}, "data_dir": data_dir}), flush=True)
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
