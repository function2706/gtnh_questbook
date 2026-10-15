"""マップのタイトル表示を「画面上一定サイズ + 隙間に入る分だけ表示 + ホバーで全文」に変更するパッチ"""
from pathlib import Path

t = Path(__file__).resolve().parent.parent / 'template.html'
h = t.read_text(encoding='utf-8')


def rep(a, b):
    global h
    assert a in h, a[:70]
    h = h.replace(a, b, 1)


# CSS: ラベルの固定フォント指定をやめ、ホバー用ツールチップを追加
rep(".node .lb{font-size:8px;fill:var(--text);text-anchor:middle;pointer-events:none;paint-order:stroke;stroke:var(--panel);stroke-width:3px;stroke-linejoin:round}\n"
    "svg.nolabel .lb, svg.far .lb{display:none}",
    ".node .lb{fill:var(--text);text-anchor:middle;pointer-events:none;paint-order:stroke;stroke:var(--panel);stroke-linejoin:round}\n"
    "svg.nolabel .lb{display:none}\n"
    ".maptip{position:absolute;z-index:4;pointer-events:none;background:var(--text);color:var(--bg);font-size:12px;line-height:1.4;padding:3px 8px;border-radius:5px;max-width:260px;transform:translate(-50%,0);white-space:normal}\n"
    ".maptip[hidden]{display:none}")

# ラベル文字列は後から配置計算で入れる
rep("  const label = id => { const s = qname(id); return s.length > 14 ? s.slice(0, 13) + '…' : s; };\n", "")
rep('<text class="lb" x="${x + w / 2}" y="${y + hh + 9}">${esc(label(id))}</text></g>`;',
    '<text class="lb" x="${x + w / 2}"></text></g>`;')
rep('<g class="vp">${edgeSvg}${nodeSvg}</g></svg><aside class="mapside" hidden></aside>`;',
    '<g class="vp">${edgeSvg}${nodeSvg}</g></svg><div class="maptip" hidden></div><aside class="mapside" hidden></aside>`;')

# 拡大率に応じてラベルを再配置
rep("  const apply = () => { vp.setAttribute('transform', `translate(${S.tx},${S.ty}) scale(${S.k})`); svg.classList.toggle('far', S.k < 0.75); };",
    r"""  // ---- タイトル: 画面上 11px 固定。周囲のノード/ラベルと重ならない幅だけ表示し、入らない分は … で省略 ----
  const FS = 11, LH = 14, MAXW = 150;
  const items = [...vp.querySelectorAll('.node')].map(g => {
    const n = pos[g.dataset.id];
    return { el: g.querySelector('.lb'), name: qname(n[0]), cx: cx(n), x: n[1], y: n[2], w: n[3], h: n[4] };
  });
  const textW = s => { let w = 0; for (const ch of s) w += ch.charCodeAt(0) > 0x2e7f ? 1 : 0.58; return w; };  // em 単位
  const fitText = (s, em) => {
    if (textW(s) <= em) return s;
    let out = '', w = 0;
    for (const ch of s) { const cw = ch.charCodeAt(0) > 0x2e7f ? 1 : 0.58; if (w + cw > em - 1) break; out += ch; w += cw; }
    return out ? out + '…' : '';
  };
  let lblTimer = 0, lastK = 0;
  function layoutLabels() {
    if (!st.labels || Math.abs(S.k - lastK) < 1e-6) return;
    lastK = S.k;
    const k = S.k, fs = FS / k, band = LH / k, gapPad = 4 / k;
    for (const a of items) {
      const top = a.y + a.h + 1 / k, bot = top + band;
      let half = MAXW / 2 / k;
      for (const b of items) {
        if (b === a) continue;
        const dx = Math.abs(b.cx - a.cx);
        if (dx > half * 2 + b.w) continue;
        // 下にあるノード本体とぶつかる範囲
        if (b.y < bot && b.y + b.h > top) half = Math.min(half, dx - b.w / 2 - gapPad);
        // 同じ段のラベル同士は隙間を半分ずつ使う
        const bt = b.y + b.h + 1 / k;
        if (bt < bot && bt + band > top) half = Math.min(half, dx / 2 - gapPad);
      }
      const txt = half > 0 ? fitText(a.name, half * 2 / fs) : '';
      a.el.textContent = txt.length >= 2 ? txt : '';
      a.el.setAttribute('y', top + fs * 0.95);
      a.el.setAttribute('font-size', fs);
      a.el.setAttribute('stroke-width', 3 / k);
    }
  }
  const apply = () => {
    vp.setAttribute('transform', `translate(${S.tx},${S.ty}) scale(${S.k})`);
    clearTimeout(lblTimer); lblTimer = setTimeout(layoutLabels, 80);
  };""")

rep("box.querySelector('#lbl').onchange = e => { st.labels = e.target.checked; svg.classList.toggle('nolabel', !st.labels); save(); };",
    "box.querySelector('#lbl').onchange = e => { st.labels = e.target.checked; svg.classList.toggle('nolabel', !st.labels); lastK = 0; layoutLabels(); save(); };\n"
    "  // ホバーでタイトル全文\n"
    "  const tip = box.querySelector('.maptip');\n"
    "  svg.addEventListener('pointerover', e => {\n"
    "    const g = e.target.closest('.node'); if (!g || e.pointerType === 'touch') { tip.hidden = true; return; }\n"
    "    const r = g.querySelector('rect').getBoundingClientRect(), b = box.getBoundingClientRect();\n"
    "    tip.textContent = qname(g.dataset.id); tip.hidden = false;\n"
    "    tip.style.left = (r.left + r.width / 2 - b.left) + 'px'; tip.style.top = (r.bottom - b.top + 4) + 'px';\n"
    "  });\n"
    "  svg.addEventListener('pointerout', e => { if (e.target.closest('.node')) tip.hidden = true; });\n"
    "  svg.addEventListener('pointerdown', () => { tip.hidden = true; });")

# ネイティブの title ツールチップはカスタムと二重になるので外す
rep('<g class="node s${s}${show ? \'\' : \' dim\'}" data-id="${id}"><title>${esc(qname(id))}</title>',
    '<g class="node s${s}${show ? \'\' : \' dim\'}" data-id="${id}">')

t.write_text(h, encoding='utf-8')
print('patched')
