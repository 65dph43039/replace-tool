"""
Core logic: load replacement pairs from data.csv, apply to text.
"""
import csv
import os
import re
from typing import Dict, List, Tuple


CSV_FILE = "data.csv"
COL_FIND = "TỪ CẦN TÌM"
COL_REPLACE = "TỪ ĐÚNG"
OUTPUT_DIR = "output"
PARENTHETICAL_CONTENT_RE = re.compile(r"\s*\([^()]*\)")


class CSVError(Exception):
    """Raised when data.csv is missing or malformed."""


def load_replacements(csv_path: str = CSV_FILE) -> List[Tuple[str, str]]:
    """
    Parse *csv_path* and return an ordered list of (find, replace) pairs.

    The CSV must be UTF-8 and have at least the two header columns
    ``TỪ CẦN TÌM`` and ``TỪ ĐÚNG`` (extra columns are silently ignored).

    Raises
    ------
    CSVError
        When the file is missing, unreadable, or missing required columns.
    """
    if not os.path.exists(csv_path):
        raise CSVError(
            f"Không tìm thấy file '{csv_path}'. "
            "Hãy tạo file data.csv theo đúng định dạng."
        )

    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                raise CSVError(f"File '{csv_path}' rỗng hoặc không đọc được.")

            # Normalise header whitespace so minor spacing issues don't break things
            headers = [h.strip() for h in reader.fieldnames]
            if COL_FIND not in headers or COL_REPLACE not in headers:
                raise CSVError(
                    f"File '{csv_path}' thiếu cột bắt buộc.\n"
                    f"Cần có: '{COL_FIND}' và '{COL_REPLACE}'.\n"
                    f"Hiện có: {headers}"
                )

            pairs: List[Tuple[str, str]] = []
            for i, row in enumerate(reader, start=2):
                find_val = (row.get(COL_FIND) or "").strip()
                replace_val = (row.get(COL_REPLACE) or "").strip()
                if find_val:          # skip blank "find" entries silently
                    pairs.append((find_val, replace_val))
            return pairs
    except (OSError, UnicodeDecodeError) as exc:
        raise CSVError(f"Lỗi đọc file '{csv_path}': {exc}") from exc


def apply_replacements(
    text: str,
    pairs: List[Tuple[str, str]],
    ignore_parenthetical_content: bool = False,
) -> Tuple[str, Dict[str, int]]:
    """
    Apply every (find, replace) pair to *text* in order.

    Returns
    -------
    result_text : str
        The text after all replacements.
    counts : dict
        Mapping of find-string → number of replacements made.
    """
    counts: Dict[str, int] = {}
    for find, replace in pairs:
        if not find:
            continue
        if ignore_parenthetical_content:
            replace = PARENTHETICAL_CONTENT_RE.sub("", replace).strip()
        if replace == find:
            continue
        occurrences = text.count(find)
        if occurrences:
            text = text.replace(find, replace)
            counts[find] = occurrences
    return text, counts


def process_file(
    file_path: str,
    pairs: List[Tuple[str, str]],
    output_dir: str = OUTPUT_DIR,
    ignore_parenthetical_content: bool = False,
) -> Tuple[str, Dict[str, int]]:
    """
    Read *file_path*, apply replacements, write result to *output_dir*.

    The output filename is the original basename (no suffix added) placed
    inside *output_dir*.  The original file is **never** overwritten.

    Returns
    -------
    out_path : str
        Path of the written output file.
    counts : dict
        Per-key replacement counts (same as :func:`apply_replacements`).

    Raises
    ------
    OSError / UnicodeDecodeError
        Propagated from file I/O; caller should handle and display to user.
    """
    with open(file_path, "r", encoding="utf-8") as fh:
        text = fh.read()

    result, counts = apply_replacements(
        text,
        pairs,
        ignore_parenthetical_content=ignore_parenthetical_content,
    )

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, os.path.basename(file_path))
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(result)

    return out_path, counts
