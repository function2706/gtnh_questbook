"""lang のエスケープ (%n/%%/\\) をビルド時に解除する前提で、表示側を合わせるパッチ。
あわせて GTNH 独自の & 書式 (&g&#RRGGBB&#RRGGBB グラデーション, &#RRGGBB, &z, &q, &r) を表示する。
"""
from pathlib import Path

t = Path(__file__).resolve().parent.parent / 'template.html'
h = t.read_text(encoding='utf-8')


def rep(a, b):
    global h
    assert a in h, a[:70]
    h = h.replace(a, b, 1)


# 改行はビルド時に実際の改行へ変換済み
rep("  s = s.replace(/%n/g, '\\n');\n", "")
rep(".replace(/%n/g, ' ')", ".replace(/\\n/g, ' ')")

# & 書式を含めたトークン分割とスタイル
rep("""  let out = '', color = '', fl = new Set(), open = false;
  const openSpan = () => {
    const cls = []; if (color) cls.push('c'); fl.forEach(f => cls.push('f-' + f));
    if (cls.length) { out += `<span class="${[...fl].map(f => 'f-' + f).join(' ')}"${color ? ` style="color:var(--c${color})"` : ''}>`; open = true; }
  };""",
    """  // color: § の色コード(0-f) または &#RRGGBB、grad: &g / &z のグラデーション
  let out = '', color = '', grad = '', fl = new Set(), open = false;
  const openSpan = () => {
    const css = [];
    if (grad) css.push(`background-image:${grad};-webkit-background-clip:text;background-clip:text;color:transparent`);
    else if (color) css.push(color[0] === '#' ? `color:${color}` : `color:var(--c${color})`);
    if (css.length || fl.size) { out += `<span class="${[...fl].map(f => 'f-' + f).join(' ')}"${css.length ? ` style="${css.join(';')}"` : ''}>`; open = true; }
  };""")
rep("  const parts = s.split(/(<[^>]+>|\\n|§.)/);",
    "  const AMP = /^&amp;(?:g&amp;#([0-9A-Fa-f]{6})&amp;#([0-9A-Fa-f]{6})|#([0-9A-Fa-f]{6})|([zq])|r)$/;\n"
    "  const parts = s.split(/(<[^>]+>|\\n|§.|&amp;g&amp;#[0-9A-Fa-f]{6}&amp;#[0-9A-Fa-f]{6}|&amp;#[0-9A-Fa-f]{6}|&amp;[zq]|&amp;r(?=\\n|§|$))/);")
rep("""      if (/[0-9a-f]/.test(c)) { color = c; fl = new Set(); }
      else if (c === 'r') { color = ''; fl = new Set(); }""",
    """      if (/[0-9a-f]/.test(c)) { color = c; grad = ''; fl = new Set(); }
      else if (c === 'r') { color = ''; grad = ''; fl = new Set(); }""")
rep("    if (p === '\\n' || p[0] === '<') {",
    """    const am = p.startsWith('&amp;') && p.match(AMP);
    if (am) {
      close();
      if (am[1]) grad = `linear-gradient(90deg,#${am[1]},#${am[2]})`;
      else if (am[3]) { color = '#' + am[3]; grad = ''; }
      else if (am[4] === 'z') grad = 'linear-gradient(90deg,#e33,#e93,#cc3,#3b3,#3bc,#36e,#a3e)';
      else if (!am[4]) { color = ''; grad = ''; fl = new Set(); }  // &r
      continue;  // &q は表示上の意味が不明なので記号だけ除去
    }
    if (p === '\\n' || p[0] === '<') {""")

t.write_text(h, encoding='utf-8')
print('patched')
