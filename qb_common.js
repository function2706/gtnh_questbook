/* GTNH クエストブック 共通処理 (閲覧ページ・進行ページで共有)
 * 前提: questdata.js (window.QDATA) を先に読み込むこと。
 * ページ側で st (mode/show) と chName(c) を定義すること。
 */
const D = window.QDATA;
const Q = D.quests, CH = D.chapters;

// 旧形式 (標準base64) のクエストIDを lang 側の URL-safe 形式へ
const normId = s => s.trim().replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_');
const qChapter = {}, mapOf = {}, nextOf = {};
CH.forEach(c => (c.map || []).forEach(n => { if (!(n[0] in mapOf)) mapOf[n[0]] = c.id; }));
for (const k in Q) (Q[k].p || []).forEach(([p]) => (nextOf[p] = nextOf[p] || []).push(k));
CH.forEach(c => c.q.forEach(id => { if (!(id in qChapter)) qChapter[id] = c.id; }));
const esc = s => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const strip = s => s.replace(/§./g, '');

// Minecraft の書式コード + BetterQuesting のタグを HTML に変換
function fmt(raw, hl) {
  if (!raw) return '';
  let s = esc(raw);
  s = s.replace(/\[url\]([\s\S]*?)\[\/url\]/g, (m, u) => `<a href="${u.replace(/§./g, '')}" target="_blank" rel="noopener">${u}</a>`);
  s = s.replace(/\[questlink\]([\s\S]*?)\[\/questlink\]/g, (m, id) => {
    const k = normId(id.replace(/§./g, '')), q = Q[k];
    return q ? `<a class="qref" href="#q=${k}">「${esc(strip(q.nj || q.ne))}」</a>` : `[quest ${id}]`;
  });
  s = s.replace(/\[quest\]([\s\S]*?)\[\/quest\]/g, '<span class="qref">「$1」</span>');
  s = s.replace(/\[(\/?)(bold)\]/g, (m, c) => c ? '</b>' : '<b>');
  s = s.replace(/\[note\]/g, '<span class="note">').replace(/\[\/note\]/g, '</span>');
  s = s.replace(/\[warn\]/g, '<span class="warn">').replace(/\[\/warn\]/g, '</span>');
  // § コード: 色/装飾をspanで表現。タグ境界を壊さないよう、HTMLタグ・改行ごとにリセット
  // color: § の色コード(0-f) または &#RRGGBB、grad: &g / &z のグラデーション
  let out = '', color = '', grad = '', fl = new Set(), open = false;
  const openSpan = () => {
    const css = [];
    if (grad) css.push(`background-image:${grad};-webkit-background-clip:text;background-clip:text;color:transparent`);
    else if (color) css.push(color[0] === '#' ? `color:${color}` : `color:var(--c${color})`);
    if (css.length || fl.size) { out += `<span class="${[...fl].map(f => 'f-' + f).join(' ')}"${css.length ? ` style="${css.join(';')}"` : ''}>`; open = true; }
  };
  const close = () => { if (open) { out += '</span>'; open = false; } };
  const AMP = /^&amp;(?:g&amp;#([0-9A-Fa-f]{6})&amp;#([0-9A-Fa-f]{6})|#([0-9A-Fa-f]{6})|([zq])|r)$/;
  const parts = s.split(/(<[^>]+>|\n|§.|&amp;g&amp;#[0-9A-Fa-f]{6}&amp;#[0-9A-Fa-f]{6}|&amp;#[0-9A-Fa-f]{6}|&amp;[zq]|&amp;r(?=\n|§|$))/);
  for (const p of parts) {
    if (!p) continue;
    if (p[0] === '§' && p.length === 2) {
      const c = p[1].toLowerCase();
      close();
      if (/[0-9a-f]/.test(c)) { color = c; grad = ''; fl = new Set(); }
      else if (c === 'r') { color = ''; grad = ''; fl = new Set(); }
      else if ('klmno'.includes(c)) fl.add(c);
      continue;
    }
    const am = p.startsWith('&amp;') && p.match(AMP);
    if (am) {
      close();
      if (am[1]) grad = `linear-gradient(90deg,#${am[1]},#${am[2]})`;
      else if (am[3]) { color = '#' + am[3]; grad = ''; }
      else if (am[4] === 'z') grad = 'linear-gradient(90deg,#e33,#e93,#cc3,#3b3,#3bc,#36e,#a3e)';
      else if (!am[4]) { color = ''; grad = ''; fl = new Set(); }  // &r
      continue;  // &q は表示上の意味が不明なので記号だけ除去
    }
    if (p === '\n' || p[0] === '<') { close(); out += p === '\n' ? '<br>' : p; continue; }
    if (!open) openSpan();
    out += hl ? highlight(p, hl) : p;
  }
  close();
  return out;
}
function highlight(text, re) { return text.replace(re, m => `<mark>${m}</mark>`); }

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

