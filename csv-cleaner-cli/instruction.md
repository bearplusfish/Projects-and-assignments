# CSV Cleaner CLI

## Objective

Write a Python command-line tool that reads a dirty CSV file and outputs a cleaned, normalized CSV file.

## Requirements

Your script must be named `cleaner.py` and accept two arguments:

```
python3 cleaner.py <input_file> <output_file>
```

The script must handle the following data quality issues:

### Structural Cleaning

1. **UTF-8 BOM** — Strip the Byte Order Mark (`\xef\xbb\xbf`) if present.
2. **Control characters** — Remove ASCII control characters (`\x00`–`\x08`, `\x0b`, `\x0c`, `\x0e`–`\x1f`, `\x7f`) from every cell. Tab (`\x09`) must be preserved.
3. **Inconsistent column count** — All output rows must have the same number of columns as the header. Pad short rows with empty strings. Rows with extra columns must merge overflow values into the last column, separated by `; `.
4. **Mixed delimiters** — Detect and normalize rows that use `;`, `\t`, or `|` as field delimiters instead of commas.
5. **Empty rows** — Skip blank or whitespace-only lines.
6. **Whitespace** — Strip leading and trailing whitespace from every cell. Collapse multiple consecutive internal spaces into a single space.
7. **Line endings** — Normalize `\r\n` and `\r` to `\n` before parsing.

### Semantic Cleaning

8. **Duplicate header rows** — Remove any data row that is identical to the header row.
9. **Duplicate data rows** — Remove fully duplicate data rows, keeping only the first occurrence.
10. **N/A placeholders** — Convert common placeholder values (`N/A`, `n/a`, `NA`, `-`, `null`, `None`, `nil`) to empty strings.
11. **Non-ASCII removal** — Strip all non-ASCII characters (codepoint > 127) from every cell.
12. **Numeric validation** — For columns whose header contains "age" (case-insensitive), convert negative numbers (`< 0`), values above 150, and non-numeric strings to empty strings.

## Constraints

- Standard library only (no `pip install`).
- Must run on Python 3.11+.
- Output must be a valid CSV with a consistent number of columns per row.

## Input

A file named `dirty_data.csv` with the following known issues:

| # | Issue | Example |
|---|-------|---------|
| 1 | UTF-8 BOM | File starts with `ef bb bf` |
| 2 | Control characters | `\x08` (backspace), `\x00` (null) embedded in cells |
| 3 | Mixed delimiter | `Charlie;35;Chicago;Semicolon delimiter` |
| 4 | Duplicate header | Header row repeated in the middle of data |
| 5 | Extra/missing columns | 6-column row, 2-column row among 4-column data |
| 6 | Whitespace padding | `" 28 "`, `"  Berlin  "` — must strip AND collapse |
| 7 | Empty rows | Whitespace-only line |
| 8 | Duplicate data rows | Hank appears twice with identical data |
| 9 | N/A placeholders | `N/A` in a cell where a value is expected |
| 10 | Negative / invalid age | `-5`, `invalid_age`, `200` — must become empty |
| 11 | Special Unicode | `✅` in a cell (should be removed) |

## Output

A cleaned CSV file written to the path specified by the second argument.

## Verification

Run `tests/test.sh` to verify correctness. Exit code 0 = pass, 1 = fail.

<!--
===============================================================================
设计说明
===============================================================================

dirty_data.csv 按照四层脏数据模型构造：

  格式层   → BOM、行尾符混用 (\r\n)
  结构层   → 空行、列数不一致、分隔符混杂 (;)
  单元格层 → 控制字符 (\x00 \x08)、空格填充、N/A 占位符
  语义层   → 负数 (-5)、超范围值 (200)、非数字 (invalid_age)

每一行对应至少一种边界。600 字节、20 行，藏了 11 种问题。

-->
