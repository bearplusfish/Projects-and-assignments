#!/bin/bash
set -euo pipefail

INPUT="${1:-data/dirty_data.csv}"
OUTPUT="${2:-data/clean_data.csv}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/cleaner.py" "$INPUT" "$OUTPUT"
