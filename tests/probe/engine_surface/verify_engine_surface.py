#!/usr/bin/env python3
# verify_engine_surface.py — PLAN-026/029 探针永久入口。
#
# PLAN-029 T-01 重构：机器必需用例集（§6 N-01～12）+ 严格聚合 + 安全输出目录。
#
# 用法：
#   python tests/probe/engine_surface/verify_engine_surface.py --profile vue|vm \
#       --auto-bin <auto.exe> --out-dir <隔离输出> [--corpus-dir <已生成语料>] [--keep]
#   （缺 --corpus-dir 时先用 gen_corpus.py 生成到 <out-dir>/corpus）
#
# 聚合语义（计划 §5.4）：
#   - REQUIRED 清单声明每个 N-case 的 profile 适用性；父用例结果由其本身与
#     全部 `<父ID>.` 子项推导（取最坏）。
#   - 0选择/缺项/重复/未运行/GAP/失败/未声明用例/环境不可用 → 一律非零。
#   - exit0 要求：必需集全覆盖且全部 PASS，且无未声明根用例混入。
# 退出码：0=全部必需用例通过；1=FAIL/GAP/缺项/重复/未声明；2=环境不可用；
#         3=有用例 not_run（探针未完成，不得冒充通过）。
import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from corpus_oracle import BookScan  # noqa: E402
from corpus_profile import PROFILE  # noqa: E402

REPEAT_A = "探针重复句甲🦊：琥珀色的狐狸跃过懒狗时携带三枚星形饼干，并轻声数到十七✨，随后沿对角线穿过整段跨度以便在窄栏里真实换行。"
REPEAT_B = "探针重复句乙🐙：深蓝色的章鱼在暗礁之间整理十二枚贝壳🫧，把第七枚留给回声，然后沉入更深的走廊。"
REPEAT_A2 = "探针复现句甲贰🔑：三十七只萤火虫按逆时针绕过石灯笼，把影子叠成第九种形状。"

RECORDS = []


def record(case, outcome, detail=""):
    """outcome ∈ PASS | FAIL | GAP | not_run（计划 §5.4 四态）。"""
    RECORDS.append({"case": case, "outcome": outcome, "detail": str(detail)[:240]})
    print(f"{outcome:8s} {case}" + (f" :: {str(detail)[:180]}" if detail else ""))


# ─────────────────────── N-01～12 必需用例清单（PLAN-029 §6） ───────────────────────

REQUIRED = {
    "N-01": {"vm": True, "vue": False, "task": "T-00/T-03",
             "desc": "同一宿主/文档比较系统/桌面/CDP真实输入，首失败边界与因果"},
    "N-02": {"vm": True, "vue": True, "task": "T-02/T-03",
             "desc": "实际消费页真实拖选第2处重复句（中文/emoji/跨行）→.at前端状态→后端核验→sidecar"},
    "N-03": {"vm": True, "vue": True, "task": "T-03",
             "desc": "正常+异常退出后新进程恢复同一出现位置，旧数据/身份不变"},
    "N-04": {"vm": True, "vue": False, "task": "T-04",
             "desc": "chrome↔正文↔输入框焦点往返与真实中文IME组合/提交/取消/快捷键"},
    "N-05": {"vm": True, "vue": True, "task": "T-05",
             "desc": "resize/DPI/字号重排/滚动、遮挡/隐藏再显示后真实拖选/恢复仍命中"},
    "N-06": {"vm": True, "vue": False, "task": "T-05",
             "desc": "系统无障碍工具在native所属树定位正文并操作，键盘访问"},
    "N-07": {"vm": True, "vue": False, "task": "T-06",
             "desc": "A/B双实例隔离，关闭A后旧事件拒绝、B继续、新A不接旧会话"},
    "N-08": {"vm": True, "vue": False, "task": "T-06",
             "desc": "正常close/切文档/崩溃分别释放自有资源；旧MCP/IPC目标再调用真实断连；端口复用"},
    "N-09": {"vm": True, "vue": True, "task": "T-07",
             "desc": "身份/序号/预算/路径/锚负控全拒绝零落盘，合法对照成功"},
    "N-10": {"vm": True, "vue": True, "task": "T-01/T-06",
             "desc": "聚合门本身：缺项/空集/重复/GAP/not_run/ENV/坏tool/占口受控非零"},
    "N-11": {"vm": True, "vue": True, "task": "T-07",
             "desc": "变异已存locator/身份使核验恢复失败→聚合非零→还原绿"},
    "N-12": {"vm": True, "vue": True, "task": "T-08/T-09",
             "desc": "Vue既有链+两端守旧门+R-05/R-06vm原负例在交付cohort全部通过"},
}


