"""lang ファイル内のエスケープ/特殊記法の出現状況を調べる"""
import collections
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
BS = "\\"
PATS = {
    "%%": r"%%",
    "%n": r"%n",
    "%その他": r"%[^n%]",
    "&amp;等": r"&[a-z]+;",
    "&#数字;": r"&#\d+;",
    "&(単体)": r"&(?![a-z]+;|#\d+;)",
    BS + "n": re.escape(BS) + "n",
    BS + "uXXXX": re.escape(BS) + r"u[0-9a-fA-F]{4}",
    BS + BS: re.escape(BS) * 2,
    BS + "その他": re.escape(BS) + r"[^nu" + re.escape(BS) + "]",
    "<タグ": r"<[a-zA-Z/]",
}
for fn in sys.argv[1:]:
    vals = [l.split("=", 1)[1] for l in open(fn, encoding="utf-8").read().splitlines()
            if l.startswith("betterquesting.") and "=" in l]
    text = "\n".join(vals)
    print("==", fn)
    for name, pat in PATS.items():
        hits = re.findall(pat, text)
        if not hits:
            continue
        ex = re.findall(r".{0,20}(?:" + pat + r").{0,12}", text)[:3]
        print(f"  {name:10} {len(hits):6}  例: {ex}")
