"""GTNH クエストブック 日本語訳ビューア (単一HTML) 生成スクリプト
公式訳が未訳の箇所は work/out/*.lang (AI訳) で補完する。

データ元: GTNewHorizons/GTNH-Translations (GPL-3.0)
         GTNewHorizons/GT-New-Horizons-Modpack (クエスト配置・前提。src/modpack に sparse clone:
           git clone --depth 1 --filter=blob:none --sparse https://github.com/GTNewHorizons/GT-New-Horizons-Modpack.git src/modpack
           git -C src/modpack sparse-checkout set config/betterquesting/DefaultQuests)
  ja: ja_JP/config/txloader/forceload/betterquesting/lang/ja_JP.lang
  en: daily-history/config/txloader/forceload/betterquesting/lang/en_US.lang

使い方:
  python build_questbook_html.py            # GitHub から最新を取得して生成
  python build_questbook_html.py ja.lang en.lang   # ローカルファイルから生成
"""
import base64
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

BASE = "https://raw.githubusercontent.com/GTNewHorizons/GTNH-Translations/master/"
JA_PATH = "ja_JP/config/txloader/forceload/betterquesting/lang/ja_JP.lang"
EN_PATH = "daily-history/config/txloader/forceload/betterquesting/lang/en_US.lang"
HERE = Path(__file__).resolve().parent
OUT = HERE / "GTNH_QuestBook_ja.html"
TEMPLATE = HERE / "template.html"
# クエストマップ用: GT-New-Horizons-Modpack の config/betterquesting/DefaultQuests (sparse clone)
QUESTDB = HERE / "src" / "modpack" / "config" / "betterquesting" / "DefaultQuests"

KEY_RE = re.compile(r"^betterquesting\.(quest|questline)\.([^.]+)\.(name|desc)=(.*)$")
FULLWIDTH = str.maketrans("０１２３４５６７８９ａｂｃｄｅｆｋｌｍｎｏｒ", "0123456789abcdefklmnor")


def read_text(src):
    if src.startswith("http"):
        with urllib.request.urlopen(src) as r:
            return r.read().decode("utf-8-sig")
    return Path(src).read_text(encoding="utf-8-sig")


def norm(v):
    # 全角の書式コード (§７ など) を半角に揃える
    return re.sub(r"§(.)", lambda m: "§" + m.group(1).translate(FULLWIDTH), v)


def parse(text):
    """lang を (値辞書, 章リスト) に分解する。章構成はコメント行から復元。"""
    values, chapters, cur = {}, [], None
    for line in text.splitlines():
        if line.startswith("### Quests in multiple quest lines"):
            cur = {"id": "_multi", "quests": [], "special": "複数の章にまたがるクエスト"}
            chapters.append(cur)
        elif line.startswith("### Quests in no quest lines"):
            cur = {"id": "_none", "quests": [], "special": "どの章にも属さないクエスト"}
            chapters.append(cur)
        m = KEY_RE.match(line)
        if not m:
            continue
        kind, qid, field, val = m.groups()
        values[(kind, qid, field)] = norm(val)
        if kind == "questline" and (cur is None or cur["id"] != qid):
            cur = {"id": qid, "quests": []}
            chapters.append(cur)
        elif kind == "quest" and cur is not None and qid not in cur["quests"]:
            cur["quests"].append(qid)
    return values, chapters


def bq_id(high, low):
    """BetterQuesting の (high, low) 64bit 対を lang 側の URL-safe base64 ID に変換"""
    n = ((high & (2**64 - 1)) << 64) | (low & (2**64 - 1))
    return base64.urlsafe_b64encode(n.to_bytes(16, "big")).decode().rstrip("=")