def parent_of(case):
    return case.split(".", 1)[0]


def aggregate(profile, records):
    """严格聚合。返回 (ok, findings, not_run_count)。

    findings: [(kind, case, detail)] kind ∈ missing|duplicate|fail|gap|
    undeclared；not_run 单列（exit 3）。
    """
    findings = []
    by_case = {}
    for r in records:
        by_case.setdefault(r["case"], []).append(r)

    # 未声明根用例：任何不属于必需集（含其子项命名空间）的记录都算混入。
    declared_roots = set(REQUIRED)
    for case in by_case:
        root = parent_of(case)
        if root not in declared_roots:
            findings.append(("undeclared", case, f"not in REQUIRED manifest"))
            continue
        if not REQUIRED[root][profile]:
            findings.append(("undeclared", case,
                             f"{root} not applicable to profile {profile}"))
    if len(by_case) != len(records):
        pass  # 同名重复在下方逐父检测（同名子项也视为重复）。

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


# ─────────────────────── 安全输出目录（计划 §5.2） ───────────────────────

MARKER = "probe-scope.json"


def _is_reparse(path):
    """Windows reparse point（symlink/junction/mount point）检测。"""
    try:
        FILE_ATTRIBUTE_REPARSE_POINT = 0x400
        return bool(os.lstat(path).st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT)
    except (OSError, AttributeError):
        return False


def guard_out_dir(raw):
    """out-dir 必须是新建或本探针标记过的自有 scope；拒绝用户根/系统目录/
    仓根/reparse 点。返回绝对路径。"""
    p = os.path.abspath(raw)
    home = os.path.expanduser("~")
    refused = {
        home, os.path.join(home, "Desktop"), os.path.join(home, "Documents"),
        os.path.join(home, "Downloads"), os.path.dirname(home),
        home + os.sep, p.rstrip(os.sep) == os.path.splitdrive(p)[0],
    }
    norm = p.rstrip(os.sep).lower()
    for r in list(refused):
        if isinstance(r, str) and norm == r.lower().rstrip(os.sep):
            raise SystemExit(f"ENV-UNSAFE out-dir refused (protected path): {p}")
    if norm == os.path.splitdrive(p)[0 + 0].lower():
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
                    f"ENV-UNSAFE out-dir exists without probe marker and is not "
                    f"empty ({len(entries)} entries): {p}")
    os.makedirs(p, exist_ok=True)
    if _is_reparse(p):
        raise SystemExit(f"ENV-UNSAFE out-dir became reparse point: {p}")
    with open(os.path.join(p, MARKER), "w", encoding="utf-8") as f:
        json.dump({"scope": "plan-029-engine-surface", "created": time.time(),
                   "pid": os.getpid()}, f)
    return p


def safe_rmtree(path, scope_root):
    """仅清 scope 内自有目录；reparse 点与越界路径具名拒绝，不跟随。"""
    p = os.path.abspath(path)
    root = os.path.abspath(scope_root)
    if p == root or not (p + os.sep).startswith(root + os.sep):
        raise SystemExit(f"CLEANUP-REFUSED outside scope: {p}")
    if _is_reparse(p):
        raise SystemExit(f"CLEANUP-REFUSED reparse point: {p}")
    import shutil
    shutil.rmtree(p, ignore_errors=True)


# ─────────────────────── cohort 指纹（N-10/AC-08 绑定面） ───────────────────────

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cohort_fingerprint(auto_bin):
    """工具身份：bin 存在性 + sha256 + --version 首行。坏 bin → (None, 原因)。"""
    if not auto_bin or not os.path.isfile(auto_bin):
        return None, f"auto-bin not found: {auto_bin!r}"
    try:
        r = subprocess.run([auto_bin, "--version"], capture_output=True,
                           encoding="utf-8", errors="replace", timeout=30)
        ver = (r.stdout or r.stderr).strip().splitlines()[0][:120] if (r.stdout or r.stderr) else "?"
    except Exception as e:  # noqa: BLE001
        return None, f"auto-bin --version failed: {e!r}"
    return {"sha256": file_sha256(auto_bin), "version": ver}, None


# ─────────────────────── T-01 数据层自检（区分力证明，026 已立） ───────────────────────

