"""GTNH クエストブック和訳ビューア 同期ツール (GUI)

ダブルクリックで起動 (.pyw はコンソール無しで起動する)。
  1. 公式訳を取得     : GTNH-Translations から ja_JP / en_US のクエスト lang を src/ に保存 (旧ファイルは .bak)
  2. クエスト定義を更新 : src/modpack (GT-New-Horizons-Modpack の DefaultQuests, sparse clone) を最新化
  3. HTMLを生成       : build_questbook_html.py を実行
「まとめて実行」で 1→2→3 を順に行う。
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import urllib.request
from pathlib import Path
from tkinter import scrolledtext, ttk

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
MODPACK = SRC / "modpack"
OUT_HTML = HERE / "GTNH_QuestBook_ja.html"
RAW = "https://raw.githubusercontent.com/GTNewHorizons/GTNH-Translations/master/"
FILES = {
    "ja_JP.lang": "ja_JP/config/txloader/forceload/betterquesting/lang/ja_JP.lang",
    "en_US.lang": "daily-history/config/txloader/forceload/betterquesting/lang/en_US.lang",
}
API_COMMITS = "https://api.github.com/repos/GTNewHorizons/GTNH-Translations/commits?per_page=1&path="
MODPACK_URL = "https://github.com/GTNewHorizons/GT-New-Horizons-Modpack.git"
QUEST_DIR = "config/betterquesting/DefaultQuests"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class App:
    def __init__(self, root):
        self.root = root
        root.title("GTNH クエストブック 同期ツール")
        root.geometry("760x520")
        root.minsize(560, 380)

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")
        self.buttons = []
        for text, fn in [("まとめて実行", self.run_all), ("1. 公式訳を取得", self.fetch_lang),
                         ("2. クエスト定義を更新", self.update_modpack), ("3. HTMLを生成", self.build)]:
            b = ttk.Button(top, text=text, command=lambda f=fn: self.start(f))
            b.pack(side="left", padx=(0, 6))
            self.buttons.append(b)
        ttk.Button(top, text="HTMLを開く", command=lambda: self.open_path(OUT_HTML)).pack(side="right")
        ttk.Button(top, text="フォルダを開く", command=lambda: self.open_path(HERE)).pack(side="right", padx=6)

        self.status = tk.StringVar(value="")
        ttk.Label(root, textvariable=self.status, padding=(10, 0), foreground="#555").pack(fill="x")
        self.bar = ttk.Progressbar(root, mode="indeterminate")
        self.bar.pack(fill="x", padx=10, pady=6)
        self.log_box = scrolledtext.ScrolledText(root, font=("Consolas", 10), height=20, state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.show_status()

    # ---- 表示まわり ----
    def log(self, msg):
        def put():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", msg.rstrip() + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.root.after(0, put)

    def show_status(self):
        parts = []
        for name in FILES:
            p = SRC / name
            parts.append(f"{name}: {self.mtime(p)}")
        parts.append(f"クエスト定義: {'あり' if (MODPACK / QUEST_DIR).exists() else 'なし'}")
        parts.append(f"HTML: {self.mtime(OUT_HTML)}")
        self.status.set("  ／  ".join(parts))

    @staticmethod
    def mtime(p):
        if not p.exists():
            return "未取得"
        import datetime
        return datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def open_path(p):
        if p.exists():
            os.startfile(p)

    def start(self, fn):
        for b in self.buttons:
            b.state(["disabled"])
        self.bar.start(12)

        def work():
            try:
                fn()
            except Exception as e:  # noqa: BLE001 - GUI にそのまま表示する
                self.log(f"[エラー] {type(e).__name__}: {e}")
            finally:
                self.root.after(0, self.done)
        threading.Thread(target=work, daemon=True).start()

    def done(self):
        self.bar.stop()
        for b in self.buttons:
            b.state(["!disabled"])
        self.show_status()

    def run(self, cmd, cwd=HERE):
        """外部コマンドを実行し、出力をログに流す。失敗時は例外。"""
        self.log("$ " + " ".join(str(c) for c in cmd))
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, env=env, creationflags=NO_WINDOW)
        for stream in (p.stdout, p.stderr):
            text = stream.decode("utf-8", errors="replace").strip()
            if text:
                self.log(text)
        if p.returncode != 0:
            raise RuntimeError(f"終了コード {p.returncode}")

    # ---- 処理本体 ----
    def run_all(self):
        self.fetch_lang()
        self.update_modpack()
        self.build()

    def fetch_lang(self):
        self.log("== 公式訳を取得 ==")
        SRC.mkdir(exist_ok=True)
        for name, path in FILES.items():
            try:
                with urllib.request.urlopen(API_COMMITS + path, timeout=20) as r:
                    c = json.load(r)[0]["commit"]["committer"]["date"]
                self.log(f"{name}: 最終更新 {c}")
            except Exception as e:  # noqa: BLE001 - 更新日時は参考情報なので失敗しても続行
                self.log(f"{name}: 更新日時の取得に失敗 ({e})")
            with urllib.request.urlopen(RAW + path, timeout=120) as r:
                data = r.read()
            dst = SRC / name
            if dst.exists() and dst.read_bytes() == data:
                self.log(f"{name}: 変更なし ({len(data):,} bytes)")
                continue
            if dst.exists():
                shutil.copy2(dst, dst.with_suffix(".lang.bak"))
            dst.write_bytes(data)
            self.log(f"{name}: 更新しました ({len(data):,} bytes)")

    def update_modpack(self):
        self.log("== クエスト定義を更新 ==")
        if not (MODPACK / ".git").exists():
            self.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", MODPACK_URL, str(MODPACK)])
            self.run(["git", "-C", str(MODPACK), "sparse-checkout", "set", QUEST_DIR])
            return
        before = subprocess.run(["git", "-C", str(MODPACK), "rev-parse", "HEAD"], capture_output=True,
                                creationflags=NO_WINDOW).stdout.decode().strip()
        self.run(["git", "-C", str(MODPACK), "fetch", "--depth", "1", "origin", "HEAD"])
        # データ取得専用のクローンなので、手元の変更は持たず最新に合わせる
        self.run(["git", "-C", str(MODPACK), "reset", "--hard", "FETCH_HEAD"])
        after = subprocess.run(["git", "-C", str(MODPACK), "rev-parse", "HEAD"], capture_output=True,
                               creationflags=NO_WINDOW).stdout.decode().strip()
        self.log("変更なし" if before == after else f"更新しました ({before[:8]} → {after[:8]})")

    def build(self):
        self.log("== HTMLを生成 ==")
        py = Path(sys.executable)
        if py.name.lower() == "pythonw.exe":  # 出力を受け取るため python.exe で実行
            py = py.with_name("python.exe")
        self.run([str(py), "-I", str(HERE / "build_questbook_html.py"),
                  str(SRC / "ja_JP.lang"), str(SRC / "en_US.lang")])
        self.log("完了。未訳や原文更新があれば、翻訳は Claude に依頼してください。")


if __name__ == "__main__":
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()
