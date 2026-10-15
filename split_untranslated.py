"""未訳エントリを抽出して翻訳用チャンク (lang形式) と用語集を作る。
  python split_untranslated.py [チャンク数]
出力: work/in/chunkNN.lang, work/glossary.tsv
"""
import re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
KEY = re.compile(r'^(betterquesting\.\S+?\.(?:name|desc))=(.*)$')

def load(p):
    d = {}
    for l in open(p, encoding='utf-8-sig'):
        m = KEY.match(l.rstrip('\n'))
        if m: d[m.group(1)] = m.group(2)
    return d

n_chunks = int(sys.argv[1]) if len(sys.argv) > 1 else 16
ja, en = load(HERE/'src/ja_JP.lang'), load(HERE/'src/en_US.lang')
# en_US の並び (章順) を保ったまま、未訳エントリを抽出
items = [(k, v) for k, v in en.items() if v.strip() and ja.get(k) == v]
total = sum(len(v) for _, v in items)
target = total / n_chunks
chunks, cur, size = [], [], 0
for i, (k, v) in enumerate(items):
    cur.append((k, v)); size += len(v)
    nxt = items[i+1][0] if i+1 < len(items) else None
    same_quest = nxt and nxt.rsplit('.', 1)[0] == k.rsplit('.', 1)[0]
    if size >= target and not same_quest and len(chunks) < n_chunks - 1:
        chunks.append(cur); cur, size = [], 0
if cur: chunks.append(cur)
out = HERE/'work/in'
for f in out.glob('chunk*.lang'): f.unlink()
for n, c in enumerate(chunks, 1):
    (out/f'chunk{n:02d}.lang').write_text(''.join(f'{k}={v}\n' for k, v in c), encoding='utf-8')
    print(f'chunk{n:02d}: {len(c)} entries, {sum(len(v) for _, v in c)} chars')

# 既存訳の《訳／原文》表記から用語集を作る
pairs = {}
for v in ja.values():
    for a, b in re.findall(r'《(?:§r)?([^《》／]+?)(?:§7)?／([^《》／]+?)》', v):
        a, b = re.sub('§.', '', a).strip(), re.sub('§.', '', b).strip()
        if a and b and a != b:
            pairs.setdefault(b, {}).setdefault(a, 0); pairs[b][a] += 1
with open(HERE/'work/glossary.tsv', 'w', encoding='utf-8') as f:
    f.write('English\t日本語(既存訳での表記, 頻度順)\n')
    for en_t in sorted(pairs, key=str.lower):
        f.write(en_t + '\t' + ' / '.join(sorted(pairs[en_t], key=lambda x: -pairs[en_t][x])) + '\n')
print('glossary', len(pairs))