def t01_oracle_selfcheck(corpus_dir, out_dir):
    ok = True
    man_path = os.path.join(corpus_dir, "corpus-manifest.json")
    if not os.path.exists(man_path):
        record("N-09.corpus-manifest", "FAIL", f"missing {man_path}")
        return False
    with open(man_path, encoding="utf-8") as f:
        man = json.load(f)
    record("N-09.corpus-manifest", "PASS",
           ", ".join(f"{k}:{v['size']}B" for k, v in man.items()))

    alpha = BookScan(os.path.join(corpus_dir, "probe-alpha.epub"))
    beta = BookScan(os.path.join(corpus_dir, "probe-beta.epub"))

    # 出现序：REPEAT_A 全书恰 3 处；第 2 处 = ch1 第二个重复段（para 7）。
    n_a = alpha.sentence_occurrence_count(REPEAT_A)
    record("N-09.alpha-repeat3", "PASS" if n_a == 3 else "FAIL", f"count={n_a}")
    ok &= (n_a == 3)
    pos2 = alpha.expected_occurrence(REPEAT_A, 2)
    want = {"chapter": "ch1.xhtml", "para_index": 7, "offset_in_para": 0}
    good = pos2 == want
    record("N-09.alpha-2nd-occurrence", "PASS" if good else "FAIL",
           f"got={pos2} want={want}")
    ok &= good

    # 次锚与乙书计数。
    n_a2 = alpha.sentence_occurrence_count(REPEAT_A2)
    n_b = beta.sentence_occurrence_count(REPEAT_B)
    record("N-09.secondary-counts", "PASS" if (n_a2, n_b) == (2, 3) else "FAIL",
           f"a2={n_a2} b={n_b}")
    ok &= (n_a2, n_b) == (2, 3)

    # 锚身份与书身份：跨书 quote 不命中对方正文。
    cross = beta.find_sentence(REPEAT_A)
    record("N-09.cross-book-isolation", "PASS" if not cross else "FAIL",
           f"beta hits for alpha sentence={len(cross)}")
    ok &= not cross

    # 错锚区分力（oracle 层）：错字 quote 必须拒绝；正确 quote+occurrence 命中。
    bad = alpha.verify_quote(REPEAT_A.replace("十七", "十八"), 1)
    good_v = alpha.verify_quote(REPEAT_A, 2)
    sep = bad["ok"] is False and good_v["ok"] and good_v["position"] == want
    record("N-09.wrong-anchor-rejected", "PASS" if sep else "FAIL",
           f"bad={bad} good_pos={good_v.get('position')}")
    ok &= sep
    # occurrence 越界拒绝。
    oor = alpha.verify_quote(REPEAT_A, 4)
    record("N-09.occurrence-oor-rejected", "PASS" if not oor["ok"] else "FAIL",
           f"{oor}")
    ok &= not oor["ok"]

    # 图像身份：两书 PNG 独立解码且角像素符合冻结色、互异。
    ia, ib = alpha.image["pixels"], beta.image["pixels"]
    amber = ia["top_left"] == (178, 60, 20) and ia["bottom_right"] == (178, 60, 20)
    blue = ib["top_left"] == (30, 60, 200) and ib["bottom_right"] == (30, 60, 200)
    record("N-09.image-pixels", "PASS" if (amber and blue) else "FAIL",
           f"alpha={ia['top_left']} beta={ib['top_left']}")
    ok &= amber and blue

    # 负例可识别：截断书 zip 读失败；超额书 >1MiB 由 size 判定。
    try:
        BookScan(os.path.join(corpus_dir, "negative-malformed.epub"))
        mal_ok = False
        detail = "malformed book scanned without error (bad)"
    except Exception as e:  # noqa: BLE001 — 截断书必然读失败
        mal_ok = True
        detail = type(e).__name__
    with open(os.path.join(corpus_dir, "negative-oversize.epub"), "rb") as f:
        oversize = len(f.read()) > PROFILE["book_max_bytes"]
    record("N-09.negatives-recognized",
           "PASS" if (mal_ok and oversize) else "FAIL",
           f"malformed={detail} oversize={oversize}")
    ok &= mal_ok and oversize

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "t01-oracle.json"), "w", encoding="utf-8") as f:
        json.dump({"alpha_repeat": n_a, "second_pos": pos2, "beta_repeat": n_b,
                   "image_alpha": alpha.image["sha256"][:16],
                   "image_beta": beta.image["sha256"][:16]}, f, ensure_ascii=False, indent=2)
    return ok


