"""
Tkinter GUI for the Replace Tool.

Contains two tabs:
  1. 🔄 Tìm & Thay Thế  – CSV-driven find/replace on text files.
  2. ✏ Prefix Actor     – Prefix [actor] into the Text column of .csv/.xlsx files.

Drag-and-drop is provided via tkinterdnd2 when available;
otherwise the app falls back to the standard file-open dialog only.
"""
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

# Attempt to import drag-and-drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _DND_AVAILABLE = True
except ImportError:
    _DND_AVAILABLE = False

from prefix_actor import PrefixActorError, process_prefix_actor
from replacer import CSVError, load_replacements, process_file

CSV_PATH = "data.csv"
OUTPUT_DIR = "output"


def _total(counts: dict) -> int:
    return sum(counts.values())


class App:
    def __init__(self, root: tk.Misc) -> None:
        self.root = root
        root.title("Replace Tool")
        root.resizable(True, True)
        root.minsize(640, 520)

        self._build_ui()

        if _DND_AVAILABLE:
            self._setup_dnd()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # ── shared status bar (bottom of root) ───────────────────────
        self.status_var = tk.StringVar(value="Sẵn sàng.")
        tk.Label(self.root, textvariable=self.status_var, anchor="w",
                 relief=tk.SUNKEN).pack(fill=tk.X, side=tk.BOTTOM)

        # ── notebook ──────────────────────────────────────────────────
        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        tab1 = ttk.Frame(nb)
        nb.add(tab1, text="🔄 Tìm & Thay Thế")
        self._build_replace_tab(tab1)

        tab2 = ttk.Frame(nb)
        nb.add(tab2, text="✏ Prefix Actor")
        self._build_prefix_actor_tab(tab2)

    def _build_replace_tab(self, parent: tk.Widget) -> None:
        """Build the original find/replace UI inside *parent*."""
        pad = {"padx": 8, "pady": 4}

        # ── top bar ────────────────────────────────────────────────────
        top = tk.Frame(parent)
        top.pack(fill=tk.X, **pad)

        tk.Label(top, text=f"File CSV: {CSV_PATH}").pack(side=tk.LEFT)

        reload_btn = ttk.Button(top, text="↺ Tải lại CSV", command=self._reload_csv)
        reload_btn.pack(side=tk.RIGHT)

        # ── drop zone / file list ──────────────────────────────────────
        zone_frame = tk.LabelFrame(
            parent,
            text=(
                "Kéo & thả file vào đây  hoặc  nhấn 'Chọn file'"
                if _DND_AVAILABLE
                else "Danh sách file (nhấn 'Chọn file' để thêm)"
            ),
        )
        zone_frame.pack(fill=tk.BOTH, expand=True, **pad)

        self.file_listbox = tk.Listbox(zone_frame, selectmode=tk.EXTENDED, height=8)
        self.file_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=4, pady=4)

        sb = ttk.Scrollbar(zone_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=sb.set)

        # ── buttons ───────────────────────────────────────────────────
        btn_row = tk.Frame(parent)
        btn_row.pack(fill=tk.X, **pad)

        ttk.Button(btn_row, text="📂 Chọn file", command=self._browse_files).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btn_row, text="🗑 Xóa đã chọn", command=self._remove_selected).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btn_row, text="🗑 Xóa tất cả", command=self._clear_files).pack(
            side=tk.LEFT, padx=4
        )
        self.run_btn = ttk.Button(
            btn_row, text="▶ Chạy thay thế", command=self._run, style="Accent.TButton"
        )
        self.run_btn.pack(side=tk.RIGHT, padx=4)

        # ── output dir indicator ──────────────────────────────────────
        dir_row = tk.Frame(parent)
        dir_row.pack(fill=tk.X, padx=8)
        tk.Label(dir_row, text=f"📁 Kết quả lưu vào: {os.path.abspath(OUTPUT_DIR)}",
                 anchor="w", fg="gray").pack(fill=tk.X)

        # ── log area ──────────────────────────────────────────────────
        log_frame = tk.LabelFrame(parent, text="Kết quả / Log")
        log_frame.pack(fill=tk.BOTH, expand=True, **pad)

        self.log = scrolledtext.ScrolledText(log_frame, height=10, state=tk.DISABLED,
                                             wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _build_prefix_actor_tab(self, parent: tk.Widget) -> None:
        """Build the Prefix Actor UI inside *parent*."""
        pad = {"padx": 8, "pady": 4}

        # ── info label ────────────────────────────────────────────────
        info = tk.Frame(parent)
        info.pack(fill=tk.X, **pad)
        tk.Label(
            info,
            text="Chọn file .csv hoặc .xlsx – cột 'actor' sẽ được chèn vào đầu cột 'Text'.",
            anchor="w",
        ).pack(fill=tk.X)

        # ── drop zone / file list ──────────────────────────────────────
        zone_frame = tk.LabelFrame(
            parent,
            text=(
                "Kéo & thả file .csv/.xlsx vào đây  hoặc  nhấn 'Chọn file'"
                if _DND_AVAILABLE
                else "Danh sách file .csv/.xlsx (nhấn 'Chọn file' để thêm)"
            ),
        )
        zone_frame.pack(fill=tk.BOTH, expand=True, **pad)

        self.pa_file_listbox = tk.Listbox(zone_frame, selectmode=tk.EXTENDED, height=8)
        self.pa_file_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=4, pady=4)

        sb = ttk.Scrollbar(zone_frame, orient=tk.VERTICAL,
                           command=self.pa_file_listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.pa_file_listbox.config(yscrollcommand=sb.set)

        # ── buttons ───────────────────────────────────────────────────
        btn_row = tk.Frame(parent)
        btn_row.pack(fill=tk.X, **pad)

        ttk.Button(btn_row, text="📂 Chọn file", command=self._pa_browse_files).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btn_row, text="🗑 Xóa đã chọn",
                   command=self._pa_remove_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="🗑 Xóa tất cả",
                   command=self._pa_clear_files).pack(side=tk.LEFT, padx=4)
        self.pa_run_btn = ttk.Button(
            btn_row, text="▶ Chạy Prefix Actor", command=self._pa_run,
            style="Accent.TButton",
        )
        self.pa_run_btn.pack(side=tk.RIGHT, padx=4)

        # ── output dir indicator ──────────────────────────────────────
        dir_row = tk.Frame(parent)
        dir_row.pack(fill=tk.X, padx=8)
        tk.Label(dir_row, text=f"📁 Kết quả lưu vào: {os.path.abspath(OUTPUT_DIR)}",
                 anchor="w", fg="gray").pack(fill=tk.X)

        # ── log area ──────────────────────────────────────────────────
        log_frame = tk.LabelFrame(parent, text="Kết quả / Log")
        log_frame.pack(fill=tk.BOTH, expand=True, **pad)

        self.pa_log = scrolledtext.ScrolledText(log_frame, height=10, state=tk.DISABLED,
                                                wrap=tk.WORD)
        self.pa_log.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    # ------------------------------------------------------------------
    # Drag-and-drop
    # ------------------------------------------------------------------

    def _setup_dnd(self) -> None:
        self.file_listbox.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
        self.file_listbox.dnd_bind("<<Drop>>", self._on_drop)  # type: ignore[attr-defined]
        self.pa_file_listbox.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
        self.pa_file_listbox.dnd_bind("<<Drop>>", self._pa_on_drop)  # type: ignore[attr-defined]

    def _on_drop(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Parse the drop data (handles paths with spaces wrapped in braces)."""
        raw: str = event.data  # type: ignore[attr-defined]
        paths = self._parse_dnd_paths(raw)
        self._add_files(paths)
        self._run_if_files()

    def _pa_on_drop(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        raw: str = event.data  # type: ignore[attr-defined]
        paths = self._parse_dnd_paths(raw)
        self._pa_add_files(paths)
        self._pa_run_if_files()

    @staticmethod
    def _parse_dnd_paths(raw: str) -> list:
        """
        tkinterdnd2 encodes paths with spaces inside curly braces.
        E.g.: '{/path/with spaces/file.txt} /simple/path.txt'
        """
        paths = []
        raw = raw.strip()
        while raw:
            if raw.startswith("{"):
                end = raw.index("}")
                paths.append(raw[1:end])
                raw = raw[end + 1:].strip()
            else:
                parts = raw.split(" ", 1)
                paths.append(parts[0])
                raw = parts[1].strip() if len(parts) > 1 else ""
        return paths

    # ------------------------------------------------------------------
    # File management – Replace tab
    # ------------------------------------------------------------------

    def _browse_files(self) -> None:
        chosen = filedialog.askopenfilenames(
            title="Chọn file cần xử lý",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if chosen:
            self._add_files(list(chosen))
            self._run_if_files()

    def _add_files(self, paths: list) -> None:
        existing = set(self.file_listbox.get(0, tk.END))
        for p in paths:
            p = p.strip()
            if p and p not in existing:
                self.file_listbox.insert(tk.END, p)
                existing.add(p)

    def _remove_selected(self) -> None:
        for i in reversed(self.file_listbox.curselection()):
            self.file_listbox.delete(i)

    def _clear_files(self) -> None:
        self.file_listbox.delete(0, tk.END)

    def _run_if_files(self) -> None:
        """Auto-run processing when files are added (matching DnD UX requirement)."""
        if self.file_listbox.size() > 0:
            self._run()

    # ------------------------------------------------------------------
    # File management – Prefix Actor tab
    # ------------------------------------------------------------------

    def _pa_browse_files(self) -> None:
        chosen = filedialog.askopenfilenames(
            title="Chọn file .csv / .xlsx",
            filetypes=[
                ("CSV / Excel", "*.csv *.xlsx"),
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx"),
                ("All files", "*.*"),
            ],
        )
        if chosen:
            self._pa_add_files(list(chosen))
            self._pa_run_if_files()

    def _pa_add_files(self, paths: list) -> None:
        existing = set(self.pa_file_listbox.get(0, tk.END))
        for p in paths:
            p = p.strip()
            if p and p not in existing:
                self.pa_file_listbox.insert(tk.END, p)
                existing.add(p)

    def _pa_remove_selected(self) -> None:
        for i in reversed(self.pa_file_listbox.curselection()):
            self.pa_file_listbox.delete(i)

    def _pa_clear_files(self) -> None:
        self.pa_file_listbox.delete(0, tk.END)

    def _pa_run_if_files(self) -> None:
        if self.pa_file_listbox.size() > 0:
            self._pa_run()

    # ------------------------------------------------------------------
    # CSV reload (Replace tab)
    # ------------------------------------------------------------------

    def _reload_csv(self) -> None:
        self._log_clear()
        self._status("Đang tải CSV...")
        try:
            pairs = load_replacements(CSV_PATH)
            self._log(f"✅ Đã tải {len(pairs)} cặp thay thế từ '{CSV_PATH}'.\n")
            self._status(f"CSV OK – {len(pairs)} cặp.")
        except CSVError as exc:
            self._log(f"❌ Lỗi CSV: {exc}\n")
            self._status("Lỗi CSV.")

    # ------------------------------------------------------------------
    # Main processing – Replace tab
    # ------------------------------------------------------------------

    def _run(self) -> None:
        files = list(self.file_listbox.get(0, tk.END))
        if not files:
            messagebox.showinfo("Chưa có file", "Vui lòng chọn ít nhất một file.")
            return

        self._log_clear()
        self._status("Đang tải CSV...")

        try:
            pairs = load_replacements(CSV_PATH)
        except CSVError as exc:
            self._log(f"❌ Lỗi CSV: {exc}\n")
            self._status("Lỗi CSV – dừng.")
            messagebox.showerror("Lỗi CSV", str(exc))
            return

        self._log(f"📋 Đã tải {len(pairs)} cặp thay thế từ '{CSV_PATH}'.\n")

        total_files = 0
        total_replacements = 0

        for fp in files:
            self._log(f"⚙  Xử lý: {fp}\n")
            try:
                out_path, counts = process_file(fp, pairs, OUTPUT_DIR)
                n = _total(counts)
                total_replacements += n
                total_files += 1
                if n == 0:
                    self._log(f"   → Không có thay thế nào. Đã lưu: {out_path}\n")
                else:
                    self._log(f"   → {n} lần thay thế. Đã lưu: {out_path}\n")
                    for find, cnt in counts.items():
                        self._log(f"      • \"{find}\" : {cnt} lần\n")
            except UnicodeDecodeError as exc:
                self._log(f"   ❌ Lỗi encoding: {exc}\n")
            except OSError as exc:
                self._log(f"   ❌ Lỗi đọc/ghi file: {exc}\n")

        summary = (
            f"\n✅ Hoàn tất: {total_files}/{len(files)} file, "
            f"tổng {total_replacements} lần thay thế.\n"
        )
        self._log(summary)
        self._status(
            f"Xong: {total_files} file, {total_replacements} lần thay thế."
        )

    # ------------------------------------------------------------------
    # Main processing – Prefix Actor tab
    # ------------------------------------------------------------------

    def _pa_run(self) -> None:
        files = list(self.pa_file_listbox.get(0, tk.END))
        if not files:
            messagebox.showinfo("Chưa có file", "Vui lòng chọn ít nhất một file .csv/.xlsx.")
            return

        self._pa_log_clear()
        total_ok = 0

        for fp in files:
            self._pa_log(f"⚙  Xử lý: {fp}\n")
            try:
                out_path = process_prefix_actor(fp, OUTPUT_DIR)
                total_ok += 1
                self._pa_log(f"   ✅ Đã lưu: {out_path}\n")
            except PrefixActorError as exc:
                self._pa_log(f"   ❌ Lỗi: {exc}\n")
            except OSError as exc:
                self._pa_log(f"   ❌ Lỗi đọc/ghi file: {exc}\n")

        self._pa_log(f"\n✅ Hoàn tất: {total_ok}/{len(files)} file.\n")
        self._status(f"Prefix Actor: {total_ok}/{len(files)} file xong.")

    # ------------------------------------------------------------------
    # Logging helpers – Replace tab
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, msg)
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)

    def _log_clear(self) -> None:
        self.log.config(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.config(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Logging helpers – Prefix Actor tab
    # ------------------------------------------------------------------

    def _pa_log(self, msg: str) -> None:
        self.pa_log.config(state=tk.NORMAL)
        self.pa_log.insert(tk.END, msg)
        self.pa_log.see(tk.END)
        self.pa_log.config(state=tk.DISABLED)

    def _pa_log_clear(self) -> None:
        self.pa_log.config(state=tk.NORMAL)
        self.pa_log.delete("1.0", tk.END)
        self.pa_log.config(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _status(self, msg: str) -> None:
        self.status_var.set(msg)
        self.root.update_idletasks()


def main() -> None:
    if _DND_AVAILABLE:
        root = TkinterDnD.Tk()  # type: ignore[attr-defined]
    else:
        root = tk.Tk()

    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