def load_map():
    """章ごとのクエスト配置と、クエストごとの前提クエストを読む。無ければ空。"""
    if not QUESTDB.exists():
        return {}, {}
    layout = {}
    for d in (QUESTDB / "QuestLines").iterdir():
        head = json.loads((d / "QuestLine.json").read_text(encoding="utf-8"))
        cid = bq_id(head["questLineIDHigh:4"], head["questLineIDLow:4"])
        nodes = []
        for f in d.glob("*.json"):
            if f.name == "QuestLine.json":
                continue
            e = json.loads(f.read_text(encoding="utf-8"))
            nodes.append([bq_id(e["questIDHigh:4"], e["questIDLow:4"]),
                          e["x:3"], e["y:3"], e.get("sizeX:3", 24), e.get("sizeY:3", 24)])
        layout[cid] = nodes
    prereq = {}
    for f in (QUESTDB / "Quests").glob("*/*.json"):
        q = json.loads(f.read_text(encoding="utf-8"))
        # 前提: [ID, 種類] 種類 0=通常, 1=暗黙(破線), 2=非表示
        prereq[bq_id(q["questIDHigh:4"], q["questIDLow:4"])] = [
            [bq_id(r["questIDHigh:4"], r["questIDLow:4"]), r.get("type:1", 0)]
            for r in q.get("preRequisites:9", {}).values()]
    return layout, prereq


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # sync_gui から呼ばれたとき日本語ログを化けさせない
    ja_src = sys.argv[1] if len(sys.argv) > 2 else BASE + JA_PATH
    en_src = sys.argv[2] if len(sys.argv) > 2 else BASE + EN_PATH
    ja, chapters = parse(read_text(ja_src))
    en, _ = parse(read_text(en_src))
    # AI訳 (work/out/*.lang) で、公式訳が英語のままの項目だけを埋める
    ai = {}
    for f in sorted((HERE / "work" / "out").glob("*.lang")):
        v, _ = parse(f.read_text(encoding="utf-8-sig"))
        ai.update(v)
    # AI訳の元にした英語 (work/in/*.lang)。今の英語と違えば原文更新とみなし AI訳は使わない
    ai_src = {}
    for f in sorted((HERE / "work" / "in").glob("*.lang")):
        v, _ = parse(f.read_text(encoding="utf-8-sig"))
        ai_src.update(v)
    stale = {k for k in ai if k in ai_src and k in en and ai_src[k] != en[k]}
    ai_used = set()
    for k, v in ai.items():
        if k in en and ja.get(k) == en[k] and k not in stale:
            ja[k] = v
            ai_used.add(k)

    def entry(kind, qid):
        nj, ne = ja.get((kind, qid, "name"), ""), en.get((kind, qid, "name"), "")
        dj, de = ja.get((kind, qid, "desc"), ""), en.get((kind, qid, "desc"), "")
        # 説明文が英語と同一 (かつ空でない) なら未訳扱い
        # t: 0=未訳, 1=公式(コミュニティ)訳, 2=AI訳を含む
        tr = not (de.strip() and dj == de) and not (not de.strip() and nj == ne)
        is_ai = (kind, qid, "name") in ai_used or (kind, qid, "desc") in ai_used
        return {"nj": nj, "ne": ne, "dj": dj, "de": de, "t": 2 if (tr and is_ai) else int(tr)}

    quests, out_ch = {}, []
    for ch in chapters:
        for q in ch["quests"]:
            quests.setdefault(q, entry("quest", q))
        c = {"id": ch["id"], "q": ch["quests"]}
        if "special" in ch:
            c.update(nj=ch["special"], ne="", dj="", de="")
        else:
            c.update(entry("questline", ch["id"]))
        out_ch.append(c)

    layout, prereq = load_map()
    if layout:
        # 章の所属はマップ定義に合わせる (lang は共有クエストを「複数の章」に退避しているため)。
        # 並びはマップ上の位置順 (左の列から、列内は上から)。
        on_map = set()
        for c in out_ch:
            if c["id"] in layout:
                c["map"] = layout[c["id"]]
                c["q"] = [n[0] for n in sorted(c["map"], key=lambda n: (n[1], n[2])) if n[0] in quests]
                on_map.update(c["q"])
        out_ch = [c for c in out_ch if c["id"] != "_multi"]
        for c in out_ch:
            if c["id"] == "_none":
                c["q"] = [q for q in quests if q not in on_map]
        out_ch = [c for c in out_ch if c["q"]]
    for qid, q in quests.items():
        if prereq.get(qid):
            q["p"] = prereq[qid]

    data = {"chapters": out_ch, "quests": quests, "built": date.today().isoformat()}
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/", payload)
    OUT.write_text(html, encoding="utf-8")
    cnt = [sum(1 for q in quests.values() if q["t"] == t) for t in (0, 1, 2)]
    print(f"map: chapters={sum(1 for c in out_ch if 'map' in c)} prereq={sum(1 for q in quests.values() if 'p' in q)}")
    print(f"chapters={len(out_ch)} quests={len(quests)} untranslated={cnt[0]} official={cnt[1]} ai={cnt[2]} -> {OUT}")
    print(f"ai_stale={len(stale)} (英語原文が更新されたため AI訳を外した項目数)")


if __name__ == "__main__":
    main()
