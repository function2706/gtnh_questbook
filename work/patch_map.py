"""template.html にクエストマップ表示を追加する一回限りのパッチ"""
from pathlib import Path

t = Path(__file__).resolve().parent.parent / 'template.html'
h = t.read_text(encoding='utf-8')

css = r'''
/* ---- クエストマップ ---- */
.viewseg{margin-left:auto}
.chtop{display:flex;align-items:flex-start;gap:12px;flex-wrap:wrap}
.mapwrap{position:relative;height:calc(100vh - 170px);min-height:420px;border:1px solid var(--line);border-radius:8px;background:var(--panel);overflow:hidden;margin-top:12px}
.mapwrap svg{width:100%;height:100%;display:block;touch-action:none;cursor:grab;user-select:none}
.mapwrap svg.drag{cursor:grabbing}
.maptools{position:absolute;left:10px;top:10px;display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:12px;z-index:2}
.maptools .btn{background:var(--panel);padding:3px 9px}
.legend{display:flex;gap:10px;background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:3px 9px;color:var(--muted)}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:-1px;border:2px solid}
.edge{stroke:var(--muted);stroke-width:1.2;fill:none;opacity:.55}
.edge.imp{stroke-dasharray:4 3}
.edge.hl{stroke:var(--accent);opacity:1;stroke-width:2.2}
.edge.dim{opacity:.12}
.node rect{stroke-width:2;rx:4}
.node.s1 rect{fill:var(--accent-soft);stroke:var(--accent)}
.node.s2 rect{fill:var(--note-bg);stroke:var(--c9)}
.node.s0 rect{fill:var(--warn-bg);stroke:var(--c6)}
.node{cursor:pointer}
.node:hover rect{stroke-width:3.5}
.node.sel rect{stroke:var(--text);stroke-width:4}
.node.dim{opacity:.3}
.node .no{font-size:9px;fill:var(--muted);text-anchor:middle;dominant-baseline:central;pointer-events:none}
.node .lb{font-size:8px;fill:var(--text);text-anchor:middle;pointer-events:none;paint-order:stroke;stroke:var(--panel);stroke-width:3px;stroke-linejoin:round}
svg.nolabel .lb, svg.far .lb{display:none}
.mapside{position:absolute;right:0;top:0;bottom:0;width:min(420px,100%);background:var(--bg);border-left:1px solid var(--line);overflow:auto;padding:10px 12px;z-index:3;box-shadow:-4px 0 12px rgba(0,0,0,.08)}
.mapside[hidden]{display:none}
.mapside .x{float:right}
.mapside details.q{margin-top:8px}
.mapside .body{padding:2px 12px 12px 14px}
.mapside .cols{grid-template-columns:1fr}
.rel{font-size:13px;margin:10px 0 0}
.rel h4{margin:8px 0 2px;font-size:12px;color:var(--muted);font-weight:normal}
.rel a{display:block;text-decoration:none;padding:2px 0}
.rel .other{color:var(--muted);font-size:11px;margin-left:4px}
.tomap{font-size:12px;margin-left:8px}
@media (max-width:820px){
  .mapwrap{height:calc(100vh - 210px)}
  .mapside{top:auto;left:0;width:100%;height:58%;border-left:0;border-top:1px solid var(--line)}
}
'''

