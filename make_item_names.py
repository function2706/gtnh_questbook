"""NEI のダンプ (dumps フォルダ) からアイテム名の対応表 src/item_names.tsv を作る。

  python make_item_names.py <dumps フォルダ>

使うファイル (ゲーム内 NEI の Options → Tools → Data Dumps で出力):
  itempanel.csv : Item Name, Item ID, Item meta, Has NBT, Display Name   … 登録名+ダメージ値ごとの表示名
  oredict.csv   : Ore Name, ItemStack(例 1xgt.metaitem.01@32146), Item ID(登録名), Display Name, Wildcard
  item.csv      : Name(登録名), ID, Has Block, Mod, Class, Display Name  … 登録名ごとの代表名 (ダメージ値 0)
優先順位: itempanel > oredict > item.csv (item.csv はダメージ値 0 にだけ使う)。
出力: 登録名<TAB>ダメージ値<TAB>表示名 (ビルド時にクエストに出てくるものだけ読み込まれる)
"""
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "src" / "item_names.tsv"
QUESTDB = HERE / "src" / "modpack" / "config" / "betterquesting" / "DefaultQuests"


def rows(path):
    if not path.exists():
        print(f"  (なし) {path.name}")
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        r = list(csv.DictReader(f))
    print(f"  {path.name}: {len(r)} 行")
    return r


def clean(name):
    """表示名の書式コードを除く。未翻訳の内部名 (xxx.name) は捨てる"""
    name = re.sub(r"§.", "", name or "").strip()
    if not name or re.fullmatch(r"[\w.\-]+\.name", name) or name.lower() == "(wildcard)":
        return ""
    return name


def quest_items():
    """クエスト (課題・報酬) に出てくる (登録名, ダメージ値) の集合"""
    found = set()

    def walk(d):
        for it in d.values():
            found.add((it.get("id:8", ""), it.get("Damage:2", 0)))
    for f in (QUESTDB / "Quests").glob("*/*.json"):
        q = json.loads(f.read_text(encoding="utf-8"))
        for t in q.get("tasks:9", {}).values():
            walk(t.get("requiredItems:9", {}))
        for r in q.get("rewards:9", {}).values():
            walk(r.get("rewards:9", {}))
            walk(r.get("choices:9", {}))
    return found


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    dumps = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "dumps"
    print(f"dumps: {dumps}")
    names = {}  # (登録名, ダメージ値) -> 表示名
    wildcard = {}  # 登録名 -> 表示名 (鉱石辞書のワイルドカード登録)

    for r in rows(dumps / "itempanel.csv"):
        n = clean(r.get("Display Name"))
        if n:
            names.setdefault((r.get("Item Name", ""), int(r.get("Item meta") or 0)), n)

    for r in rows(dumps / "oredict.csv"):
        n, reg = clean(r.get("Display Name")), r.get("Item ID", "")
        m = re.search(r"@(\d+)$", r.get("ItemStack", ""))
        if not (n and reg and m):
            continue
        if r.get("Wildcard", "").lower() == "true":
            wildcard.setdefault(reg, n)
        else:
            names.setdefault((reg, int(m.group(1))), n)

    for r in rows(dumps / "item.csv"):
        n = clean(r.get("Display Name"))
        if n:
            names.setdefault((r.get("Name", ""), 0), n)

    # ワイルドカード登録は、他で名前が無いダメージ値の代わりにクエスト側で使う
    need = quest_items() if QUESTDB.exists() else set()
    for reg, dmg in need:
        if (reg, dmg) not in names and reg in wildcard:
            names[(reg, dmg)] = wildcard[reg]

    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        for (reg, dmg), n in sorted(names.items()):
            f.write(f"{reg}\t{dmg}\t{n}\n")
    print(f"出力: {OUT} ({len(names)} 件)")
    if need:
        hit = sum(1 for k in need if k in names)
        print(f"クエストに出てくるアイテム {len(need)} 種のうち、名前が付くもの {hit} 種 ({hit / len(need):.0%})")


if __name__ == "__main__":
    main()
