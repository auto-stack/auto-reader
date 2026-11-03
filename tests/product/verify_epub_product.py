#!/usr/bin/env python3
"""verify_epub_product.py — READER-007 正式 EPUB 产品永久门（T-02 建立）。

统一入口（计划 §5.5/§6，P-01～12 必需集）：

    python tests/product/verify_epub_product.py --profile vue|vm \\
        --auto-bin <固定 auto.exe> --out-dir <自有隔离> [--corpus-dir <语料>] [--keep]

- P-01～12 在 REQUIRED 清单注册唯一 ID（profile 适用性显式）；父用例结果由其
  本身与子项最坏推导；0 选择/缺项/重复/GAP/FAIL/not_run/未声明根/坏 cohort/
  ENV 不可用一律非零。
- 从正常产品 UI 驱动（正式书架/reading_page），不调用 probe 专用写端点；
  数据/API/磁盘仅作独立读回，正常保存不预写。
- 旧 APP 门（verify_standalone/verify_local/verify_epub/原生驱动）作为
  P-12 子腿同 cohort 回归；T-09 固定最终 cohort 全量执行。
- 语料由 tests/product/gen_product_corpus.py 确定性生成（hash 可重算）。

退出码：0=全部必需用例通过；1=FAIL/GAP/缺项/重复/未声明；2=环境不可用；
         3=有用例 not_run（功能未闭合，不得冒充通过）。
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MARKER = "product-scope.json"

# 产品语料重复句/跨段样本（与 gen_product_corpus.py 内一致，FROZEN）。
REPEAT_A = "产品重复句甲🦊：琥珀色的狐狸跃过懒狗时携带三枚星形饼干，并轻声数到十七✨，随后沿对角线穿过整段跨度以便在窄栏里真实换行。"
REPEAT_B = "产品重复句乙🐙：深蓝色的章鱼在暗礁之间整理十二枚贝壳🫧，把第七枚留给回声，然后沉入更深的走廊。"
CROSS_PARA = "跨段引文甲：这段文字的上半句落在段落末尾，"  # 前半（段尾）
CROSS_PARA2 = "下半句则跨进下一段的开头继续，形成真实跨段范围。"  # 后半（下段首）

RECORDS = []


def record(case, outcome, detail=""):
    """outcome ∈ PASS | FAIL | GAP | not_run（计划 §6 四态）。"""
    RECORDS.append({"case": case, "outcome": outcome, "detail": str(detail)[:240]})
    print(f"{outcome:8s} {case}" + (f" :: {str(detail)[:180]}" if detail else ""))


# ─────────────────────── P-01～12 必需用例清单（READER-007 §6） ───────────────────────

REQUIRED = {
    "P-01": {"vm": True, "vue": True, "task": "T-00",
             "desc": "029交付cohort+正式Reader启动，两端实际window/route/backend；依赖未就绪停T-00"},
    "P-02": {"vm": True, "vue": True, "task": "T-02/03/04",
             "desc": "正常书架导入/打开，断网、移走probe资产路径后重开，目录/图/脚注/正文结构"},
    "P-03": {"vm": True, "vue": True, "task": "T-04/08",
             "desc": "分页/滚动、字号/列宽变化、隐藏显示后重新选指定范围；专门复现029 Vue重排风险"},
    "P-04": {"vm": True, "vue": True, "task": "T-05/06",
             "desc": "重复句第2处、中文emoji跨行/跨段范围→高亮/批注→编辑/删除；CFI真实解析+quote/occ独立oracle"},
    "P-05": {"vm": True, "vue": True, "task": "T-05/07",
             "desc": "完整旧v1库、章书签、重复句/未知字段边界、可映射与不可映射/多义记录"},
    "P-06": {"vm": True, "vue": True, "task": "T-07/08",
             "desc": "真实保存后正常退出/强退，新进程换布局恢复；旧/新混合记录"},
    "P-07": {"vm": True, "vue": True, "task": "T-07",
             "desc": "搜索重复句→每个命中跳转→回访注释→Markdown导出；导出可独立解析"},
    "P-08": {"vm": True, "vue": True, "task": "T-08",
             "desc": "配对CFI指另一处重复句、错book/hash/session/stale事件、错quote、源改版"},
    "P-09": {"vm": True, "vue": True, "task": "T-02/08",
             "desc": "30MiB与单资源等profile边界两侧、坏zip/超额/脚本/远程URL/跨书路径"},
    "P-10": {"vm": True, "vue": True, "task": "T-05/08",
             "desc": "迁移/新记录写失败、坏/空状态文件、只读目录、重开；不报假保存/空库"},
    "P-11": {"vm": True, "vue": True, "task": "T-08/09",
             "desc": "两书/两实例并存、换书/关闭/迟到事件、IME/焦点/系统无障碍/geometry"},
    "P-12": {"vm": True, "vue": True, "task": "T-09/10",
             "desc": "新旧双端门；缺case/GAP/错工具/占口；真实资产或locator变异→还原"},
}


def parent_of(case):
    return case.split(".", 1)[0]


def aggregate(profile, records):
    """严格聚合。返回 (ok, findings, not_run_count)。语义同 029 N-10 门。"""
    findings = []
    by_case = {}
    for r in records:
        by_case.setdefault(r["case"], []).append(r)

    declared_roots = set(REQUIRED)
    for case in by_case:
        root = parent_of(case)
        if root not in declared_roots:
            findings.append(("undeclared", case, "not in REQUIRED manifest"))
            continue
        if not REQUIRED[root][profile]:
            findings.append(("undeclared", case,
                             f"{root} not applicable to profile {profile}"))

    for cid, spec in REQUIRED.items():
        if not spec[profile]:
            continue
        subs = [(c, rs) for c, rs in by_case.items() if parent_of(c) == cid]
        if not subs:
            findings.append(("missing", cid, "required case not executed"))
            continue
        for c, rs in subs:
            if len(rs) > 1:
                findings.append(("duplicate", c, f"{len(rs)} records with same case id"))
            for r in rs:
                if r["outcome"] == "FAIL":
                    findings.append(("fail", c, r["detail"]))
                elif r["outcome"] == "GAP":
                    findings.append(("gap", c, r["detail"]))
    not_run = [r for r in records if r["outcome"] == "not_run"]
    ok = not findings and not not_run
    return ok, findings, len(not_run)


# ─────────────────────── 安全输出目录（029 §5.2 语义） ───────────────────────


def _is_reparse(path):
    try:
        FILE_ATTRIBUTE_REPARSE_POINT = 0x400
        return bool(os.lstat(path).st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT)
    except (OSError, AttributeError):
        return False


def guard_out_dir(raw):
    """out-dir 必须是新建或本门标记过的自有 scope；拒绝用户根/系统目录/仓根/
    reparse 点。返回绝对路径。"""
    p = os.path.abspath(raw)
    home = os.path.expanduser("~")
    refused = {
        home, os.path.join(home, "Desktop"), os.path.join(home, "Documents"),
        os.path.join(home, "Downloads"), os.path.dirname(home), home + os.sep,
    }
    norm = p.rstrip(os.sep).lower()
    for r in list(refused):
        if isinstance(r, str) and norm == r.lower().rstrip(os.sep):
            raise SystemExit(f"ENV-UNSAFE out-dir refused (protected path): {p}")
    if norm == os.path.splitdrive(p)[0].lower():
        raise SystemExit(f"ENV-UNSAFE out-dir refused (drive root): {p}")
    if _is_reparse(p):
        raise SystemExit(f"ENV-UNSAFE out-dir refused (reparse point): {p}")
    if os.path.exists(p):
        marker = os.path.join(p, MARKER)
        if not os.path.isdir(p):
            raise SystemExit(f"ENV-UNSAFE out-dir not a directory: {p}")
        if not os.path.exists(marker):
            entries = os.listdir(p)
            if entries:
                raise SystemExit(
                    f"ENV-UNSAFE out-dir exists without product marker and is not "
                    f"empty ({len(entries)} entries): {p}")
    os.makedirs(p, exist_ok=True)
    if _is_reparse(p):
        raise SystemExit(f"ENV-UNSAFE out-dir became reparse point: {p}")
    with open(os.path.join(p, MARKER), "w", encoding="utf-8") as f:
        f.write(json.dumps({"scope": "reader-007", "entry": "verify_epub_product.py"}))
    return p


def safe_rmtree(path):
    if not os.path.isdir(path):
        return
    if _is_reparse(path):
        raise SystemExit(f"ENV-UNSAFE refusing rmtree on reparse point: {path}")
    p = os.path.abspath(path)
    if not os.path.basename(p) and os.path.dirname(p) == os.path.splitdrive(p)[0]:
        raise SystemExit(f"ENV-UNSAFE refusing rmtree on drive root: {p}")
    shutil.rmtree(p)


# ─────────────────────── cohort 与运行助手 ───────────────────────


def http_json(url, method="GET", data=None, timeout=15):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        try:
            return json.loads(raw.decode("utf-8", "replace"))
        except json.JSONDecodeError:
            return raw.decode("utf-8", "replace")


def http_ok(url, timeout=8):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def wait(fn, deadline, step=2.0):
    t0 = time.monotonic()
    while time.monotonic() - t0 < deadline:
        try:
            if fn():
                return True
        except Exception:
            pass
        time.sleep(step)
    return False


def run_cmd(cmd, cwd=None, env=None, timeout=900):
    e = dict(os.environ)
    if env:
        e.update(env)
    r = subprocess.run(cmd, cwd=cwd, env=e, capture_output=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return r


def bin_version(auto_bin):
    try:
        r = subprocess.run([auto_bin, "--version"], capture_output=True,
                           text=True, timeout=30)
        return (r.stdout or r.stderr).strip()
    except Exception as e:
        return f"ERR:{e}"


# ─────────────────────── P-01：029 交付 + 正式启动（T-00 已证事实，门内复核） ───────────────────────

UI_PLAN_029 = os.path.join("D:", os.sep, "autostack", "auto-ui",
                           "docs", "plans", "archived",
                           "029-reader-native-input-and-surface-closure.md")
UI_LANDING = "65bb455fa4066a9401d47c845d5d13bda48804be"


def check_cohort_desk(auto_bin):
    """029 交付 desk 复核：归档计划 status/复审/landing 在位；auto 版本 g47d8f7b；
    auto-ui-tool 含 doc-surface 接口（T-00 物化后必须持续满足）。"""
    try:
        with open(UI_PLAN_029, encoding="utf-8") as f:
            plan = f.read()
        ok_archived = ("status: archived" in plan
                       and "T-10" in plan
                       and "outcome: pass" in plan)
        ok_landing = run_cmd(["git", "log", "-1", "--format=%H", UI_LANDING],
                             cwd=os.path.join("D:", os.sep, "autostack", "auto-ui"),
                             timeout=60).stdout.strip() == UI_LANDING
    except OSError:
        ok_archived = ok_landing = False
    ver = bin_version(auto_bin)
    ok_auto = "g47d8f7b" in ver
    tool = os.environ.get("AUTO_UI_TOOL_BIN", "")
    ok_tool = bool(tool) and os.path.isfile(tool)
    if ok_tool:
        try:
            with open(tool, "rb") as f:
                blob = f.read()
            ok_tool = b"AutoUIDocSurfacePopup" in blob and b"doc_surface" in blob
        except OSError:
            ok_tool = False
    return ok_archived, ok_landing, ok_auto, ok_tool, ver


def p01(args, out_dir):
    """P-01：029 全部门/独立review/交付可核；Reader 自身窗口/工具同源。"""
    desk = check_cohort_desk(args.auto_bin)
    record("P-01.cohort-desk", "PASS" if all(desk[:4]) else "FAIL",
           f"archived={desk[0]} landing={desk[1]} auto_g47d8f7b={desk[2]} "
           f"tool_doc-surface={desk[3]} ver={desk[4][:40]}")
    if not all(desk[:4]):
        return
    # 正式启动：vm 分离窗口+后端+MCP；vue 前端+后端。
    data_dir = os.path.join(out_dir, f"reader-data-{args.profile}")
    env = dict(os.environ,
               AUTO_READER_DATA=data_dir,
               AUTO_HTTP_STEP_BUDGET="1000000000",
               AUTO_HTTP_REQUEST_TIMEOUT_MS="300000")
    logf = open(os.path.join(out_dir, f"boot-{args.profile}.log"), "w",
                encoding="utf-8", errors="replace")
    if args.profile == "vm":
        env["AUTO_UI_TOOL_BIN"] = os.environ.get("AUTO_UI_TOOL_BIN", "")
        env["WEBVIEW2_USER_DATA_FOLDER"] = os.path.join(out_dir, "webview-udf")
        env["AUTO_VM_WINDOW"] = "1000x720"
        cmd = [args.auto_bin, "run", "-r", "vm", "--no-merge", "-B", "17825"]
    else:
        cmd = [args.auto_bin, "run", "--server=vm"]
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=logf,
                            stderr=subprocess.STDOUT)
    try:
        ok_back = wait(lambda: http_ok("http://127.0.0.1:17825/api/library/books"), 120)
        record("P-01.backend", "PASS" if ok_back else "FAIL",
               "backend 17825 books reachable")
        if args.profile == "vm":
            time.sleep(6)
            text = open(os.path.join(out_dir, f"boot-{args.profile}.log"),
                        encoding="utf-8", errors="replace").read()
            has_window = "图书阅读器" in text
            m = re.search(r"AutoUI MCP: listening on http://127\.0\.0\.1:(\d+)", text)
            record("P-01.window", "PASS" if has_window else "FAIL",
                   "native window 图书阅读器 (auto-ui-tool)")
            record("P-01.mcp", "PASS" if m else "FAIL",
                   f"mcp={('http://127.0.0.1:' + m.group(1)) if m else 'missing'}")
        else:
            ok_front = wait(lambda: http_ok("http://localhost:17824/"), 150)
            record("P-01.frontend", "PASS" if ok_front else "FAIL",
                   "vue frontend localhost:17824 (IPv6 loopback)")
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True)
        proc.wait()
        logf.close()


# ─────────────────────── P-09：预算/安全边界（导入侧现跑，引擎侧 T-08） ───────────────────────

def p09_import_legs(args, out_dir):
    """P-09 导入侧：继承 verify_epub（E-01..E-05：30MiB/12MiB 预算、坏 zip、
    图像/拒绝负例）在交付 cohort 上全绿。引擎侧（脚本/远程/跨书）T-08 接入。"""
    r = run_cmd([sys.executable,
                 os.path.join(ROOT, "tests", "epub", "verify_epub.py"),
                 "--auto"],
                cwd=ROOT, env={"AUTO_EXE": args.auto_bin}, timeout=1200)
    tail = (r.stdout or "")[-200:] + (r.stderr or "")[-100:]
    ok = r.returncode == 0 and "FAIL=0" in (r.stdout or "")
    record("P-09.import-bounds", "PASS" if ok else "FAIL",
           f"verify_epub rc={r.returncode} tail={tail.strip()[-150:]}")
    record("P-09.engine-bounds", "not_run",
           "引擎侧资源/脚本/远程/跨书边界 T-08 接入")


# ─────────────────────── P-12：新旧双端门（结构 T-02，冻结跑 T-09） ───────────────────────

def p12_structure(args, out_dir):
    """P-12 腿：verify_standalone/verify_local/原生驱动/变异红→绿。T-02 仅
    注册执行点；T-09 固定最终 cohort 全量执行（缺 case/GAP 非零语义由聚合器承担）。"""
    record("P-12.old-gates", "not_run",
           "verify_standalone/verify_local/原生驱动 + 变异红→绿 于 T-09 冻结 cohort 执行")
    record("P-12.strict-aggregator", "PASS",
           "聚合器非零语义在本门生效（缺项/重复/未声明/GAP/not_run → 非零）")


# ─────────────────────── 未实现用例注册（T-03..T-08 接入） ───────────────────────

def register_pending():
    for cid in ("P-02", "P-03", "P-04", "P-05", "P-06", "P-07", "P-08", "P-10", "P-11"):
        record(cid, "not_run", f"待 {REQUIRED[cid]['task']} 接入")


# ─────────────────────── main ───────────────────────


def main():
    ap = argparse.ArgumentParser(description="READER-007 EPUB 产品永久门")
    ap.add_argument("--profile", choices=["vue", "vm"], default="vue")
    ap.add_argument("--auto-bin", default=os.environ.get("AUTO_BIN", ""),
                    help="固定 auto.exe（或 AUTO_BIN env）")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--keep", action="store_true", help="保留 out-dir")
    ap.add_argument("--corpus-dir", default="",
                    help="已生成产品语料目录（缺省在 out-dir/corpus 生成）")
    args = ap.parse_args()

    if not args.auto_bin or not os.path.isfile(args.auto_bin):
        print("ENV-FAIL --auto-bin required (missing or not a file)")
        return 2
    if not os.environ.get("AUTO_UI_TOOL_BIN") and args.profile == "vm":
        print("ENV-FAIL vm profile requires AUTO_UI_TOOL_BIN (frozen cohort tool)")
        return 2
    out_dir = guard_out_dir(args.out_dir)

    corpus = args.corpus_dir or os.path.join(out_dir, "corpus")
    if not os.path.exists(corpus):
        r = run_cmd([sys.executable,
                     os.path.join(HERE, "gen_product_corpus.py"),
                     "--out-dir", corpus], cwd=ROOT, timeout=600)
        if r.returncode != 0:
            print("ENV-FAIL corpus generation failed:", (r.stderr or "")[-200:])
            return 2
    print(f"cohort: auto={bin_version(args.auto_bin)[:60]} "
          f"tool={os.environ.get('AUTO_UI_TOOL_BIN', '')}")

    p01(args, out_dir)
    p09_import_legs(args, out_dir)
    p12_structure(args, out_dir)
    register_pending()

    ok, findings, n_not_run = aggregate(args.profile, RECORDS)
    print(f"\naggregate: ok={ok} findings={len(findings)} not_run={n_not_run}")
    for kind, case, detail in findings:
        print(f"  {kind:10s} {case} :: {detail[:160]}")
    if findings:
        return 1
    if n_not_run:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
