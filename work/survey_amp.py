import re, sys, collections
sys.stdout.reconfigure(encoding="utf-8")
for fn in sys.argv[1:]:
    text = "\n".join(l.split("=", 1)[1] for l in open(fn, encoding="utf-8").read().splitlines() if l.startswith("betterquesting.") and "=" in l)
    c = collections.Counter(m.group(0)[:3] for m in re.finditer(r"&.", text))
    print("==", fn, c.most_common(15))
    for pat in [r"&#[0-9A-Fa-f]{6}", r"&[0-9a-fk-or](?=[^a-z ])", r"&g"]:
        ex = re.findall(r".{0,15}(?:" + pat + r").{0,25}", text)[:3]
        print("  ", pat, len(re.findall(pat, text)), ex)