# ─────────────────────── N-10：聚合门负控（本文件自身） ───────────────────────

def n10_aggregator_selftest():
    """受控负例喂 aggregate()，断言全部非零且分类正确；合法全集 exit0。"""
    def base_records():
        recs = []
        for cid, spec in REQUIRED.items():
            if spec["vue"]:
                recs.append({"case": cid, "outcome": "PASS", "detail": "synthetic"})
        return recs

    cases = []

    # 1) 缺项。
    recs = [r for r in base_records() if r["case"] != "N-03"]
    ok, f, _ = aggregate("vue", recs)
    cases.append(("missing", not ok and any(k == "missing" and c == "N-03" for k, c, _ in f)))

    # 2) 空集。
    ok, f, _ = aggregate("vue", [])
    cases.append(("empty", not ok))

    # 3) 重复。
    recs = base_records() + [{"case": "N-03", "outcome": "PASS", "detail": "dup"}]
    ok, f, _ = aggregate("vue", recs)
    cases.append(("duplicate", not ok and any(k == "duplicate" for k, _, _ in f)))

    # 4) GAP。
    recs = [dict(r, outcome="GAP") if r["case"] == "N-05" else r for r in base_records()]
    ok, f, _ = aggregate("vue", recs)
    cases.append(("gap", not ok and any(k == "gap" and c == "N-05" for k, c, _ in f)))

    # 5) not_run（由 aggregate 的 not_run 通路）。
    recs = [dict(r, outcome="not_run") if r["case"] == "N-05" else r for r in base_records()]
    ok, f, n_nr = aggregate("vue", recs)
    cases.append(("not_run", (not ok) and n_nr == 1))

    # 6) 未声明用例混入。
    recs = base_records() + [{"case": "V-99.legacy", "outcome": "PASS", "detail": "old id"}]
    ok, f, _ = aggregate("vue", recs)
    cases.append(("undeclared", not ok and any(k == "undeclared" for k, _, _ in f)))

    # 7) profile 不适用的用例出现（vm-only 用例混入 vue 记录）。
    recs = base_records() + [{"case": "N-04.ime", "outcome": "PASS", "detail": "vm only"}]
    ok, f, _ = aggregate("vue", recs)
    cases.append(("cross-profile", not ok))

    # 8) FAIL。
    recs = [dict(r, outcome="FAIL") if r["case"] == "N-02" else r for r in base_records()]
    ok, f, _ = aggregate("vue", recs)
    cases.append(("fail", not ok and any(k == "fail" and c == "N-02" for k, c, _ in f)))

    # 9) 合法全集 → exit0。
    ok, f, n_nr = aggregate("vue", base_records())
    cases.append(("legal-exit0", ok and not f and n_nr == 0))

    # 10) 0选择等价面：N-02 FAIL 明细已含（8）；子项 FAIL 也必须拦。
    recs = base_records() + [{"case": "N-02.real-drag", "outcome": "FAIL",
                              "detail": "no sidecar record"}]
    ok, f, _ = aggregate("vue", recs)
    cases.append(("sub-fail", not ok and any(k == "fail" and c == "N-02.real-drag"
                                             for k, c, _ in f)))

    bad = [(name, ok_i) for name, ok_i in cases if not ok_i]
    record("N-10.aggregator-negatives", "PASS" if not bad else "FAIL",
           f"{len(cases)-len(bad)}/{len(cases)} controlled negatives non-zero"
           + (f"; broken={bad}" if bad else ""))


# ─────────────────────── 表面用例执行（T-02+ 驱动） ───────────────────────

def stub(cid, note="implemented in a later task"):
    def _stub(ctx):
        record(cid, "not_run", f"probe incomplete: {note}")
        return "not_run"
    return _stub


def _run_cmd_capture(cmd, cwd, env, timeout):
    """子进程运行并捕获输出；超时返回 (None, "TIMEOUT …s")。"""
    try:
        r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return r, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return None, f"TIMEOUT {timeout}s"


def _wait_port_free(port, deadline=30.0):
    """端口静默屏障：上一段实例 kill 后 socket 释放有迟滞（且服务端有 busy
    回退链——带着残留实例起下一实例会把 HTTP 全部打到别人身上，dry2
    N-12.vue-chain 实证）。返回 False = deadline 内仍被占。"""
    import socket
    t0 = time.monotonic()
    while time.monotonic() - t0 < deadline:
        sk = socket.socket()
        try:
            sk.bind(("127.0.0.1", port))
            return True
        except OSError:
            time.sleep(1.0)
        finally:
            sk.close()
    return False


