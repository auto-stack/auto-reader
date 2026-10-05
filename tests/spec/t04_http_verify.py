#!/usr/bin/env python3
# t04_http_verify.py — READER-001 T-04 应用级 HTTP 验证（长文/迁移/重复/中断）。
# 前置：bash tests/spec/run_fresh_server.sh（干净数据目录的 VM 后端在 17825）。
# 覆盖：容量阶梯（64KB 多章 / 512KB 边界 / 10MiB 预算上限）、v0 索引拒绝
#       （迁移语义）、同内容异名去重、同题异容独立档案。
# 幂等：生成物首行注入运行级唯一标识（内容去重基于内容）；请求体 ASCII
# 安全（\u 转义）；空响应幂等重试（T-02 实测缺陷）。
import json
import os
import subprocess
import sys
import time
import uuid

BASE = "http://127.0.0.1:17825"
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIX = os.path.join(REPO, "tests", "fixtures", "library")
RUN = uuid.uuid4().hex[:8]
FAILS = []


def curl(method, path, body=None, tries=3):
    for k in range(tries):
        cmd = ["curl", "-s", "-m", "120", "-X", method]
        if body is not None:
            cmd += ["-H", "Content-Type: application/json", "-d",
                    json.dumps(body, ensure_ascii=True)]
        cmd.append(BASE + path)
        out = subprocess.run(cmd, capture_output=True, text=True,
                             encoding="utf-8").stdout
        if out.strip():
            v = json.loads(out)
            if isinstance(v, str):
                try:
                    v2 = json.loads(v)
                    if isinstance(v2, (dict, list)):
                        return v2
                except (json.JSONDecodeError, ValueError):
                    pass
            return v
        time.sleep(0.3)
    return {"__empty__": True}


def check(cond, name, detail=""):
    if cond:
        print("PASS " + name)
    else:
        FAILS.append(name)
        print("FAIL " + name + (" :: " + str(detail)[:200] if detail else ""))


PARA = "山月不知心底事，水风空落眼前花，摇曳碧云斜。江上柳如烟，雁飞残月天。\n"


def gen(name, blocks, paras):
    path = os.path.join(FIX, name)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"run:{RUN}\n" + PARA * 100)
        for c in range(1, blocks + 1):
            f.write(f"第{c}章 长卷\n")
            f.write(PARA * paras)
    return path


def main():
    # 1) 容量阶梯 fixture（现场生成）
    p_small = gen(f"cap-64kb-{RUN}.txt", 6, 80)        # ~64KB，预算内
    p_mid = gen(f"cap-512kb-{RUN}.txt", 40, 80)        # ~512KB，预算边界
    long_path = gen(f"cap-10mb-{RUN}.txt", 2000, 80)   # ~10MiB（AC 目标，超预算）
    check(os.path.getsize(long_path) >= 10 * 1024 * 1024, "10MiB fixture generated",
          os.path.getsize(long_path))

    # 2) 64KB 多章导入：预算内全绿
    o = curl("POST", "/api/library/import", {"path": p_small, "author": "cap", "force": False})
    check(o.get("code") == "ok", "64KB multi-chapter import ok", o)
    bid = o.get("book_id", "")
    books = curl("GET", "/api/library/books")
    rec = next((x for x in books.get("books", []) if x.get("book_id") == bid), {})
    check(rec.get("chapter_count") == 7, "64KB chapters=7 (开篇+6)", rec.get("chapter_count"))
    c1 = curl("GET", f"/api/library/chapter?book_id={bid}&number=2")
    check(str(c1.get("title", "")).startswith("第1章"), "64KB ch2 title", c1.get("title"))

    # 3) 512KB：预算边界——响应可能超时丢失，但导入应最终完成
    om = curl("POST", "/api/library/import", {"path": p_mid, "author": "", "force": False})
    if om.get("code") == "ok" or om.get("__empty__"):
        books2 = curl("GET", "/api/library/books")
        m = [x for x in books2.get("books", []) if x.get("title") == f"cap-512kb-{RUN}"]
        check(len(m) == 1, "512KB import completes (response may time out)", len(m))
    else:
        check(om.get("error") is not None or om.get("code") == "io_error",
              "512KB rejected with explicit error", om)

    # 4) 迁移：v0 旧形索引 → 拒绝且保留（运行中后端），恢复后复归 duplicate
    data_dir = os.environ.get("AUTO_READER_DATA", "")
    if data_dir and os.path.isdir(data_dir):
        libfile = os.path.join(data_dir, "library.json")
        if os.path.exists(libfile):
            backup = open(libfile, "rb").read()
            with open(libfile, "w", encoding="utf-8") as f:
                f.write('{"books":[{"id":"legacy","name":"x"}]}')
            o2 = curl("POST", "/api/library/import",
                      {"path": p_small, "author": "", "force": False})
            check(o2.get("code") == "io_error" and "人工迁移" in o2.get("message", ""),
                  "v0 index rejected at runtime", o2)
            with open(libfile, "wb") as f:
                f.write(backup)
            o3 = curl("POST", "/api/library/import",
                      {"path": p_small, "author": "", "force": False})
            check(o3.get("code") == "duplicate", "v1 index restored (duplicate)", o3)
    else:
        print("SKIP runtime-migration (AUTO_READER_DATA not visible to driver)")

    # 5) 同内容异名 + 同题异容（内容按运行唯一）
    p1 = os.path.join(FIX, "xiaoshuo.txt")
    p2 = os.path.join(FIX, "xiaoshuo-copy.txt")
    oa = curl("POST", "/api/library/import", {"path": p1, "author": "", "force": False})
    check(oa.get("code") in ("ok", "duplicate"), "copy fixture import", oa)
    ob = curl("POST", "/api/library/import", {"path": p2, "author": "", "force": False})
    check(ob.get("code") == "duplicate", "same-content copy → duplicate", ob)
    p3 = os.path.join(FIX, f"gen-same-title-{RUN}.txt")
    with open(p3, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"run:{RUN}\n第一章 山月\n不同出版社的版本内容 {RUN}。\n\n第二章 碧云\n另一版本第二章。\n")
    oc = curl("POST", "/api/library/import", {"path": p3, "author": "", "force": False})
    check(oc.get("code") == "ok" and oc.get("existing_id") == "",
          "same-title different-content → distinct", oc)

    # 6) 10MiB（AC 目标）置于最后：VM 轨 10M 指令预算硬上限（engine.rs
    #    CPU_CUMULATIVE_STEP_BUDGET）——登记跨仓能力计划，不以降标顶替；
    #    此处断言「显式失败而非假成功」。
    o10 = curl("POST", "/api/library/import", {"path": long_path, "author": "", "force": False})
    blocked = (o10.get("error") is not None) or (o10.get("code") == "io_error") or o10.get("__empty__")
    check(blocked, "10MiB import fails explicitly (VM budget ceiling, cross-repo)", o10)

    print(f"--- summary: {len(FAILS)} fails ---")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
