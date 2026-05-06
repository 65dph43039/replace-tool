"""
Core logic for the Prefix-Actor tool.

Reads .csv or .xlsx files, finds the columns ``actor`` and ``Text``
(case-insensitive, leading/trailing/internal whitespace normalised),
then for every row prefixes the Text value with ``[actor_value]``,
writing the result to ``output/`` with the same filename.
"""
import os
import re
from typing import Optional

import pandas as pd


OUTPUT_DIR = "output"
_COL_ACTOR = "actor"
_COL_TEXT = "text"


class PrefixActorError(Exception):
    """Raised when required columns are missing or the file type is unsupported."""


def normalize_col(name: str) -> str:
    """Return a canonical header name: strip edges + collapse internal whitespace + lowercase."""
    return re.sub(r"\s+", " ", name.strip()).lower()


def _find_col(columns, target: str) -> Optional[str]:
    """Return the first original column name whose normalised form equals *target*, or None."""
    for col in columns:
        if normalize_col(col) == target:
            return col
    return None


def process_prefix_actor(
    file_path: str,
    output_dir: str = OUTPUT_DIR,
) -> str:
    """
    Read *file_path* (.csv or .xlsx), prefix ``[actor_value]`` into the Text
    column of every row, and save the result to *output_dir* with the same
    basename.  The original file is **never** overwritten.

    Parameters
    ----------
    file_path : str
        Path to the input file (.csv or .xlsx).
    output_dir : str
        Directory where the output file will be written (created if absent).

    Returns
    -------
    out_path : str
        Path of the written output file.

    Raises
    ------
    PrefixActorError
        If the file type is not supported or required columns are missing.
    OSError
        Propagated from file I/O; callers should handle and display to user.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        df = pd.read_csv(file_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    elif ext == ".xlsx":
        df = pd.read_excel(file_path, sheet_name=0, dtype=str)
        df = df.fillna("")
    else:
        raise PrefixActorError(
            f"Loại file không được hỗ trợ: '{ext}'. Chỉ chấp nhận .csv và .xlsx."
        )

    actor_col = _find_col(df.columns, _COL_ACTOR)
    text_col = _find_col(df.columns, _COL_TEXT)

    missing = []
    if actor_col is None:
        missing.append("actor")
    if text_col is None:
        missing.append("Text")
    if missing:
        raise PrefixActorError(
            f"Không tìm thấy cột bắt buộc: {missing}.\n"
            f"Các cột hiện có: {list(df.columns)}"
        )

    def _prefix(row: pd.Series) -> str:
        actor = str(row[actor_col])
        text = str(row[text_col])
        if text:
            return f"[{actor}] {text}"
        return f"[{actor}]"

    df[text_col] = df.apply(_prefix, axis=1)

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, os.path.basename(file_path))

    if ext == ".csv":
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
    else:
        df.to_excel(out_path, index=False)

    return out_path