js = r'''
// ---- クエストマップ ----
function renderMap(c, focus) {
  const nodes = c.map, pos = {};
  nodes.forEach(n => pos[n[0]] = n);
  const idx = {}; c.q.forEach((id, i) => idx[id] = i + 1);
  let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
  nodes.forEach(([, x, y, w, hh]) => { minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x + w); maxY = Math.max(maxY, y + hh); });
  // 同じ章内の前提だけを線にする (種類2=非表示は描かない)
  const edges = [];
  nodes.forEach(([id]) => ((Q[id] && Q[id].p) || []).forEach(([pid, ty]) => { if (pos[pid] && ty !== 2) edges.push([pid, id, ty]); }));
  const cx = n => n[1] + n[3] / 2, cy = n => n[2] + n[4] / 2;
  const qname = id => strip(Q[id] ? (st.mode === 'en' ? Q[id].ne : (Q[id].nj || Q[id].ne)) : id);
  const label = id => { const s = qname(id); return s.length > 14 ? s.slice(0, 13) + '…' : s; };
  const edgeSvg = edges.map(([a, b, ty]) => {
    const A = pos[a], B = pos[b];
    // 終点をノード枠の手前で止めて矢印を見せる
    const x1 = cx(A), y1 = cy(A), x2 = cx(B), y2 = cy(B), dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1;
    const r = Math.min(B[3], B[4]) / 2 + 3, r0 = Math.min(A[3], A[4]) / 2;
    return `<line class="edge${ty === 1 ? ' imp' : ''}" data-a="${a}" data-b="${b}" x1="${x1 + dx / L * r0}" y1="${y1 + dy / L * r0}" x2="${x2 - dx / L * r}" y2="${y2 - dy / L * r}" marker-end="url(#arr)"/>`;
  }).join('');
  const nodeSvg = nodes.map(([id, x, y, w, hh]) => {
    const q = Q[id], s = q ? q.t : 0, show = !st.filt || (q && String(q.t) === st.filt);
    return `<g class="node s${s}${show ? '' : ' dim'}" data-id="${id}"><title>${esc(qname(id))}</title>
      <rect x="${x}" y="${y}" width="${w}" height="${hh}"/><text class="no" x="${x + w / 2}" y="${y + hh / 2}">${idx[id] || ''}</text>
      <text class="lb" x="${x + w / 2}" y="${y + hh + 9}">${esc(label(id))}</text></g>`;
  }).join('');
  const box = view.querySelector('.mapwrap');
  box.innerHTML = `<div class="maptools"><button class="btn" data-z="in">＋</button><button class="btn" data-z="out">－</button><button class="btn" data-z="fit">全体</button>
      <label class="btn" style="display:flex;gap:4px;align-items:center"><input type="checkbox" id="lbl" ${st.labels ? 'checked' : ''}>名前</label>
      <span class="legend"><span><i style="background:var(--accent-soft);border-color:var(--accent)"></i>公式訳</span><span><i style="background:var(--note-bg);border-color:var(--c9)"></i>AI訳</span><span><i style="background:var(--warn-bg);border-color:var(--c6)"></i>未訳</span></span></div>
    <svg class="${st.labels ? '' : 'nolabel'}"><defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0L10,5L0,10z" fill="var(--muted)"/></marker></defs>
      <g class="vp">${edgeSvg}${nodeSvg}</g></svg><aside class="mapside" hidden></aside>`;
  const svg = box.querySelector('svg'), vp = svg.querySelector('.vp'), side = box.querySelector('.mapside');
  const S = { k: 1, tx: 0, ty: 0 };
  const apply = () => { vp.setAttribute('transform', `translate(${S.tx},${S.ty}) scale(${S.k})`); svg.classList.toggle('far', S.k < 0.75); };
  const fit = () => {
    const W = svg.clientWidth, H = svg.clientHeight, pad = 30;
    S.k = Math.min((W - pad * 2) / (maxX - minX + 20), (H - pad * 2 - 30) / (maxY - minY + 20), 3);
    S.tx = (W - (maxX - minX) * S.k) / 2 - minX * S.k; S.ty = pad + 30 - minY * S.k; apply();
  };
  const zoomAt = (f, px, py) => { const k = Math.max(0.15, Math.min(6, S.k * f)); f = k / S.k; S.tx = px - (px - S.tx) * f; S.ty = py - (py - S.ty) * f; S.k = k; apply(); };
  const center = id => {
    const n = pos[id]; if (!n) return;
    const W = svg.clientWidth, H = svg.clientHeight, narrow = innerWidth <= 820;
    if (S.k < 1.2) S.k = 1.5;
    S.tx = (narrow ? W / 2 : (W - 420) / 2) - cx(n) * S.k;
    S.ty = (narrow ? H * 0.2 : H / 2) - cy(n) * S.k; apply();
  };
  // ドラッグ移動・ホイール/ピンチ拡大
  const pts = new Map(); let moved = 0, pinch0 = null;
  svg.addEventListener('pointerdown', e => {
    pts.set(e.pointerId, [e.clientX, e.clientY]); moved = 0; svg.classList.add('drag');
    if (pts.size === 2) { const [a, b] = [...pts.values()]; pinch0 = Math.hypot(a[0] - b[0], a[1] - b[1]); }
  });
  svg.addEventListener('pointermove', e => {
    if (!pts.has(e.pointerId)) return;
    const [px, py] = pts.get(e.pointerId), dx = e.clientX - px, dy = e.clientY - py;
    pts.set(e.pointerId, [e.clientX, e.clientY]);
    if (pts.size === 2) {
      const [a, b] = [...pts.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]), r = svg.getBoundingClientRect();
      if (pinch0) zoomAt(d / pinch0, (a[0] + b[0]) / 2 - r.left, (a[1] + b[1]) / 2 - r.top);
      pinch0 = d; moved += 10; return;
    }
    if (Math.abs(dx) + Math.abs(dy) > 0 && moved + Math.abs(dx) + Math.abs(dy) > 5 && !svg.hasPointerCapture(e.pointerId)) svg.setPointerCapture(e.pointerId);
    moved += Math.abs(dx) + Math.abs(dy); S.tx += dx; S.ty += dy; apply();
  });
  const up = e => { pts.delete(e.pointerId); if (pts.size < 2) pinch0 = null; if (!pts.size) svg.classList.remove('drag'); };
  svg.addEventListener('pointerup', up); svg.addEventListener('pointercancel', up);
  svg.addEventListener('wheel', e => { e.preventDefault(); const r = svg.getBoundingClientRect(); zoomAt(Math.exp(-e.deltaY * 0.0015), e.clientX - r.left, e.clientY - r.top); }, { passive: false });
  svg.addEventListener('click', e => { if (moved > 5) return; const g = e.target.closest('.node'); selectNode(g ? g.dataset.id : null); });
  box.querySelector('.maptools').addEventListener('click', e => {
    const z = e.target.dataset.z; if (!z) return;
    if (z === 'fit') fit(); else zoomAt(z === 'in' ? 1.4 : 1 / 1.4, svg.clientWidth / 2, svg.clientHeight / 2);
  });
  box.querySelector('#lbl').onchange = e => { st.labels = e.target.checked; svg.classList.toggle('nolabel', !st.labels); save(); };

  function selectNode(id) {
    svg.querySelectorAll('.node').forEach(g => g.classList.toggle('sel', g.dataset.id === id));
    svg.querySelectorAll('.edge').forEach(l => {
      const on = !!id && (l.dataset.a === id || l.dataset.b === id);
      l.classList.toggle('hl', on); l.classList.toggle('dim', !!id && !on);
    });
    if (!id) { side.hidden = true; return; }
    const pre = ((Q[id] && Q[id].p) || []).map(p => p[0]), next = nextOf[id] || [];
    const link = k => {
      const ch = !pos[k] && CH.find(x => x.id === (mapOf[k] || qChapter[k]));
      return `<a href="#" data-go="${k}">${esc(qname(k))}${ch ? `<span class="other">（${esc(chName(ch))}）</span>` : ''}</a>`;
    };
    side.innerHTML = `<button class="btn x" data-close>✕</button>${qCard(id, idx[id], null, true)}
      <div class="rel">${pre.length ? `<h4>前提クエスト</h4>${pre.map(link).join('')}` : ''}${next.length ? `<h4>次に開くクエスト</h4>${next.map(link).join('')}` : ''}</div>`;
    side.hidden = false; side.scrollTop = 0;
  }
  side.addEventListener('click', e => {
    if (e.target.closest('[data-close]')) { selectNode(null); return; }
    const a = e.target.closest('[data-go]'); if (!a) return;
    e.preventDefault();
    const k = a.dataset.go;
    if (pos[k]) { selectNode(k); center(k); } else location.hash = 'm=' + k;
  });
  fit();
  if (focus && pos[focus]) { selectNode(focus); center(focus); }
}
'''


