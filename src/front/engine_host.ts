// engine_host.ts — READER-007 T-03 产品 vue 轨引擎宿主（逃生舱，页面自身装载）。
//
// 背景：doc-surface 在 vue 轨退化为透传 div（auto-ui 宿主接管契约），029 探针
// vue 轨靠 Playwright 注入胶水；产品禁止驱动注入（计划 §2「浏览器侧不能只由
// Playwright 注入实验 adapter 后宣称产品已接入」）。本模块是页面自身装载面：
// reading_page.at 经 use.web 引入 mountProductEngine，在 Init 时调用——它
// querySelector 找 doc-surface 透传容器，import 应用自有固定资产
// engine-adapter.js，并 mountProbe 到该容器。事件回传（locator）由 adapter
// 直接 fetch /api/reader/locator（T-05 接入数据层，本阶段回传校验面就绪）。
//
// VM 轨不消费本模块：doc-surface 是真实 WebView2 表面，url 由后端
// surface-url 端点生成并自动装载 native-host.html（其自身 import adapter）。
// 双轨由 ports/engine_host.web.at ↔ engine_host.vm.at facade 承担。

// 签名与 engine_host.vm.at 的 mountProductEngine(session_id, book_id,
// source_hash) 逐参对齐（facade 双轨一致；reading_page.at 以三位置参数调用）。
export async function mountProductEngine(
  sessionId: string,
  bookId: string,
  sourceHash: string,
): Promise<string> {
  // Init 异步链里 surface_url 刚写入 model，Vue 需 nextTick 才把 doc-surface
  // 渲染入树——轮询等宿主容器出现（100ms × 50 = 5s 上限），避免 no-host。
  let host: Element | null = null
  for (let i = 0; i < 50 && !host; i++) {
    host = document.querySelector('[data-auto-tag="doc-surface"]')
    if (!host) await new Promise(r => setTimeout(r, 100))
  }
  if (!host) return 'no-host'
  try {
    // vite 的 import-analysis 只静态解析字面量参数——直接
    // import('/api/reader/asset/engine-adapter.js') 会被当作项目内模块
    // 解析并失败（2026-11-03 T-03 实测 vite "Failed to resolve import"）。
    // 运行时拼接让浏览器在运行时 import：同源 /api 前缀经 vite proxy 到达
    // 后端固定资产端点，adapter 内部相对导入（foliate-*.js）同样经 proxy。
    const adapterUrl = '/api/reader/asset/' + 'engine-adapter.js'
    const m = await import(adapterUrl)
    await m.mountProbe({
      host,
      documentUrl: '/api/reader/document/' + bookId + '/file',
      locatorUrl: '/api/reader/locator',
      sessionId,
      bookId,
      sourceHash,
      onStatus: (msg: string) => { document.title = 'r:' + msg },
    })
    return 'ok'
  } catch (e) {
    return 'error:' + String(e)
  }
}
