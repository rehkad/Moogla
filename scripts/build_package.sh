#!/usr/bin/env bash
set -e

if [ $# -ne 1 ]; then
    echo "Usage: $0 OUTPUT" >&2
    exit 1
fi

if ! command -v pyinstaller >/dev/null 2>&1; then
    echo "pyinstaller is required. Install with pip install pyinstaller." >&2
    exit 1
fi

OUTPUT=$1
pyinstaller --onefile --name moogla src/moogla/cli.py
mkdir -p "$(dirname "$OUTPUT")"
cp "dist/moogla" "$OUTPUT"
echo "Package created at $OUTPUT"
