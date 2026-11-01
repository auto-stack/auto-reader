#!/usr/bin/env python3
# verify_engine_surface.py — PLAN-026 探针永久入口（T-01 骨架；T-02/T-04/T-05 充实）。
#
# 用法：
#   python tests/probe/verify_engine_surface.py --profile vue --auto-bin <auto.exe> \
#       --out-dir <隔离输出> [--corpus-dir <已生成语料>] [--keep]
#   （缺 --corpus-dir 时先用 gen_corpus.py 生成到 <out-dir>/corpus）
#
# 聚合面（计划 §6 映射，逐例 PASS/reproduced_fail/GAP/not_run，不把 skip 计 PASS）：
#   T-01 数据层自检（本骨架即跑）：语料指纹、出现序 oracle、错锚区分力、
#        负例书可识别。
#   V-01..V-10：双端表面用例，T-02/T-03/T-04/T-05 实现；未实现一律
#        not_run_probe_incomplete，聚合退出码 3（探针未完成），不得冒充通过。
#
# 退出码：0=全部必需用例通过；1=有 FAIL；2=环境不可用；3=有用例未实现。
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from corpus_oracle import BookScan          # noqa: E402
from corpus_profile import PROFILE          # noqa: E402

REPEAT_A = "探针重复句甲🦊：琥珀色的狐狸跃过懒狗时携带三枚星形饼干，并轻声数到十七✨，随后沿对角线穿过整段跨度以便在窄栏里真实换行。"
REPEAT_B = "探针重复句乙🐙：深蓝色的章鱼在暗礁之间整理十二枚贝壳🫧，把第七枚留给回声，然后沉入更深的走廊。"
REPEAT_A2 = "探针复现句甲贰🔑：三十七只萤火虫按逆时针绕过石灯笼，把影子叠成第九种形状。"

RECORDS = []


def record(case, outcome, detail=""):
    """outcome ∈ PASS | FAIL | GAP | not_run（计划 §5.4 四态）。"""
    RECORDS.append({"case": case, "outcome": outcome, "detail": str(detail)[:240]})
    print(f"{outcome:8s} {case}" + (f" :: {str(detail)[:180]}" if detail else ""))


# ─────────────────────── T-01 数据层自检（区分力证明） ───────────────────────

