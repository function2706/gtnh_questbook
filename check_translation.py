"""翻訳チャンクの検証。
  python check_translation.py 05        # work/in/chunk05.lang と work/out/chunk05*.lang を照合
  python check_translation.py zz_upd20261101   # バージョン更新分 (work/in/zz_*.lang)
  python check_translation.py all
キー欠落・余分なキー・書式トークン(§コード/%n/[タグ]/URL/questlink)の不一致を報告する。
"""
import re, sys
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
KEY = re.compile(r'^(betterquesting\.\S+?\.(?:name|desc))=(.*)$')

def load(p):
    d = {}
    for l in open(p, encoding='utf-8-sig'):
        m = KEY.match(l.rstrip('\n'))
        if m: d[m.group(1)] = m.group(2)
    return d

def tokens(s):
    c = Counter(re.findall(r'\[/?[a-z]+\]', s))
    c['%n'] = s.count('%n')
    c.update('URL:' + u for u in re.findall(r'\[url\](.*?)\[/url\]', s))
    c.update('QL:' + u for u in re.findall(r'\[questlink\](.*?)\[/questlink\]', s))
    return c

def check(n):
    # 数字ならチャンク番号 (chunkNN)、それ以外はファイル名 (例: zz_upd20261101) として扱う
    name = f'chunk{n}' if n.isdigit() else n
    src = load(HERE/f'work/in/{name}.lang')
    out = {}
    for f in sorted((HERE/'work/out').glob(f'{name}*.lang')):
        out.update(load(f))
    missing = [k for k in src if k not in out]
    extra = [k for k in out if k not in src]
    bad = []
    for k, v in src.items():
        if k not in out: continue
        a, b = tokens(v), tokens(out[k])
        if a != b:
            diff = {t: (a[t], b[t]) for t in set(a) | set(b) if a[t] != b[t]}
            bad.append((k, diff))
        elif not re.search(r'[぀-ヿ一-鿿]', out[k]) and re.search(r'[A-Za-z]{4,} [A-Za-z]{3,} [A-Za-z]{3,}', re.sub('§.', '', v)):
            bad.append((k, '日本語が含まれていない (未翻訳?)'))
    print(f'{name}: src={len(src)} out={len(out)} missing={len(missing)} extra={len(extra)} format_errors={len(bad)}')
    for k in missing[:20]: print('  MISSING', k)
    for k in extra[:20]: print('  EXTRA', k)
    for k, d in bad[:30]: print('  BAD', k, d)
    return not (missing or extra or bad)

args = sys.argv[1:] or ['all']
if args == ['all']:
    ns = sorted(p.stem[5:] for p in (HERE/'work/in').glob('chunk*.lang'))
    ns += sorted(p.stem for p in (HERE/'work/in').glob('zz_*.lang'))  # バージョン更新分
else:
    ns = [a.zfill(2) if a.isdigit() else a for a in args]
ok = all([check(n) for n in ns])
print('OK' if ok else 'NG')
