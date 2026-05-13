#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Setup working paths
WORK_DIR="/tmp/csv-cleaner-test-$$"
trap 'rm -rf "$WORK_DIR"' EXIT

mkdir -p "$WORK_DIR"

INPUT="$WORK_DIR/dirty_data.csv"
OUTPUT="$WORK_DIR/clean_data.csv"

# Copy the dirty data into place
cp "$PROJECT_DIR/environment/dirty_data.csv" "$INPUT"

echo "=== Running solve.sh ==="
cd "$PROJECT_DIR"
bash "$PROJECT_DIR/solution/solve.sh" "$INPUT" "$OUTPUT"

echo ""
echo "=== Running validation ==="
python3 "$SCRIPT_DIR/test_logic.py" "$OUTPUT"
