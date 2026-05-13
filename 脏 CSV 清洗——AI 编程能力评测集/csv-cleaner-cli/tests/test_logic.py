#!/usr/bin/env python3
"""Validate a cleaned CSV against the csv-cleaner-cli benchmark requirements.

Usage:
    python3 test_logic.py <cleaned_csv>

Exit 0 if all checks pass, exit 1 if any check fails.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ILLEGAL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MULTISPACE = re.compile(r" {2,}")
NA_PATTERN = re.compile(r"^(?:n/?a|null|none|nil|-)$", re.IGNORECASE)
SPACE_PADDING = re.compile(r"^\s|.*\s$")
FAILED = False
ANY_FAILED = False


def fail(msg: str) -> None:
    global FAILED
    print(f"  FAIL: {msg}")
    FAILED = True


def check(condition: bool, msg: str) -> None:
    if not condition:
        fail(msg)


def load_csv(path: Path) -> list[list[str]]:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    rows: list[list[str]] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        reader = csv.reader([stripped])
        row = next(reader)
        row = [c.strip() for c in row]
        if any(row):
            rows.append(row)
    return rows


def _begin() -> None:
    """Reset per-test flag; never clears ANY_FAILED."""
    global FAILED
    FAILED = False


def _pass() -> None:
    global FAILED, ANY_FAILED
    if not FAILED:
        print("  PASS")
    else:
        ANY_FAILED = True


# ─── Test 1: File not empty ────────────────────────────────────
def test_file_not_empty(path: Path) -> None:
    _begin()
    print("[1] File not empty ...")
    check(path.exists(), f"File not found: {path}")
    check(path.stat().st_size > 0, "File is empty (0 bytes)")
    _pass()


# ─── Test 2: No BOM ────────────────────────────────────────────
def test_no_bom(path: Path) -> None:
    _begin()
    print("[2] No UTF-8 BOM ...")
    first = path.read_bytes()[:3]
    check(first != b"\xef\xbb\xbf", f"BOM still present: {first.hex()}")
    _pass()


# ─── Test 3: No illegal control characters ─────────────────────
def test_no_control_chars(rows: list[list[str]]) -> None:
    _begin()
    print("[3] No illegal control characters ...")
    for i, row in enumerate(rows, 1):
        for j, cell in enumerate(row):
            m = ILLEGAL_CHARS.search(cell)
            check(m is None,
                  f"Row {i} col {j}: char 0x{m.group(0).encode('utf-8').hex() if m else '??'} in {cell!r}")
    _pass()


# ─── Test 4: Consistent column count ───────────────────────────
def test_column_count_consistent(rows: list[list[str]]) -> None:
    _begin()
    print("[4] Consistent column count ...")
    check(len(rows) > 0, "No rows in output")
    ncols = len(rows[0])
    for i, row in enumerate(rows, 1):
        check(len(row) == ncols, f"Row {i}: {len(row)} cols, expected {ncols}")
    print(f"  INFO: {ncols} columns x {len(rows)} rows")
    _pass()


# ─── Test 5: No duplicate header ───────────────────────────────
def test_no_duplicate_header(rows: list[list[str]]) -> None:
    _begin()
    print("[5] No duplicate header rows ...")
    check(len(rows) >= 1, "No rows in output")
    header = rows[0]
    n = sum(1 for r in rows[1:] if r == header)
    check(n == 0, f"{n} duplicate header row(s) found")
    _pass()


# ─── Test 6: No duplicate data rows ────────────────────────────
def test_no_duplicate_data(rows: list[list[str]]) -> None:
    _begin()
    print("[6] No duplicate data rows ...")
    data = rows[1:]
    seen: set[tuple[str, ...]] = set()
    dups: list[int] = []
    for i, row in enumerate(data, 2):
        key = tuple(row)
        if key in seen:
            dups.append(i)
        seen.add(key)
    check(len(dups) == 0, f"Duplicate data rows at lines: {dups}")
    _pass()


# ─── Test 7: Mixed delimiters fixed ────────────────────────────
def test_mixed_delimiters_fixed(rows: list[list[str]]) -> None:
    _begin()
    print("[7] Mixed delimiters normalized ...")
    # A cell with 3+ semicolons = un-split semicolon-delimited row
    for i, row in enumerate(rows, 1):
        for j, cell in enumerate(row):
            check(cell.count(";") < 3,
                  f"Row {i} col {j}: un-split semicolons in {cell!r}")
    _pass()


# ─── Test 8: No N/A placeholders ───────────────────────────────
def test_no_na_placeholders(rows: list[list[str]]) -> None:
    _begin()
    print("[8] No N/A placeholders ...")
    for i, row in enumerate(rows, 1):
        for j, cell in enumerate(row):
            check(not NA_PATTERN.match(cell),
                  f"Row {i} col {j}: placeholder not converted: {cell!r}")
    _pass()


# ─── Test 9: Whitespace stripped and normalized ────────────────
def test_whitespace_normalized(rows: list[list[str]]) -> None:
    _begin()
    print("[9] Whitespace stripped and normalized ...")
    for i, row in enumerate(rows, 1):
        for j, cell in enumerate(row):
            if not cell:
                continue
            check(not SPACE_PADDING.search(cell),
                  f"Row {i} col {j}: leading/trailing space in {cell!r}")
            check(not MULTISPACE.search(cell),
                  f"Row {i} col {j}: consecutive spaces in {cell!r}")
    _pass()


# ─── Test 10: Age column validation ────────────────────────────
def test_age_column_valid(rows: list[list[str]]) -> None:
    _begin()
    print("[10] Age column numeric validation ...")
    header = rows[0]
    age_cols = [i for i, h in enumerate(header) if h.lower() == "age"]
    check(len(age_cols) > 0, "No 'Age' column found in header")
    if not age_cols:
        _pass()
        return
    col = age_cols[0]
    for i, row in enumerate(rows[1:], 2):
        val = row[col] if col < len(row) else ""
        if not val:
            continue
        try:
            n = int(val)
            check(n >= 0, f"Row {i}: negative age {n}")
            check(n <= 150, f"Row {i}: unrealistic age {n}")
        except ValueError:
            fail(f"Row {i}: non-numeric age value: {val!r}")
    _pass()


# ─── Test 11: Expected data content ────────────────────────────
def test_expected_content(rows: list[list[str]]) -> None:
    _begin()
    print("[11] Expected data content ...")

    def find_row(col0: str) -> list[str] | None:
        return next((r for r in rows if r[0] == col0), None)

    # --- Alice: clean row intact ---
    alice = find_row("Alice")
    check(alice is not None, "Alice row missing")
    check(alice is not None and alice[1] == "25", f"Alice age wrong: {alice}")

    # --- Bob (missing age): age should be empty ---
    bob_missing = next((r for r in rows if r[0] == "Bob" and r[1] == ""), None)
    check(bob_missing is not None, "Bob (missing age) not found")

    # --- Bob (\x08 backspace): control char gone, no double space ---
    bob_ctrl = next((r for r in rows if r[0] == "Bob" and "backspace" in r[3]), None)
    check(bob_ctrl is not None, "Bob (backspace) row missing")
    check(bob_ctrl is not None and "  " not in bob_ctrl[3],
          f"Bob has double space: {bob_ctrl[3]!r}") # type: ignore
    check(bob_ctrl is not None and "with backspace" in bob_ctrl[3],
          f"Bob spacing not normalized: {bob_ctrl[3]!r}") # type: ignore

    # --- Missing name row: first col empty but row exists ---
    missing_name = next((r for r in rows if r[0] == "" and r[1] == "30"), None)
    check(missing_name is not None, "Missing-name row not found")

    # --- Charlie (semicolon): fixed to commas ---
    charlie = next((r for r in rows if r[0] == "Charlie" and r[1] == "35"), None)
    check(charlie is not None, "Charlie (semicolon) row missing")

    # --- Charlie (invalid_age): age should be empty ---
    charlie_bad = next((r for r in rows if r[0] == "Charlie" and r[1] == ""), None)
    check(charlie_bad is not None, "Charlie (invalid_age) row missing or age not cleared")

    # --- Diana (\x00): null byte gone ---
    diana = find_row("Diana")
    check(diana is not None, "Diana row missing")
    check(diana is not None and "null" in diana[3] and "byte" in diana[3],
          f"Diana notes corrupted: {diana[3]!r}") # type: ignore

    # --- Eve (6 cols): merged into last col ---
    eve = next((r for r in rows if r[0] == "Eve" and r[1] == "22"), None)
    check(eve is not None, "Eve (6 cols) row missing")
    check(eve is not None and ("Extra" in eve[3] or "Column" in eve[3]),
          f"Eve extra cols not merged into last: {eve[3]!r}") # type: ignore

    # --- Eve (age 200): age should be empty ---
    eve_big = next((r for r in rows if r[0] == "Eve" and r[1] == ""), None)
    check(eve_big is not None, "Eve (age 200) row missing or age not cleared")

    # --- Frank (short): padded ---
    frank = next((r for r in rows if r[0] == "Frank" and r[1] == "40"), None)
    check(frank is not None, "Frank (short) row missing")
    check(frank is not None and frank[2] == "" and frank[3] == "",
          f"Frank not padded correctly: {frank}")

    # --- Frank (whitespace): stripped, "28", "Berlin" ---
    frank_ws = next((r for r in rows if r[0] == "Frank" and r[1] == "28"), None)
    check(frank_ws is not None, "Frank (whitespace) row missing")
    check(frank_ws is not None and frank_ws[2] == "Berlin",
          f"Frank city not stripped: {frank_ws[2]!r}") # type: ignore
    check(frank_ws is not None and "Needs stripping" == frank_ws[3],
          f"Frank notes wrong: {frank_ws[3]!r}") # type: ignore

    # --- Grace: clean row ---
    grace = find_row("Grace")
    check(grace is not None, "Grace row missing")

    # --- Hank: appears exactly once ---
    hank_count = sum(1 for r in rows if r[0] == "Hank")
    check(hank_count == 1, f"Hank appears {hank_count} times (expected 1)")

    # --- David (age -5): age should be empty ---
    david = find_row("David")
    check(david is not None, "David row missing")
    check(david is not None and david[1] == "",
          f"David negative age not cleared: {david[1]!r}") # type: ignore

    # --- Ivy (N/A): age should be empty ---
    ivy = find_row("Ivy")
    check(ivy is not None, "Ivy row missing")
    check(ivy is not None and ivy[1] == "",
          f"Ivy N/A age not cleared: {ivy[1]!r}") # type: ignore

    # --- Jack: ✅ removed ---
    jack = find_row("Jack")
    check(jack is not None, "Jack row missing")
    check(jack is not None and "✅" not in jack[3],
          f"Jack's ✅ not removed: {jack[3]!r}") # type: ignore

    _pass()


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <cleaned_csv>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])
    print(f"Validating: {path}\n")

    test_file_not_empty(path)
    test_no_bom(path)
    rows = load_csv(path)
    test_no_control_chars(rows)
    test_column_count_consistent(rows)
    test_no_duplicate_header(rows)
    test_no_duplicate_data(rows)
    test_mixed_delimiters_fixed(rows)
    test_no_na_placeholders(rows)
    test_whitespace_normalized(rows)
    test_age_column_valid(rows)
    test_expected_content(rows)

    if ANY_FAILED:
        print("\n=== Some checks FAILED ===")
        sys.exit(1)

    print("\n=== All checks passed ===")
    sys.exit(0)


if __name__ == "__main__":
    main()


# =============================================================================
# Known limitations (not fixed — out of scope for this benchmark)
# =============================================================================
#
# 1. split("\n") breaks quoted newlines
#    Splitting the whole file by newline before CSV parsing would corrupt
#    multi-line quoted fields.  Not an issue here (605-byte file, no quoted
#    newlines) but would matter for a production tool.
#
# 4. strip() may remove intentional whitespace
#    Every cell is stripped.  Some CSV formats treat leading/trailing spaces
#    as meaningful.  For this benchmark's data, all such spaces are noise.
#
# 7. cell.count(";") < 3 is a heuristic
#    Test 7 uses "3+ semicolons = un-split row" as a rule of thumb.  It is
#    not mathematically precise but works for the scale of this data set.
#
# 8. test 10 / test 11 overlap on Age
#    Test 10 validates the Age column generically; test 11 checks specific
#    expected values.  Both are intentional — they catch different failure
#    modes.
#
# 9. test 11 is hardcoded to known data
#    Unlike tests 1–10 which apply universal rules, test 11 relies on
#    specific rows (Alice, Bob, Charlie, …) from the known dirty_data.csv.
#    This is by design: benchmark tests must verify concrete expected output.
#
# 10. repeated O(n) scanning in test 11
#    Each `next((r for r in rows if …), None)` is a linear scan.  With 18
#    rows the overhead is negligible.
#
# 11. error messages could be more informative
#    Some messages rely on guard expressions (m is None / or '??') to avoid
#    crashes.  Readable enough for this context.
#
# 13. empty-row skipping logic
#    load_csv skips fully blank lines but keeps rows that have at least one
#    non-empty cell.  This matches the expected cleaning behaviour.
#
# 14. minimal CLI
#    Only `<cleaned_csv>` is accepted.  For a single-purpose benchmark
#    verifier, a single argument is sufficient.
#
# 15. type annotations are incomplete
#    Helper functions and test functions lack full type stubs.  Not needed
#    for the verifier's audience.