def _run_n12_gate(ctx):
    """N-12（AC-09）：Vue 既有链 + 两端旧门 + R-05/R-06vm 原负例（冻结
    cohort）。vue profile 的旧链 = 本聚合自身 vue 臂记录最坏推导镜像；
    vm profile 在隔离 out-dir 实际重跑 driver_vue。两端 verify_standalone
    各自完整跑（含 R-05 verify_epub 与 R-06vm 毁损负控/合法对照）；
    R-05 直连入口另设具名快检（T-08 复现定责的同一机制）。"""
    profile = ctx["profile"]

    # 端口静默屏障：前段实例必须完全退出再起 vue 链（17825/17827）。
    ports_quiet = _wait_port_free(17825) and _wait_port_free(17827)
    if not ports_quiet:
        record("N-12.vue-chain", "FAIL",
               "ports 17825/17827 not free before vue chain (leftover instance?)")

    # ① Vue 既有链
    if ports_quiet and profile == "vue":
        vue_recs = [r for r in RECORDS
                    if parent_of(r["case"]) in ("N-02", "N-03", "N-09")]
        bad = [r for r in vue_recs if r["outcome"] in ("FAIL", "GAP")]
        record("N-12.vue-chain", "PASS" if not bad else "FAIL",
               ("; ".join(f'{r["case"]}:{r["outcome"]}' for r in bad[:3])
                if bad else f"own vue arm ({len(vue_recs)} records) all pass"))
    elif ports_quiet:
        vue_dir = os.path.join(ctx["out_dir"], "n12-vue")
        os.makedirs(vue_dir, exist_ok=True)
        vrecs = []
        try:
            from driver_vue import run_vue
            oracle = BookScan(os.path.join(ctx["corpus_dir"], "probe-alpha.epub"))
            run_vue(vue_dir, ctx["corpus_dir"], oracle, REPEAT_A,
                    lambda c, o, d="": vrecs.append({"case": c, "outcome": o, "detail": d}))
        except Exception as e:
            record("N-12.vue-chain", "FAIL", "driver_vue exception: " + repr(e)[:120])
        else:
            bad = [r for r in vrecs if r["outcome"] in ("FAIL", "GAP")]
            record("N-12.vue-chain", "PASS" if not bad else "FAIL",
                   ("; ".join(f'{r["case"]}:{r["outcome"]}:{r["detail"][:40]}'
                              for r in bad[:3])
                    if bad else f"isolated rerun ({len(vrecs)} records) all pass"))

    # ② R-05 直连入口具名快检（api.at 直连服务真实契约，T-08 同门命令）
    root = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
    vep = os.path.abspath(os.path.join(HERE, "..", "..", "epub", "verify_epub.py"))
    r, out = _run_cmd_capture([sys.executable, vep, "--auto"], cwd=root,
                              env=dict(os.environ, AUTO_EXE=ctx["auto_bin"]),
                              timeout=600)
    rc = getattr(r, "returncode", r)
    record("N-12.r05-direct-entry", "PASS" if (rc == 0 and "PASS=22 FAIL=0" in out)
           else "FAIL", f"rc={rc} tail={out[-130:]}")

    # ③ 两端旧门完整跑（verify_standalone：R-01 启动/占口/坏tool、R-02/03
    # HTTP+UI oracle、R-04 verify_local、R-05 预算/缺失负例+verify_epub、
    # R-06 毁损负控——vue 走 Playwright 像素面，vm 走原生物件+截图像素面）
    gate = os.path.abspath(os.path.join(HERE, "..", "..", "basic", "verify_standalone.py"))
    for prof in ("vue", "vm"):
        gdir = os.path.join(ctx["out_dir"], f"n12-standalone-{prof}")
        os.makedirs(gdir, exist_ok=True)
        r, out = _run_cmd_capture(
            [sys.executable, gate, "--profile", prof, "--auto-bin", ctx["auto_bin"]],
            cwd=root, env=dict(os.environ, VERIFY_STANDALONE_HOME=gdir,
                               AUTO_EXE=ctx["auto_bin"]),
            timeout=3600)
        rc = getattr(r, "returncode", r)
        record(f"N-12.standalone-{prof}", "PASS" if rc == 0 else "FAIL",
               f"rc={rc} tail={out[-150:]}")


