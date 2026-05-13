#!/usr/bin/env python3
"""Display dirty CSV with hidden characters and problems annotated."""
import csv, io, sys
from pathlib import Path

def show(path: Path) -> None:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    lines = [l.strip() for l in text.split("
") if l.strip()]
    hdr = next(csv.reader(io.StringIO(lines[0])))
    seen: set[str] = set()
    sys.stdout.buffer.write(f'{"ROW":<4s}  {"Name":<12s}  {"Age":<10s}  {"City":<12s}  {"Notes":<28s}  FLAGS
'.encode())
    sys.stdout.buffer.write(b'-' * 100 + b'
')
    for i, line in enumerate(lines[1:], 2):
        try: row = next(csv.reader(io.StringIO(line)))
        except csv.Error: row = line.split(",")
        while len(row) < 4: row.append("")
        tags = []
        if any(ord(c) < 0x20 for c in line): tags.append("CTRL")
        if ";" in line and line.count(";") >= 3 and "," not in line: tags.append("BAD-DELIM")
        if line.count(",") >= 5: tags.append(f"WIDE({line.count(',')+1}cols)")
        if "," in line and line.count(",") == 1: tags.append("NARROW(2cols)")
        if "N/A" in line: tags.append("NA")
        if "-5" in line: tags.append("NEG-AGE")
        if "200" in line and "Eve" in line: tags.append("OVER-AGE")
        if "invalid_age" in line: tags.append("BAD-AGE")
        if "  " in line and "," in line: tags.append("PADDING")
        if '✅' in line: tags.append("EMOJI")
        if i > 2 and row[:4] == hdr[:4]: tags.append("DUP-HEADER")
        key = ",".join(row)
        if key in seen: tags.append("DUP-DATA")
        else: seen.add(key)
        if "" in row[:4] and "BAD-DELIM" not in tags: tags.append("MISSING")
        name  = "".join(c if " " <= c <= "~" else f"[{ord(c):02X}]" for c in row[0])
        age   = "".join(c if " " <= c <= "~" else f"[{ord(c):02X}]" for c in row[1])
        city  = "".join(c if " " <= c <= "~" else f"[{ord(c):02X}]" for c in row[2])
        notes = "".join(c if " " <= c <= "~" else f"[{ord(c):02X}]" for c in row[3])
        flag_str = " ".join(tags) if tags else "ok"
        out = f'{i:<4d}  {name:<12s}  {age:<10s}  {city:<12s}  {notes:<28s}  {flag_str}
'
        sys.stdout.buffer.write(out.encode())

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=Path, nargs="?", default="environment/dirty_data.csv")
    args = p.parse_args()
    show(args.csv)
