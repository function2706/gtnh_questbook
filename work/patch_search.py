"""検索結果に本文スニペット・ヒット数・検索範囲切替を追加するパッチ"""
from pathlib import Path

t = Path(__file__).resolve().parent.parent / 'template.html'
h = t.read_text(encoding='utf-8')


def rep(a, b):
    global h
    assert a in h, a[:70]
    h = h.replace(a, b, 1)


# CSS
rep(".hit .where{font-size:12px;color:var(--muted)}",
    ".hit .where{font-size:12px;color:var(--muted)}\n"
    ".snip{display:block;font-weight:normal;font-size:13px;color:var(--muted);margin-top:3px;line-height:1.6}\n"
    ".snip mark{color:var(--text)}\n"
    ".snip .lang{font-size:11px;border:1px solid var(--line);border-radius:4px;padding:0 4px;margin-right:4px}\n"
    "#scope{padding:4px 6px}")

# 検索範囲の切替
rep('<select id="filt" class="btn">',
    '<select id="scope" class="btn" title="検索範囲"><option value="all">タイトル＋本文</option><option value="title">タイトルのみ</option></select>\n    <select id="filt" class="btn">')
rep("const st = { mode: 'ja', filt: '', ch: CH[0].id, q: '', view: 'list', labels: true };",
    "const st = { mode: 'ja', filt: '', ch: CH[0].id, q: '', view: 'list', labels: true, scope: 'all' };")
rep("document.getElementById('filt').onchange",
    "document.getElementById('scope').onchange = e => { st.scope = e.target.value; if (st.q.trim()) renderSearch(); };\n"
    "document.getElementById('filt').onchange")

# qCard: 見出しにスニペットを差し込めるようにする
rep("function qCard(id, idx, hl, openIt) {", "function qCard(id, idx, hl, openIt, snip) {")
rep('<span class="nm">${fmt(nmMain, hl)}${sub}</span>', '<span class="nm">${fmt(nmMain, hl)}${sub}${snip || \'\'}</span>')

# 検索本体を差し替え
start = h.index("function renderSearch() {")
end = h.index("// ---- クエストマップ ----")
h = h[:start] + r'''// 検索用のプレーンテキスト: 書式コード・タグを除き、改行は空白に
const plain = s => (s || '').replace(/§./g, '').replace(/%n/g, ' ').replace(/\[\/?[a-z]+\]/g, '').replace(/\s+/g, ' ').trim();
const reEsc = w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

// 本文からヒット箇所の前後を最大 2 か所抜き出す
function snippets(text, hl, max = 2, span = 36) {
  const out = []; let m, last = -1; hl.lastIndex = 0;
  while ((m = hl.exec(text)) && out.length < max) {
    if (m.index < last) continue;
    const a = Math.max(0, m.index - span), b = Math.min(text.length, m.index + m[0].length + span);
    out.push((a > 0 ? '…' : '') + esc(text.slice(a, b)).replace(new RegExp(hl.source, 'gi'), x => `<mark>${x}</mark>`) + (b < text.length ? '…' : ''));
    last = b;
  }
  return out;
}
const countHits = (text, re) => { re.lastIndex = 0; return (text.match(re) || []).length; };

function renderSearch() {
  const words = st.q.trim().split(/\s+/).filter(Boolean);
  const res = words.map(w => new RegExp(reEsc(w), 'gi'));
  const hl = new RegExp(words.map(reEsc).join('|'), 'gi');
  const titleOnly = st.scope === 'title';
  const hits = [];
  for (const c of CH) for (const id of c.q) {
    if (qChapter[id] !== c.id || !pass(id)) continue;
    const q = Q[id];
    const title = plain(q.nj) + ' ' + plain(q.ne);
    const body = { ja: plain(q.dj), en: plain(q.de) };
    const hay = titleOnly ? title : title + ' ' + body.ja + ' ' + body.en;
    if (!res.every(r => { r.lastIndex = 0; return r.test(hay); })) continue;
    const nameHit = res.some(r => { r.lastIndex = 0; return r.test(title); });
    // 表示中の言語の本文を優先してヒット数とスニペットを出す
    const langs = st.mode === 'en' ? ['en', 'ja'] : st.mode === 'both' ? ['ja', 'en'] : ['ja', 'en'];
    let n = 0, snip = '';
    if (!titleOnly) {
      for (const L of langs) {
        const k = countHits(body[L], hl);
        if (!k) continue;
        n += k;
        if (!snip) {
          const tag = (st.mode === 'en' && L === 'ja') || (st.mode !== 'en' && L === 'en') ? `<span class="lang">${L === 'en' ? '英語' : '日本語'}</span>` : '';
          snip = snippets(body[L], hl).map(s => `<span class="snip">${tag}${s}</span>`).join('');
        }
        if (st.mode !== 'both') break;
      }
    }
    hits.push({ nameHit, n, c, id, snip });
  }
  hits.sort((a, b) => (b.nameHit - a.nameHit) || (b.n - a.n));
  const LIM = 200, nTitle = hits.filter(x => x.nameHit).length;
  view.innerHTML = `<div class="chhead"><h2>検索: ${esc(st.q)}</h2></div>
    <div class="meta">${hits.length} 件（タイトル一致 ${nTitle} ／ 本文のみ一致 ${hits.length - nTitle}）${hits.length > LIM ? ` ／ 上位 ${LIM} 件を表示` : ''}${titleOnly ? ' ／ 検索範囲: タイトルのみ' : ''}</div>` +
    (hits.slice(0, LIM).map(x => `<div class="hit"><div class="where">${esc(chName(x.c))}${x.n ? ` ・ 本文 ${x.n} か所` : ''}</div>${qCard(x.id, null, hl, false, x.snip)}</div>`).join('') || '<div class="empty">見つかりませんでした</div>');
  window.scrollTo(0, 0);
}


''' + h[end:]

t.write_text(h, encoding='utf-8')
print('patched')
