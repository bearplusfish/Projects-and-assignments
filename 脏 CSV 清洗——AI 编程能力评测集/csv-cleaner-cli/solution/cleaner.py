#!/usr/bin/env python3
"""CSV cleaner: normalizes dirty CSV into clean, consistent output."""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from pathlib import Path

ILLEGAL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MULTISPACE = re.compile(r" {2,}")
ALT_DELIMITERS = [";", "\t", "|"]
NA_PATTERN = re.compile(r"^(?:n/?a|null|none|nil|-)$", re.IGNORECASE)
AGE_LABEL = re.compile(r"^age$", re.IGNORECASE)
NON_ASCII = re.compile(r"[^\x00-\x7f]")


def sniff_dialect(path: Path) -> type[csv.Dialect] | None:
    """Try to detect the CSV dialect from the first 8 KB."""
    try:
        with open(path, encoding="utf-8-sig") as fh:
            sample = fh.read(8192)
        sniffer = csv.Sniffer()
        return sniffer.sniff(sample, delimiters=",;\t|")
    except Exception:
        return None


def read_rows(path: Path, dialect: type[csv.Dialect] | None) -> list[list[str]]:
    """Read all data rows, skipping empty lines and recovering from malformed rows."""
    rows: list[list[str]] = []

    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        raw_text = fh.read()

    raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = raw_text.split("\n")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        cleaned_line = ILLEGAL_CHARS.sub("", stripped)

        try:
            if dialect is None:
                reader = csv.reader(io.StringIO(cleaned_line))
            else:
                reader = csv.reader(io.StringIO(cleaned_line), dialect=dialect)
            row = next(reader)
        except csv.Error:
            row = [c.strip() for c in cleaned_line.split(",")]

        row = [c.strip() for c in row]
        if not any(row):
            continue

        rows.append(row)

    return rows


def strip_non_ascii(rows: list[list[str]]) -> list[list[str]]:
    """Remove non-ASCII characters from every cell."""
    return [[NON_ASCII.sub("", c) for c in row] for row in rows]


def normalize_whitespace(rows: list[list[str]]) -> list[list[str]]:
    """Collapse multiple consecutive spaces into one within each cell."""
    return [[MULTISPACE.sub(" ", c) for c in row] for row in rows]


def fix_mixed_delimiters(rows: list[list[str]]) -> list[list[str]]:
    """Re-parse rows that appear to use a different delimiter than the header."""
    if not rows:
        return rows

    ncols = len(rows[0])
    if ncols <= 1:
        return rows

    fixed: list[list[str]] = [rows[0]]

    for row in rows[1:]:
        if len(row) == ncols:
            fixed.append(row)
            continue

        raw = ",".join(row)
        best: list[str] | None = None

        for delim in ALT_DELIMITERS:
            if delim not in raw:
                continue
            candidate = [c.strip() for c in raw.split(delim)]
            if len(candidate) == ncols:
                best = candidate
                break

        if best is not None:
            fixed.append(best)
        else:
            fixed.append(row)

    return fixed


def normalize_columns(rows: list[list[str]]) -> list[list[str]]:
    """Ensure all rows match header column count. Extra cols merge into last col."""
    if not rows:
        return rows

    ncols = len(rows[0])
    normalized: list[list[str]] = []

    for row in rows:
        if 0 < len(row) < ncols:
            row = row + [""] * (ncols - len(row))
        elif len(row) > ncols:
            overflow = "; ".join(row[ncols - 1:])
            row = row[:ncols - 1] + [overflow]
        normalized.append(row)

    return normalized


def normalize_na_values(rows: list[list[str]]) -> list[list[str]]:
    """Convert N/A style placeholders to empty strings."""
    return [[c if not NA_PATTERN.match(c) else "" for c in row] for row in rows]


def validate_numeric_fields(rows: list[list[str]]) -> list[list[str]]:
    """Validate numeric columns: negative or >150 → empty; non-numeric → empty."""
    if not rows:
        return rows

    header = rows[0]
    num_cols = [i for i, h in enumerate(header) if AGE_LABEL.match(h)]
    if not num_cols:
        return rows

    cleaned: list[list[str]] = [list(header)]
    for row in rows[1:]:
        row = list(row)
        for col in num_cols:
            if col >= len(row):
                continue
            val = row[col]
            if not val:
                continue
            try:
                n = int(val)
                if n < 0 or n > 150:
                    row[col] = ""
            except ValueError:
                row[col] = ""
        cleaned.append(row)

    return cleaned


