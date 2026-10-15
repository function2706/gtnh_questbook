"""クエストカードに 課題/必要アイテム・報酬・前提/後続 を表示し、表示の有無をオプションで切り替えるパッチ"""
from pathlib import Path

t = Path(__file__).resolve().parent.parent / 'template.html'
h = t.read_text(encoding='utf-8')


def rep(a, b):
    global h
    assert a in h, a[:70]
    h = h.replace(a, b, 1)


css = r'''
/* ---- 課題・報酬・前提 ---- */
.opts{position:relative}
.opts>summary{list-style:none;cursor:pointer}
.opts>summary::-webkit-details-marker{display:none}
.opts .menu{position:absolute;right:0;top:calc(100% + 4px);z-index:10;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:8px 12px;box-shadow:0 4px 14px rgba(0,0,0,.12);display:flex;flex-direction:column;gap:4px;white-space:nowrap}
.xinfo{margin-top:12px;display:grid;gap:10px}
.xsec{border:1px solid var(--line);border-radius:8px;padding:8px 12px;background:var(--bg)}
.xsec h5{margin:0 0 4px;font-size:12px;color:var(--muted);font-weight:600;letter-spacing:.04em}
.xsec h5 .logic{font-weight:normal;margin-left:6px}
.task{margin:4px 0;font-size:14px}
.tag{display:inline-block;font-size:11px;line-height:1.5;padding:0 6px;border-radius:9px;border:1px solid var(--line);color:var(--muted);margin-right:4px;vertical-align:1px}
.tag.req{border-color:var(--accent);color:var(--accent)}
.tag.opt{border-color:var(--c9);color:var(--c9)}
.tag.use{border-color:var(--c4);color:var(--c4)}
.items{display:flex;flex-wrap:wrap;gap:4px 6px;margin:3px 0 0}
.it{display:inline-flex;align-items:baseline;gap:4px;font-size:13px;background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:1px 7px;max-width:100%;overflow-wrap:anywhere}
.it .n{font-variant-numeric:tabular-nums;color:var(--muted)}
.it.raw .nm2{font-family:ui-monospace,Consolas,monospace;font-size:12px}
.it .mod{font-size:10px;color:var(--muted)}
.rels{display:grid;grid-template-columns:1fr 1fr;gap:4px 16px;font-size:13px}
.rels a{display:block;text-decoration:none;padding:1px 0}
.rels .none{color:var(--muted)}
.rels .other{color:var(--muted);font-size:11px;margin-left:4px}
@media (max-width:820px){ .rels{grid-template-columns:1fr} }
'''
rep("/* ---- クエストマップ ---- */", css + "\n/* ---- クエストマップ ---- */")

# ヘッダーに表示項目メニュー
rep('<button class="btn" id="theme" title="テーマ切替">◐</button>',
    '<details class="opts"><summary class="btn">表示項目 ▾</summary><div class="menu">'
    '<label><input type="checkbox" data-opt="task"> 課題・必要アイテム</label>'
    '<label><input type="checkbox" data-opt="reward"> 報酬</label>'
    '<label><input type="checkbox" data-opt="rel"> 前提・後続クエスト</label>'
    '</div></details>\n    <button class="btn" id="theme" title="テーマ切替">◐</button>')

# 状態と保存
rep("labels: true, scope: 'all' };", "labels: true, scope: 'all', show: { task: true, reward: true, rel: true } };")
rep("if (s.labels === false) st.labels = false;", "if (s.labels === false) st.labels = false; if (s.show) Object.assign(st.show, s.show);")
rep("JSON.stringify({ mode: st.mode, view: st.view, labels: st.labels,", "JSON.stringify({ mode: st.mode, view: st.view, labels: st.labels, show: st.show,")