def t01_oracle_selfcheck(corpus_dir, out_dir):
    ok = True
    man_path = os.path.join(corpus_dir, "corpus-manifest.json")
    if not os.path.exists(man_path):
        record("T-01.corpus-manifest", "FAIL", f"missing {man_path}")
        return False
    with open(man_path, encoding="utf-8") as f:
        man = json.load(f)
    record("T-01.corpus-manifest", "PASS",
           ", ".join(f"{k}:{v['size']}B" for k, v in man.items()))

    alpha = BookScan(os.path.join(corpus_dir, "probe-alpha.epub"))
    beta = BookScan(os.path.join(corpus_dir, "probe-beta.epub"))

    # 出现序：REPEAT_A 全书恰 3 处；第 2 处 = ch1 第二个重复段（para 7）。
    n_a = alpha.sentence_occurrence_count(REPEAT_A)
    record("T-01.alpha-repeat3", "PASS" if n_a == 3 else "FAIL", f"count={n_a}")
    ok &= (n_a == 3)
    pos2 = alpha.expected_occurrence(REPEAT_A, 2)
    want = {"chapter": "ch1.xhtml", "para_index": 7, "offset_in_para": 0}
    good = pos2 == want
    record("T-01.alpha-2nd-occurrence", "PASS" if good else "FAIL",
           f"got={pos2} want={want}")
    ok &= good

    # 次锚与乙书计数。
    n_a2 = alpha.sentence_occurrence_count(REPEAT_A2)
    n_b = beta.sentence_occurrence_count(REPEAT_B)
    record("T-01.secondary-counts", "PASS" if (n_a2, n_b) == (2, 3) else "FAIL",
           f"a2={n_a2} b={n_b}")
    ok &= (n_a2, n_b) == (2, 3)

    # 锚身份与书身份：跨书 quote 不命中对方正文。
    cross = beta.find_sentence(REPEAT_A)
    record("T-01.cross-book-isolation", "PASS" if not cross else "FAIL",
           f"beta hits for alpha sentence={len(cross)}")
    ok &= not cross

    # 错锚区分力（oracle 层）：错字 quote 必须拒绝；正确 quote+occurrence 命中。
    bad = alpha.verify_quote(REPEAT_A.replace("十七", "十八"), 1)
    good_v = alpha.verify_quote(REPEAT_A, 2)
    sep = bad["ok"] is False and good_v["ok"] and good_v["position"] == want
    record("T-01.wrong-anchor-rejected", "PASS" if sep else "FAIL",
           f"bad={bad} good_pos={good_v.get('position')}")
    ok &= sep
    # occurrence 越界拒绝。
    oor = alpha.verify_quote(REPEAT_A, 4)
    record("T-01.occurrence-oor-rejected", "PASS" if not oor["ok"] else "FAIL",
           f"{oor}")
    ok &= not oor["ok"]

    # 图像身份：两书 PNG 独立解码且角像素符合冻结色、互异。
    ia, ib = alpha.image["pixels"], beta.image["pixels"]
    amber = ia["top_left"] == (178, 60, 20) and ia["bottom_right"] == (178, 60, 20)
    blue = ib["top_left"] == (30, 60, 200) and ib["bottom_right"] == (30, 60, 200)
    record("T-01.image-pixels", "PASS" if (amber and blue) else "FAIL",
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
    record("T-01.negatives-recognized",
           "PASS" if (mal_ok and oversize) else "FAIL",
           f"malformed={detail} oversize={oversize}")
    ok &= mal_ok and oversize

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "t01-oracle.json"), "w", encoding="utf-8") as f:
        json.dump({"alpha_repeat": n_a, "second_pos": pos2, "beta_repeat": n_b,
                   "image_alpha": alpha.image["sha256"][:16],
                   "image_beta": beta.image["sha256"][:16]}, f, ensure_ascii=False, indent=2)
    return ok


# ─────────────────────── V-01..V-10 注册表 ───────────────────────

def stub(case):
    def _stub(ctx):
        record(case, "not_run", "probe incomplete: case implemented in a later task")
        return "not_run"
    return _stub


def run_surface(ctx):
    """按 profile 驱动 V-01..V-10 已实现面（T-02 起）。"""
    oracle = BookScan(os.path.join(ctx["corpus_dir"], "probe-alpha.epub"))
    if ctx["profile"] == "vue":
        from driver_vue import run_vue
        run_vue(ctx["out_dir"], ctx["corpus_dir"], oracle, REPEAT_A, record)
    else:
        from driver_vm import run_vm
        run_vm(ctx["out_dir"], ctx["corpus_dir"], oracle, record)


CASES = {"surface": run_surface}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["vue", "vm"], required=True)
    ap.add_argument("--auto-bin", default=os.environ.get("AUTO_BIN") or "auto")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--corpus-dir", default=None)
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    t0 = time.monotonic()
    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

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

    # 表面用例：按 profile 执行（骨架期全部 not_run）。
    ctx = {"profile": args.profile, "corpus_dir": corpus_dir, "out_dir": out_dir,
           "auto_bin": args.auto_bin, "results": {}}
    for cid in sorted(CASES):
        ctx["results"][cid] = CASES[cid](ctx)

    with open(os.path.join(out_dir, f"results-{args.profile}.json"), "w",
              encoding="utf-8") as f:
        json.dump({"profile": args.profile, "elapsed_s": round(time.monotonic() - t0, 1),
                   "data_layer_ok": data_ok, "records": RECORDS}, f,
                  ensure_ascii=False, indent=2)

    fails = [r for r in RECORDS if r["outcome"] == "FAIL"]
    not_runs = [r for r in RECORDS if r["outcome"] == "not_run"]
    if fails:
        return 1
    if not_runs:
        return 3
    return 0 if data_ok else 1


if __name__ == "__main__":
    sys.exit(main())
