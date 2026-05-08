"""
Unit tests for replacer.py – CSV parsing and text-replacement logic.
Run with:  pytest tests/
"""
import csv
import os
import sys
import textwrap

import pytest

# Ensure project root is on sys.path when running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from replacer import CSVError, apply_replacements, load_replacements, process_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_csv(path: str, rows: list, headers=("TỪ CẦN TÌM", "TỪ ĐÚNG")) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)


# ---------------------------------------------------------------------------
# load_replacements
# ---------------------------------------------------------------------------

class TestLoadReplacements:
    def test_basic(self, tmp_path):
        csv_file = str(tmp_path / "data.csv")
        write_csv(csv_file, [("xin chào", "hello"), ("tạm biệt", "goodbye")])
        pairs = load_replacements(csv_file)
        assert pairs == [("xin chào", "hello"), ("tạm biệt", "goodbye")]

    def test_quoted_value_with_comma(self, tmp_path):
        """Values containing commas must be properly quoted and parsed."""
        csv_file = str(tmp_path / "data.csv")
        write_csv(csv_file, [("a, b", "c")])
        pairs = load_replacements(csv_file)
        assert pairs == [("a, b", "c")]

    def test_skips_blank_find(self, tmp_path):
        csv_file = str(tmp_path / "data.csv")
        write_csv(csv_file, [("", "anything"), ("real", "value")])
        pairs = load_replacements(csv_file)
        assert pairs == [("real", "value")]

    def test_extra_columns_ignored(self, tmp_path):
        csv_file = str(tmp_path / "data.csv")
        headers = ("TỪ CẦN TÌM", "TỪ ĐÚNG", "GHI CHÚ")
        with open(csv_file, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(headers)
            writer.writerow(["old", "new", "some note"])
        pairs = load_replacements(csv_file)
        assert pairs == [("old", "new")]

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(CSVError, match="Không tìm thấy"):
            load_replacements(str(tmp_path / "missing.csv"))

    def test_missing_column_raises(self, tmp_path):
        csv_file = str(tmp_path / "bad.csv")
        write_csv(csv_file, [("a", "b")], headers=("WRONG_COL", "TỪ ĐÚNG"))
        with pytest.raises(CSVError, match="thiếu cột"):
            load_replacements(csv_file)

    def test_utf8_bom(self, tmp_path):
        """Files saved with BOM (utf-8-sig) should be read correctly."""
        csv_file = str(tmp_path / "bom.csv")
        with open(csv_file, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow(["TỪ CẦN TÌM", "TỪ ĐÚNG"])
            writer.writerow(["old", "new"])
        pairs = load_replacements(csv_file)
        assert pairs == [("old", "new")]

    def test_empty_file_raises(self, tmp_path):
        csv_file = str(tmp_path / "empty.csv")
        open(csv_file, "w").close()
        with pytest.raises(CSVError):
            load_replacements(csv_file)


# ---------------------------------------------------------------------------
# apply_replacements
# ---------------------------------------------------------------------------

class TestApplyReplacements:
    def test_single_replacement(self):
        text, counts = apply_replacements("hello world", [("hello", "hi")])
        assert text == "hi world"
        assert counts == {"hello": 1}

    def test_multiple_occurrences(self):
        text, counts = apply_replacements("a a a", [("a", "b")])
        assert text == "b b b"
        assert counts == {"a": 3}

    def test_multiple_pairs(self):
        text, counts = apply_replacements("foo bar", [("foo", "baz"), ("bar", "qux")])
        assert text == "baz qux"
        assert counts == {"foo": 1, "bar": 1}

    def test_no_match_not_in_counts(self):
        text, counts = apply_replacements("hello", [("xyz", "abc")])
        assert text == "hello"
        assert counts == {}

    def test_empty_text(self):
        text, counts = apply_replacements("", [("a", "b")])
        assert text == ""
        assert counts == {}

    def test_empty_pairs(self):
        text, counts = apply_replacements("hello", [])
        assert text == "hello"
        assert counts == {}

    def test_order_matters(self):
        """Earlier pairs are applied first; later pairs may act on already-replaced text."""
        text, counts = apply_replacements("abc", [("abc", "def"), ("def", "ghi")])
        assert text == "ghi"

    def test_vietnamese_characters(self):
        text, counts = apply_replacements(
            "xin chào bạn", [("xin chào", "hello")]
        )
        assert text == "hello bạn"
        assert counts == {"xin chào": 1}

    def test_skip_empty_find(self):
        text, counts = apply_replacements("hello", [("", "X")])
        assert text == "hello"
        assert counts == {}

    def test_ignore_parenthetical_content_in_replacement(self):
        text, counts = apply_replacements(
            "Omodaka",
            [("Omodaka", "Raumac (Rau-mác)")],
            ignore_parenthetical_content=True,
        )
        assert text == "Raumac"
        assert counts == {"Omodaka": 1}

    def test_ignore_parenthetical_content_skips_noop_replacement(self):
        text, counts = apply_replacements(
            "Alex",
            [("Alex", "Alex (A-lếch)")],
            ignore_parenthetical_content=True,
        )
        assert text == "Alex"
        assert counts == {}

    def test_ignore_parenthetical_content_handles_nested_parentheses(self):
        text, counts = apply_replacements(
            "Omodaka",
            [("Omodaka", "Raumac (Rau-mác (đọc gần đúng))")],
            ignore_parenthetical_content=True,
        )
        assert text == "Raumac"
        assert counts == {"Omodaka": 1}


# ---------------------------------------------------------------------------
# process_file
# ---------------------------------------------------------------------------

class TestProcessFile:
    def test_writes_to_output_dir(self, tmp_path):
        src = tmp_path / "input.txt"
        src.write_text("foo bar", encoding="utf-8")
        out_dir = str(tmp_path / "output")

        out_path, counts = process_file(str(src), [("foo", "baz")], out_dir)

        assert os.path.isfile(out_path)
        assert open(out_path, encoding="utf-8").read() == "baz bar"
        assert counts == {"foo": 1}

    def test_does_not_overwrite_original(self, tmp_path):
        src = tmp_path / "input.txt"
        src.write_text("original content", encoding="utf-8")
        out_dir = str(tmp_path / "output")

        process_file(str(src), [("original", "changed")], out_dir)

        assert src.read_text(encoding="utf-8") == "original content"

    def test_creates_output_dir_if_missing(self, tmp_path):
        src = tmp_path / "f.txt"
        src.write_text("x", encoding="utf-8")
        out_dir = str(tmp_path / "new_output")
        assert not os.path.exists(out_dir)

        process_file(str(src), [], out_dir)
        assert os.path.isdir(out_dir)