def rep(a, b):
    global h
    assert a in h, a[:70]
    h = h.replace(a, b, 1)


rep('@media (max-width:820px){\n  .layout{display:block}', css + '@media (max-width:820px){\n  .layout{display:block}')
rep("function route() {", js + "\nfunction route() {")

# 状態: view / labels を保存
rep("const st = { mode: 'ja', filt: '', ch: CH[0].id, q: '' };",
    "const st = { mode: 'ja', filt: '', ch: CH[0].id, q: '', view: 'list', labels: true };")
rep("if (s.mode) st.mode = s.mode;",
    "if (s.mode) st.mode = s.mode; if (s.view) st.view = s.view; if (s.labels === false) st.labels = false;")
rep("JSON.stringify({ mode: st.mode, theme:", "JSON.stringify({ mode: st.mode, view: st.view, labels: st.labels, theme:")

# 前提の逆引きとマップ所属
rep("const qChapter = {};",
    "const qChapter = {}, mapOf = {}, nextOf = {};\n"
    "CH.forEach(c => (c.map || []).forEach(n => { if (!(n[0] in mapOf)) mapOf[n[0]] = c.id; }));\n"
    "for (const k in Q) (Q[k].p || []).forEach(([p]) => (nextOf[p] = nextOf[p] || []).push(k));")