js = r'''
// ---- 課題・報酬・前提/後続 ----
const REG = D.reg || [], NAMES = D.names || {};
const MOB = { Pig: '豚', Cow: '牛', Sheep: '羊', Chicken: 'ニワトリ', Squid: 'イカ', Bat: 'コウモリ', Zombie: 'ゾンビ', Skeleton: 'スケルトン',
  Spider: 'クモ', Creeper: 'クリーパー', Enderman: 'エンダーマン', Blaze: 'ブレイズ', Ghast: 'ガスト', Slime: 'スライム', LavaSlime: 'マグマキューブ',
  Witch: 'ウィッチ', PigZombie: 'ゾンビピッグマン', Silverfish: 'シミ', WitherBoss: 'ウィザー', EnderDragon: 'エンダードラゴン' };
const DIM = { 0: 'オーバーワールド', '-1': 'ネザー', 1: 'ジ・エンド', 7: '黄昏の森' };
function itemHtml(e) {
  const [ri, dmg = 0, cnt = 1, od = '', nbt = ''] = e, reg = REG[ri] || '?';
  const full = `${reg}:${dmg}`, named = NAMES[`${reg}@${dmg}`] || (nbt && strip(nbt));
  let label, raw = false, mod = '';
  if (named) label = esc(named);
  else if (od) label = `鉱石辞書 <b>${esc(od)}</b>`;
  else { const [m, ...rest] = reg.split(':'); mod = m; raw = true;
    label = esc(rest.join(':') || reg) + (dmg === 32767 ? ' (全種)' : dmg ? `:${dmg}` : ''); }
  return `<span class="it${raw ? ' raw' : ''}" title="${esc(full)}"><span class="nm2">${label}</span>${mod ? `<span class="mod">${esc(mod)}</span>` : ''}<span class="n">×${cnt}</span></span>`;
}
const itemsHtml = list => `<div class="items">${(list || []).map(itemHtml).join('')}</div>`;
const entName = s => { const [a, b] = s.includes('.') ? [s.slice(0, s.indexOf('.')), s.slice(s.indexOf('.') + 1)] : ['', s];
  return MOB[s] ? `${MOB[s]} <span class="mod">${esc(s)}</span>` : `${esc(b)}${a ? ` <span class="mod">${esc(a)}</span>` : ''}`; };
function taskHtml(t) {
  switch (t.k) {
    case 'item': return `<div class="task">${t.opt ? '<span class="tag opt">任意</span>' : '<span class="tag req">必須</span>'}`
      + `アイテム提出${t.use ? '<span class="tag use">消費</span>' : '<span class="tag">消費なし</span>'}${t.one ? '<span class="tag">いずれか1つ</span>' : ''}${itemsHtml(t.i)}</div>`;
    case 'craft': return `<div class="task"><span class="tag req">必須</span>クラフト${itemsHtml(t.i)}</div>`;
    case 'check': return `<div class="task"><span class="tag">☑</span>チェックボックス（読んで確認するだけ）</div>`;
    case 'hunt': return `<div class="task"><span class="tag req">必須</span>討伐: ${entName(t.e)} ×${t.n}</div>`;
    case 'meeting': return `<div class="task"><span class="tag req">必須</span>接触: ${entName(t.e)} ×${t.n}</div>`;
    case 'loc': return `<div class="task"><span class="tag req">必須</span>到達: ${t.hide ? '（非公開）' : `${esc(strip(t.name))} <span class="mod">${esc(DIM[t.dim] || 'ディメンション ' + t.dim)}</span>`}</div>`;
    case 'fluid': return `<div class="task"><span class="tag req">必須</span>液体提出${t.use ? '<span class="tag use">消費</span>' : '<span class="tag">消費なし</span>'}<div class="items">`
      + t.f.map(([n, a]) => `<span class="it raw"><span class="nm2">${esc(n)}</span><span class="n">${a.toLocaleString()} mB</span></span>`).join('') + '</div></div>';
    default: return `<div class="task">${esc(t.name || t.k)}</div>`;
  }
}
const qLink = k => { const ch = CH.find(x => x.id === (mapOf[k] || qChapter[k]));
  return `<a href="#q=${k}" data-go="${k}">${esc(strip(Q[k] ? (st.mode === 'en' ? Q[k].ne : (Q[k].nj || Q[k].ne)) : k))}${ch ? `<span class="other">（${esc(chName(ch))}）</span>` : ''}</a>`; };
function rewardHtml(r) {
  switch (r.k) {
    case 'item': return `<div class="task">アイテム${itemsHtml(r.i)}</div>`;
    case 'choice': return `<div class="task">選択式<span class="tag">1つ選ぶ</span>${itemsHtml(r.i)}</div>`;
    case 'xp': return `<div class="task">経験値 ${r.n}${r.lv ? ' レベル' : ' ポイント'}</div>`;
    case 'qc': return `<div class="task">クエスト完了: ${Q[r.q] ? qLink(r.q) : esc(r.q)}</div>`;
    default: return `<div class="task">${esc(r.name || r.k)}</div>`;
  }
}
function extraHtml(id) {
  const q = Q[id], d = q && q.d, out = [];
  if (st.show.task && d && d.t.length)
    out.push(`<div class="xsec"><h5>課題${d.or ? '<span class="logic tag">いずれか1つで達成</span>' : d.t.length > 1 ? '<span class="logic tag">すべて達成</span>' : ''}</h5>${d.t.map(taskHtml).join('')}</div>`);
  if (st.show.reward && d && d.r.length)
    out.push(`<div class="xsec"><h5>報酬</h5>${d.r.map(rewardHtml).join('')}</div>`);
  if (st.show.rel) {
    const pre = ((q && q.p) || []).map(p => p[0]), next = nextOf[id] || [];
    if (pre.length || next.length)
      out.push(`<div class="xsec"><div class="rels"><div><h5>前提クエスト</h5>${pre.map(qLink).join('') || '<span class="none">なし</span>'}</div>`
        + `<div><h5>後続クエスト</h5>${next.map(qLink).join('') || '<span class="none">なし</span>'}</div></div></div>`);
  }
  return out.length ? `<div class="xinfo">${out.join('')}</div>` : '';
}
'''
rep("function qCard(id, idx, hl, openIt, snip) {", js + "\nfunction qCard(id, idx, hl, openIt, snip) {")

# カード本文の後ろに追加情報
rep('<div class="body">${body}<div class="qid">', '<div class="body">${body}${extraHtml(id)}<div class="qid">')

# マップの詳細パネルは前提/後続をカード側に任せる
rep("""${qCard(id, idx[id], null, true)}
      <div class="rel">${pre.length ? `<h4>前提クエスト</h4>${pre.map(link).join('')}` : ''}${next.length ? `<h4>次に開くクエスト</h4>${next.map(link).join('')}` : ''}</div>`;""",
    """${qCard(id, idx[id], null, true)}`;""")

# 表示項目の切り替え
rep("document.getElementById('scope').onchange",
    "document.querySelectorAll('[data-opt]').forEach(cb => {\n"
    "  cb.checked = st.show[cb.dataset.opt];\n"
    "  cb.onchange = () => { st.show[cb.dataset.opt] = cb.checked; save(); rerender(); };\n"
    "});\n"
    "document.addEventListener('click', e => { const o = document.querySelector('.opts'); if (o.open && !o.contains(e.target)) o.open = false; });\n"
    "document.getElementById('scope').onchange")

t.write_text(h, encoding='utf-8')
print('patched')
