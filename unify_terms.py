"""AI訳 (work/out/*.lang) 内の《訳／原文》表記の訳語ゆれを、最頻の訳に統一する。
  python unify_terms.py
"""
import re, glob, collections, sys
sys.stdout.reconfigure(encoding='utf-8')
PAT = re.compile(r'《((?:§.)*)([^《》／§]{1,30})((?:§.)*)／((?:§.)*)([^《》／]{1,40}?)((?:§.)*)》')
files = sorted(glob.glob('work/out/*.lang'))
pairs = collections.defaultdict(collections.Counter)
for f in files:
    for m in PAT.finditer(open(f, encoding='utf-8').read()):
        pairs[m.group(5).strip()][m.group(2).strip()] += 1
best = {en: c.most_common(1)[0][0] for en, c in pairs.items() if len(c) > 1}
n = 0
for f in files:
    s = open(f, encoding='utf-8').read()
    def rep(m):
        global n
        en, ja = m.group(5).strip(), m.group(2).strip()
        if en in best and ja != best[en]:
            n += 1
            return m.group(0).replace(m.group(2), best[en], 1)
        return m.group(0)
    s2 = PAT.sub(rep, s)
    if s2 != s: open(f, 'w', encoding='utf-8').write(s2)
print(f'variant terms={len(best)} replaced={n}')
