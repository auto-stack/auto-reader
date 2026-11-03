#!/usr/bin/env python3
"""prepare_product_assets.py — READER-007 T-03 产品固定资产打包（T-01 §1 冻结）。

用途：从只读 readest foliate-js 检出重建「应用自有受管资产」到仓库内固定目录
    src/assets/engine-assets/（git 跟踪、随 app 分发），产出 manifest 记录 hash。
    app 运行时只依赖该目录，不依赖 D:/autostack/readest 检出、PROBE_ASSETS_DIR
    或 tests/probe 目录（AC-02「断网和移走probe资产路径后重开仍用」）。

用法：python tests/product/prepare_product_assets.py
        [--readest D:/autostack/readest]
        [--out-dir src/assets/engine-assets]   # 缺省仓库内固定目录

产物（每次运行确定性重写，hash 可重算）：
  foliate-*.js / foliate-vendor-*.js   引擎扁平化 flat 重写（vendor 引用一致化）
  engine-adapter.js                    产品 adapter（消费 /api/reader/*）
  native-host.html                     原生表面装载页（WebView2 doc-surface）
  manifest.json                        每文件 sha256 + engine revision + 内容指纹
"""
import argparse
import hashlib
import json
import os
import shutil

ENGINE_REVISION = "foliate-js@3d7941954a98b136316a795e8200d60c9643b141"

# 产品 native-host：与探针同构，但资产/文档/会话/回传全部走正式 /api/reader/*。
NATIVE_HOST_HTML_TEMPLATE = """<!doctype html>
<!-- READER-007 T-03 正式原生表面页：WebView2(iced 宿主内) 从消费 app 同源装载
     应用自有固定资产与受管原件；选区 fetch 直达 .at 消费 handler；挂载完成
     后经 window.ipc 回报引擎身份与装载时长。 -->
<html>
<head><meta charset="utf-8"><title>reader-native-surface</title>
<style>
  html,body{margin:0;height:100%;background:#fff;font:15px/1.7 serif}
  #seam{position:absolute;inset:0;overflow:hidden}
</style></head>
<body>
  <div id="seam"></div>
  <script type="module">
    const q = new URLSearchParams(location.search);
    import('/api/reader/asset/engine-adapter.js')
      .then(m => m.mountProbe({
        host: document.getElementById('seam'),
        documentUrl: '/api/reader/document/' + q.get('doc') + '/file',
        locatorUrl: '/api/reader/locator',
        commandUrl: '/api/reader/command',
        sessionId: q.get('session'),
        bookId: q.get('doc'),
        sourceHash: q.get('hash'),
        onStatus: (m) => { document.title = 'r:' + m; },
      }))
      .then(r => {
        if (window.ipc) window.ipc.postMessage(JSON.stringify({
          schema_version: 1, probe: 'product-engine',
          engine: '__REV__',
          spine: r.book.sections.length,
          loadMs: r.loadMs, surface_alive: true,
        }));
      })
      .catch(e => {
        if (window.ipc) window.ipc.postMessage(JSON.stringify({ probe: 'product-engine', error: String(e) }));
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

NATIVE_HOST_HTML = NATIVE_HOST_HTML_TEMPLATE.replace("__REV__", ENGINE_REVISION)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


def flat_rewrite(src_text):
    """与探针 prepare_engine_assets.py 相同的扁平化重写（T-02 固化）。"""
    text = src_text.replace("'./", "'./foliate-")
    text = text.replace("'./foliate-vendor/", "'./foliate-vendor-")
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--readest", default="D:/autostack/readest")
    ap.add_argument("--out-dir", default="src/assets/engine-assets")
    ap.add_argument("--adapter", default="",
                    help="产品 adapter 源（缺省 = tests/product/engine-adapter.js）")
    args = ap.parse_args()

    src = os.path.join(args.readest, "packages", "foliate-js")
    if not os.path.isdir(src):
        raise SystemExit("readest foliate-js missing: " + src)

    out = os.path.abspath(args.out_dir)
    os.makedirs(out, exist_ok=True)

    written = []
    for name in sorted(os.listdir(src)):
        if not name.endswith(".js"):
            continue
        text = open(os.path.join(src, name), encoding="utf-8",
                    errors="surrogateescape").read()
        target = os.path.join(out, "foliate-" + name)
        with open(target, "w", encoding="utf-8", newline="\n") as f:
            f.write(flat_rewrite(text))
        written.append(target)

    vendor = os.path.join(src, "vendor")
    for name in sorted(os.listdir(vendor)):
        if not name.endswith(".js"):
            continue
        text = open(os.path.join(vendor, name), encoding="utf-8",
                    errors="surrogateescape").read()
        target = os.path.join(out, "foliate-vendor-" + name)
        with open(target, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        written.append(target)

    adapter_src = args.adapter or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "engine-adapter.js")
    if not os.path.isfile(adapter_src):
        raise SystemExit("product adapter missing: " + adapter_src)
    adapter_dst = os.path.join(out, "engine-adapter.js")
    shutil.copyfile(adapter_src, adapter_dst)
    written.append(adapter_dst)

    host_dst = os.path.join(out, "native-host.html")
    with open(host_dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(NATIVE_HOST_HTML)
    written.append(host_dst)

    manifest = {
        "schema_version": 1,
        "engine_revision": ENGINE_REVISION,
        "scope": "reader-007-product-assets",
        "files": {os.path.basename(p): sha256_file(p) for p in sorted(written)},
    }
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