# 章表示: リスト/マップ切替
old = """  view.innerHTML = `<div class="chhead"><h2>${fmt(st.mode === 'en' && c.ne ? c.ne : c.nj)}</h2>${st.mode !== 'en' && c.ne ? `<div class="en">${esc(strip(c.ne))}</div>` : ''}</div>"""
new = """  const head = `<div class="chtop"><div class="chhead"><h2>${fmt(st.mode === 'en' && c.ne ? c.ne : c.nj)}</h2>${st.mode !== 'en' && c.ne ? `<div class="en">${esc(strip(c.ne))}</div>` : ''}</div>
    ${c.map ? `<div class="seg viewseg"><button data-v="list" class="${st.view !== 'map' ? 'on' : ''}">リスト</button><button data-v="map" class="${st.view === 'map' ? 'on' : ''}">マップ</button></div>` : ''}</div>`;
  if (c.map && st.view === 'map') {
    view.innerHTML = head + `<div class="meta">${n} クエスト ／ 公式訳 ${t - a} ／ AI訳 ${a} ／ 未訳 ${n - t} ／ ドラッグで移動・ホイールで拡大・クリックで詳細</div><div class="mapwrap"></div>`;
    window.scrollTo(0, 0); renderMap(c, focus); return;
  }
  view.innerHTML = head + `"""
rep(old, new)

rep("document.getElementById('filt').onchange",
    "view.addEventListener('click', e => { const b = e.target.closest('[data-v]'); if (!b) return; st.view = b.dataset.v; save(); renderChapter(); });\n"
    "document.getElementById('filt').onchange")

# ルーティング: #m=ID でマップ上のクエストを開く
rep("else if (h.startsWith('q=')) { focus = h.slice(2); if (qChapter[focus]) st.ch = qChapter[focus]; }",
    "else if (h.startsWith('q=')) { focus = h.slice(2); if (qChapter[focus]) st.ch = qChapter[focus]; st.view = 'list'; }\n"
    "  else if (h.startsWith('m=')) { focus = h.slice(2); if (mapOf[focus]) { st.ch = mapOf[focus]; st.view = 'map'; } }")

# カードに「マップで見る」
rep('<div class="qid">ID: ${id}</div>',
    '<div class="qid">ID: ${id}${mapOf[id] ? `<a class="tomap" href="#m=${id}">マップで見る</a>` : \'\'}</div>')

t.write_text(h, encoding='utf-8')
print('patched')
