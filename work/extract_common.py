"""template.html から共通部分 (データ読込・書式変換・課題/報酬描画) を qb_common.js に切り出す一回限りのスクリプト"""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
t = root / 'template.html'
h = t.read_text(encoding='utf-8')


def cut(start, end):
    """start から end の直前までを h から取り除いて返す"""
    global h
    i = h.index(start)
    j = h.index(end, i)
    block = h[i:j]
    h = h[:i] + h[j:]
    return block


# 1) データ読込
head = cut("const D = window.QDATA;\nconst Q = D.quests, CH = D.chapters;\n", "const st = {")
# 2) ID 変換・逆引き・esc/strip/fmt/highlight
core = cut("// 旧形式 (標準base64) のクエストIDを lang 側の URL-safe 形式へ\n", "// ---- 章ナビ ----")
# 3) 課題・報酬・前提/後続
detail = cut("// ---- 課題・報酬・前提/後続 ----\n", "function qCard(")

common = ("/* GTNH クエストブック 共通処理 (閲覧ページ・進行ページで共有)\n"
          " * 前提: questdata.js (window.QDATA) を先に読み込むこと。\n"
          " * ページ側で st (mode/show) と chName(c) を定義すること。\n"
          " */\n" + head + "\n" + core + detail)
(root / 'qb_common.js').write_text(common, encoding='utf-8')

h = h.replace('<script src="questdata.js"></script>\n<script>',
              '<script src="questdata.js"></script>\n<script src="qb_common.js"></script>\n<script>', 1)
t.write_text(h, encoding='utf-8')
print('common lines:', common.count('\n'))