def remove_duplicate_header(rows: list[list[str]]) -> list[list[str]]:
    """Remove rows that are identical to the header row (after the first)."""
    if len(rows) < 2:
        return rows

    header = rows[0]
    clean_rows = [header]

    for row in rows[1:]:
        if row != header:
            clean_rows.append(row)

    return clean_rows


def remove_duplicate_data(rows: list[list[str]]) -> list[list[str]]:
    """Remove duplicate data rows, keeping the first occurrence."""
    if len(rows) < 2:
        return rows

    seen: set[tuple[str, ...]] = set()
    unique: list[list[str]] = []

    for row in rows:
        key = tuple(row)
        if key not in seen:
            seen.add(key)
            unique.append(row)

    return unique


def clean(in_path: Path, out_path: Path) -> None:
    dialect = sniff_dialect(in_path)
    rows = read_rows(in_path, dialect)
    rows = strip_non_ascii(rows)
    rows = normalize_whitespace(rows)
    rows = fix_mixed_delimiters(rows)
    rows = normalize_na_values(rows)
    rows = normalize_columns(rows)
    rows = validate_numeric_fields(rows)
    rows = remove_duplicate_header(rows)
    rows = remove_duplicate_data(rows)

    if not rows:
        print("Warning: no data rows found after cleaning.", file=sys.stderr)
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean a dirty CSV file and produce normalized output."
    )
    parser.add_argument("input", type=Path, help="Path to the dirty CSV file")
    parser.add_argument("output", type=Path, help="Path for the cleaned CSV output")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    clean(args.input, args.output)


if __name__ == "__main__":
    main()


# =============================================================================
# Known limitations / suggestions (not implemented — out of scope for benchmark)
# =============================================================================
#
# 1. csv.Sniffer false positives
#    Dialect detection is heuristic and may misidentify delimiters on ambiguous
#    data. A production tool should validate by checking column-count consistency
#    after the sniff and fall back to a configurable default.
#
# 2. Per-line StringIO overhead
#    Each line creates a new StringIO + csv.reader instance. For large files
#    (>10K rows), use a single csv.reader on the full text, with per-row
#    fallback only when csv.Error is raised.
#
# 4. Irreversible column merge
#    Extra columns are joined with "; " into the last cell. This cannot be
#    undone. A safer approach uses a rarer separator (" | ") or logs a
#    warning and drops the overflow instead of merging.
#
# 5. Numeric column detection too strict
#    Currently only matches exact "age" (case-insensitive). Variants like
#    "Age (years)" or "user_age" are missed. A production tool should accept
#    a CLI flag (--numeric-cols) or use substring matching.
#
# 6. Row-level dedup too aggressive
#    Whole-row dedup may delete rows that are identical in data but represent
#    distinct records (e.g., two different people with the same attributes).
#    Consider supporting primary-key-based dedup or making full-row dedup
#    opt-in via a flag.
#
# 7. Full in-memory loading
#    All rows are held in a list. For files > available RAM this will OOM.
#    A streaming pipeline (generator-based) with a spill-to-disk strategy
#    would be needed for production use.
#
# 9. print() instead of logging
#    Production tools should use the `logging` module with configurable
#    levels (INFO, WARNING, ERROR) rather than print() to stderr.
#
# 10. sniff_dialect reads only 8 KB
#     The first 8 KB may not be representative for files where the header
#     or first rows are clean but later rows have mixed delimiters.
#     Consider increasing the sample size or allowing the user to
#     specify the delimiter explicitly (--delimiter).
#
# 11. Fallback split(",") too naive
#     When csv.reader fails, the fallback is a simple comma split that
#     cannot handle quoted fields or embedded commas. A better fallback
#     would try all configured delimiters and pick the one that yields
#     the expected column count.
#
# 12. Header assumed to be row 1
#     The first non-empty row is always treated as the header. If the file
#     has no header, this corrupts the first data row. A --no-header flag
#     or automatic header detection (checking if row 1 looks like data vs.
#     labels) would be more robust.