def run_surface(ctx):
    """按 profile 驱动已实现面。未实现必需父用例显式 not_run（聚合 exit3，
    不冒充通过）——T-02..T-09 逐个替换为真实执行。"""
    profile = ctx["profile"]
    if profile == "vue":
        from driver_vue import run_vue
        oracle = BookScan(os.path.join(ctx["corpus_dir"], "probe-alpha.epub"))
        run_vue(ctx["out_dir"], ctx["corpus_dir"], oracle, REPEAT_A, record)
        _run_n12_gate(ctx)
    else:
        # PLAN-029：vm 臂 = 真实 AutoUI 原生 VM 消费者。N-01（T-09：双通道
        # 输入对照）由 run_vm 在 N-02 后执行；N-04 IME/焦点门在 run_vm 尾段；
        # N-12 旧门/链在聚合末段独立执行（实例已停，端口空闲）。
        from driver_vm import run_vm
        oracle = BookScan(os.path.join(ctx["corpus_dir"], "probe-alpha.epub"))
        run_vm(ctx["out_dir"], ctx["corpus_dir"], oracle, record)
        # N-04 由 run_vm 尾段执行（真实 IME 门）；驱动早退未触达时显式 not_run。
        if not any(r["case"].startswith("N-04") for r in RECORDS):
            record("N-04", "not_run", "driver exited before the N-04 gate")
        if not any(r["case"].startswith("N-01") for r in RECORDS):
            record("N-01", "not_run", "driver exited before the N-01 gate")
        _run_n12_gate(ctx)


CASES = {"surface": run_surface, "n10": lambda ctx: n10_aggregator_selftest()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["vue", "vm"], required=True)
    ap.add_argument("--auto-bin", default=os.environ.get("AUTO_BIN") or "auto")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--corpus-dir", default=None)
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    t0 = time.monotonic()

    # 环境门：cohort 工具身份（N-10/AC-08：坏 bin 具名失败，无静默回落）。
    cohort, err = cohort_fingerprint(args.auto_bin)
    if cohort is None:
        print("ENV-UNAVAILABLE", err)
        return 2
    print(f"[cohort] auto {cohort['version']} sha256={cohort['sha256'][:16]}…")

    out_dir = guard_out_dir(args.out_dir)
    with open(os.path.join(out_dir, "cohort.json"), "w", encoding="utf-8") as f:
        json.dump({"profile": args.profile, "auto_bin": os.path.abspath(args.auto_bin),
                   **cohort}, f, ensure_ascii=False, indent=2)

    # 语料：缺则生成（隔离输出目录内），然后数据层自检。
    corpus_dir = args.corpus_dir or os.path.join(out_dir, "corpus")
    if not os.path.exists(os.path.join(corpus_dir, "corpus-manifest.json")):
        r = subprocess.run([sys.executable, os.path.join(HERE, "gen_corpus.py"),
                            "--out-dir", corpus_dir], capture_output=True,
                           encoding="utf-8", errors="replace", timeout=120)
        if r.returncode != 0:
            print("ENV-UNAVAILABLE corpus generation failed:", r.stdout, r.stderr)
            return 2

    data_ok = t01_oracle_selfcheck(corpus_dir, out_dir)
    if not data_ok:
        record("N-09", "FAIL", "data-layer oracle selfcheck failed")

    # 表面用例：按 profile 执行。
    ctx = {"profile": args.profile, "corpus_dir": corpus_dir, "out_dir": out_dir,
           "auto_bin": args.auto_bin, "cohort": cohort, "results": {}}
    for cid in sorted(CASES):
        ctx["results"][cid] = CASES[cid](ctx)

    ok, findings, n_not_run = aggregate(args.profile, RECORDS)
    with open(os.path.join(out_dir, f"results-{args.profile}.json"), "w",
              encoding="utf-8") as f:
        json.dump({"profile": args.profile,
                   "elapsed_s": round(time.monotonic() - t0, 1),
                   "data_layer_ok": data_ok, "aggregate_ok": ok,
                   "findings": findings, "not_run": n_not_run,
                   "cohort": cohort, "records": RECORDS},
                  f, ensure_ascii=False, indent=2)

    print(f"[aggregate] ok={ok} findings={len(findings)} not_run={n_not_run}")
    if not data_ok:
        return 1
    if any(k == "fail" or k == "gap" for k, _, _ in findings) and n_not_run:
        return 1
    if findings:
        return 1
    if n_not_run:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
