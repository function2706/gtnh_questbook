"""GTNH クエストブック和訳ビューア 同期ツール (GUI)

ダブルクリックで起動 (.pyw はコンソール無しで起動する)。
  1. 公式訳を取得     : GTNH-Translations から ja_JP / en_US のクエスト lang を src/ に保存 (旧ファイルは .bak)
  2. クエスト定義を更新 : src/modpack (GT-New-Horizons-Modpack の DefaultQuests, sparse clone) を最新化
  3. HTMLを生成       : build_questbook_html.py を実行
「まとめて実行」で 1→2→3 を順に行う。
  ゲームに反映…       : 3 で作った ja_JP.lang (公式訳 + AI訳) を GTNH インスタンスの
                        config/txloader/forceload/betterquesting/lang/ にコピー (既存は .bak に退避)
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
from tkinter import filedialog, messagebox, scrolledtext, ttk

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
GAME_LANG = HERE / "dist" / "config" / "txloader" / "forceload" / "betterquesting" / "lang" / "ja_JP.lang"
GAME_LANG_REL = Path("config", "txloader", "forceload", "betterquesting", "lang", "ja_JP.lang")
SETTINGS = HERE / "sync_gui_settings.json"  # 反映先フォルダの記憶 (git 管理外)


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

        game = ttk.Frame(root, padding=(10, 0, 10, 6))
        game.pack(fill="x")
        b = ttk.Button(game, text="ゲームに反映…", command=self.apply_to_game)
        b.pack(side="left", padx=(0, 8))
        self.buttons.append(b)
        self.target = tk.StringVar(value=self.load_settings().get("instance", ""))
        ttk.Label(game, text="反映先:").pack(side="left")
        ttk.Label(game, textvariable=self.target, foreground="#555").pack(side="left", padx=4)

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

    # ---- 設定 ----
    @staticmethod
    def load_settings():
        try:
            return json.loads(SETTINGS.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    @staticmethod
    def save_settings(d):
        SETTINGS.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- ゲームへの反映 ----
    @staticmethod
    def resolve_game_dir(p):
        """選ばれたフォルダから config を含むゲームディレクトリを探す (インスタンス直下 or .minecraft)"""
        for cand in (p, p / ".minecraft", p / "minecraft"):
            if (cand / "config").is_dir():
                return cand
        return None

    def apply_to_game(self):
        """反映先を選んで (前回の場所があれば確認して) コピーする。ダイアログはメインスレッドで出す。"""
        if not GAME_LANG.exists():
            messagebox.showwarning("ゲームに反映", "先に「3. HTMLを生成」を実行してください。")
            return
        cur = self.target.get()
        if cur and messagebox.askyesno("ゲームに反映", f"次のインスタンスに反映します。\n\n{cur}\n\n「いいえ」で別のフォルダを選びます。"):
            base = Path(cur)
        else:
            sel = filedialog.askdirectory(title="GTNH のインスタンスフォルダ (または .minecraft) を選択")
            if not sel:
                return
            base = Path(sel)
        game_dir = self.resolve_game_dir(base)
        if not game_dir:
            messagebox.showerror("ゲームに反映", f"config フォルダが見つかりません。GTNH のインスタンスフォルダか .minecraft を選んでください。\n\n{base}")
            return
        self.target.set(str(game_dir))
        s = self.load_settings()
        s["instance"] = str(game_dir)
        self.save_settings(s)
        self.start(lambda: self.copy_lang(game_dir))

    def copy_lang(self, game_dir):
        self.log("== ゲームに反映 ==")
        dst = game_dir / GAME_LANG_REL
        data = GAME_LANG.read_bytes()
        if dst.exists() and dst.read_bytes() == data:
            self.log(f"変更なし: {dst}")
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            bak = dst.with_suffix(".lang.bak")
            shutil.copy2(dst, bak)
            self.log(f"既存ファイルを退避: {bak}")
        dst.write_bytes(data)
        self.log(f"コピーしました: {dst}")
        self.log("ゲームの言語を日本語にして起動すると反映されます (起動中の場合は再起動してください)。")

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
