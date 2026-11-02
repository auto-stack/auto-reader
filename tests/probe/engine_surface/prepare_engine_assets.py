#!/usr/bin/env python3
# prepare_engine_assets.py — 从只读 readest 检出重建 PLAN-026 探针引擎资产。
# （plan-artifacts/plan-026/engine-assets 按 delete-at-merge 已删；本脚本
#   保证资产可确定性重建，无具名持有。）
#
# 用法：python prepare_engine_assets.py --out-dir <engine-assets目录> \
#           [--readest D:/autostack/readest]
# 产出：foliate-*.js（vendor 扁平化重写）、engine-adapter.js、native-host.html
import argparse
import os
import shutil

VENDOR_HTML = """<!doctype html>
<!-- PLAN-026 T-03 原生表面页：WebView2(iced 宿主内) 从消费 app 同源装载
     引擎资产与受管文档；选区 fetch 直达 .at 消费 handler；挂载完成后经
     window.ipc 回报引擎身份与装载时长。 -->
<html>
<head><meta charset="utf-8"><title>plan-026-native-surface</title>
<style>
  html,body{margin:0;height:100%;background:#fff;font:15px/1.7 serif}
  #seam{position:absolute;inset:0;overflow:hidden}
</style></head>
<body>
  <div id="seam"></div>
  <script type="module">
    const q = new URLSearchParams(location.search);
    import('/api/probe/asset/engine-adapter.js')
      .then(m => m.mountProbe({
        host: document.getElementById('seam'),
        documentUrl: '/api/probe/document/' + q.get('doc') + '/file',
        locatorUrl: '/api/probe/locator',
        sessionId: q.get('session'),
        bookId: q.get('doc'),
        sourceHash: q.get('hash'),
        onStatus: (m) => { document.title = 'p:' + m; },
      }))
      .then(r => {
        if (window.ipc) window.ipc.postMessage(JSON.stringify({
          schema_version: 1, probe: 't03-engine',
          engine: 'foliate-js@3d794195',
          spine: r.book.sections.length,
          loadMs: r.loadMs, surface_alive: true,
        }));
      })
      .catch(e => {
        if (window.ipc) window.ipc.postMessage(JSON.stringify({ probe: 't03-engine', error: String(e) }));
        document.title = 'CATCH:' + e;
      });
    // 选区状态周期回报（真实拖选是否产生 DOM 选区的宿主侧可见证据）。
    setInterval(() => {
      if (!window.ipc) return;
      const frames = [];
      const collect = (root) => {
        for (const el of root.querySelectorAll('*')) {
          if (el.tagName === 'IFRAME') frames.push(el);
          if (el.shadowRoot) collect(el.shadowRoot);
        }
      };
      collect(document);
      const sels = frames.map(f => {
        try {
          const s = f.contentDocument.getSelection();
          return s && !s.isCollapsed ? s.toString().slice(0, 40) : '(c)';
        } catch (e) { return 'ERR'; }
      });
      window.ipc.postMessage(JSON.stringify({ probe: 'sel', sels }));
    }, 3000);
  </script>
</body>
</html>
"""

ADAPTER_NOTE = """// engine-adapter.js 由 worktree 提交固化：
// auto-ui experiments/reader-engine-probe 伴随的探针资产（见
// docs/research/reader-engine-probe.md §5）；本脚本从 git 历史恢复该文件
// 由调用方以 --adapter 指定，或使用当前目录已有的 engine-adapter.js。
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--readest", default="D:/autostack/readest")
    ap.add_argument("--adapter", required=True,
                    help="engine-adapter.js 源（git show 提取件或既有副本）")
    args = ap.parse_args()
    src = os.path.join(args.readest, "packages", "foliate-js")
    if not os.path.isdir(src):
        raise SystemExit("readest foliate-js missing: " + src)
    out = args.out_dir
    os.makedirs(out, exist_ok=True)
    for name in os.listdir(src):
        if name.endswith(".js"):
            text = open(os.path.join(src, name), encoding="utf-8",
                        errors="surrogateescape").read()
            text = text.replace("'./", "'./foliate-")
            text = text.replace("'./foliate-vendor/", "'./foliate-vendor-")
            with open(os.path.join(out, "foliate-" + name), "w",
                      encoding="utf-8", newline="\n") as f:
                f.write(text)
    # PLAN-029 T-00 修正：.at 后端资产路由 :name 只匹配单段（实测
    # foliate-vendor/zip.js 404），vendor 文件必须扁平为 foliate-vendor-<名>，
    # 并把顶层文件的 './foliate-vendor/<名>' 引用同步改写为扁平名（026 合入
    # 件从未整体重验，重建脚本与 026 实跑资产布局脱节——本次实测修复）。
    vendor = os.path.join(src, "vendor")
    for name in os.listdir(vendor):
        if name.endswith(".js"):
            text = open(os.path.join(vendor, name), encoding="utf-8",
                        errors="surrogateescape").read()
            with open(os.path.join(out, "foliate-vendor-" + name), "w",
                      encoding="utf-8", newline="\n") as f:
                f.write(text)
    shutil.copyfile(args.adapter, os.path.join(out, "engine-adapter.js"))
    with open(os.path.join(out, "native-host.html"), "w", encoding="utf-8",
              newline="\n") as f:
        f.write(VENDOR_HTML)
    print("engine assets prepared at", os.path.abspath(out))


if __name__ == "__main__":
    main()
