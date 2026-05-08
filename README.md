# Replace Tool – Tìm & Thay Thế / Prefix Actor

A small cross-platform desktop app (Python + Tkinter) with two tools in one window:

1. **🔄 Tìm & Thay Thế** – reads find/replace pairs from a CSV file and applies them to
   one or more text files.
2. **✏ Prefix Actor** – reads `.csv` or `.xlsx` files and prepends `[actor]` to every
   value in the `Text` column.

---

## Features

### Tìm & Thay Thế
- **CSV-driven replacements** – define pairs in `data.csv` (UTF-8).
- **Multi-file selection** – use the file dialog to pick many files at once.
- **Drag-and-drop** – drop files onto the window; processing starts automatically
  (requires the optional `tkinterdnd2` package).
- **Safe output** – originals are *never* overwritten; results go to `output/`.
- **Per-file report** – total replacements and per-key counts shown in the log pane.
- **Optional parenthesis stripping** – can ignore content inside parentheses in the
  `TỪ ĐÚNG` column during replacement.
- **Robust CSV parsing** – quoted values and embedded commas handled correctly.
- **Clear error messages** – missing/malformed CSV and file-encoding problems
  are reported in the UI.

### Prefix Actor
- Accepts `.csv` and `.xlsx` (first sheet only) input files.
- Finds columns named **`actor`** and **`Text`** with **case-insensitive, whitespace-tolerant**
  header matching (e.g. `" ACTOR "` and `"text"` both match).
- For each row, prepends `[actor_value]` to the `Text` value:
  - Non-empty text → `[Alice] Hello world`
  - Empty text → `[Alice]`
  - Empty/null actor → `[] Hello world`
- Saves the processed file to `output/<original-filename>` (never overwrites the input).
- Drag-and-drop `.csv`/`.xlsx` files directly onto the file list.

---

## Requirements

| Requirement | Minimum version |
|---|---|
| Python | 3.9+ |
| pandas | 1.5+ |
| openpyxl | 3.0+ |
| tkinterdnd2 *(optional, for drag-and-drop)* | 0.3.0+ |
| pytest *(optional, for tests)* | 7.0+ |

Install all dependencies:

```bash
pip install -r requirements.txt
```

> **Note:** `tkinter` is part of the Python standard library and is included with
> most Python distributions. If it is missing (e.g. some minimal Linux installs)
> run `sudo apt install python3-tk` (Debian/Ubuntu) or equivalent for your distro.

---

## CSV format – `data.csv`

The file must be **UTF-8** (with or without BOM) and have **exactly these two column headers** in the first row:

| TỪ CẦN TÌM | TỪ ĐÚNG |
|---|---|
| text to find | replacement text |

Example (`data.csv`):

```csv
TỪ CẦN TÌM,TỪ ĐÚNG
xin chào,xin chào bạn
sai lỗi,đúng rồi
"có dấu phẩy, trong chuỗi",không có dấu phẩy
```

- Values that contain commas **must** be wrapped in double-quotes.
- Rows with an empty `TỪ CẦN TÌM` value are silently skipped.
- Extra columns beyond the two required ones are ignored.

A ready-to-use sample file is included in the repository as `data.csv`.

---

## Usage

```bash
python app.py
```

The app opens with two tabs:

### Tab 1 – 🔄 Tìm & Thay Thế

1. The app reads `data.csv` from the **same directory** as `app.py` on start-up.
2. Add files by:
   - Clicking **📂 Chọn file** and selecting one or more files, **or**
   - Dragging files from your file manager and dropping them onto the file list.
3. Processing starts automatically when files are added via drag-and-drop.
   For manually added files, click **▶ Chạy thay thế**.
4. Optionally tick **Bỏ qua nội dung trong dấu ngoặc đơn ở cột 'TỪ ĐÚNG'** if you
   want values like `Alex (A-lếch)` to be applied as `Alex`.
5. Results are saved to the `output/` subdirectory next to `app.py`.
6. The log pane shows per-file replacement counts.

### Tab 2 – ✏ Prefix Actor

1. Switch to the **✏ Prefix Actor** tab.
2. Add `.csv` or `.xlsx` files by:
   - Clicking **📂 Chọn file** and selecting one or more files, **or**
   - Dragging `.csv`/`.xlsx` files onto the file list.
3. Processing starts automatically when files are added via drag-and-drop.
   For manually added files, click **▶ Chạy Prefix Actor**.
4. Results are saved to `output/<original-filename>` (same folder as `app.py`).
5. The log pane shows per-file status and any column-not-found errors.

#### Input file format (Prefix Actor)

The input `.csv` or `.xlsx` file must contain at least two columns:

| actor | Text |
|---|---|
| Alice | Hello world |
| Bob | Goodbye |

Column names are matched **case-insensitively** and **whitespace-tolerantly**
(`" ACTOR "`, `"actor"`, `"Actor"` all work).

Output example (same file, `output/` folder):

| actor | Text |
|---|---|
| Alice | [Alice] Hello world |
| Bob | [Bob] Goodbye |

### Buttons (both tabs)

| Button | Action |
|---|---|
| ↺ Tải lại CSV | *(Replace tab)* Reload `data.csv` without restarting |
| 📂 Chọn file | Open file picker |
| 🗑 Xóa đã chọn | Remove highlighted files from the list |
| 🗑 Xóa tất cả | Clear the file list |
| ▶ Chạy thay thế | *(Replace tab)* Run replacements on all listed files |
| ▶ Chạy Prefix Actor | *(Prefix Actor tab)* Run prefix operation on all listed files |

---

## Project structure

```
replace-tool/
├── app.py               # GUI entry point (two-tab Tkinter app)
├── replacer.py          # Core logic: CSV loading, text replacement
├── prefix_actor.py      # Core logic: actor-prefix for .csv/.xlsx
├── data.csv             # Sample replacement table
├── requirements.txt     # Python dependencies
├── tests/
│   ├── test_replacer.py      # Unit tests – find/replace logic
│   └── test_prefix_actor.py  # Unit tests – prefix-actor logic
└── output/              # Created automatically; holds processed files
```

---

## Running tests

```bash
pytest tests/
```

---

## Packaging as a standalone executable (optional)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed app.py
```

The executable will appear in `dist/app` (or `dist/app.exe` on Windows).
