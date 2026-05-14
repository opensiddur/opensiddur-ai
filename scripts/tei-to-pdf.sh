#!/bin/bash

# Convert a JLPTEI source file (in a project directory) to a PDF using the
# LuaLaTeX + reledmac/reledpar pipeline.
#
# Two stages run sequentially:
#   1. opensiddur.exporter.compiler           — JLPTEI → linear pseudo-TEI
#   2. opensiddur.exporter.pdf.pdf            — pseudo-TEI → reledmac LuaLaTeX → PDF
#
# The optional ``-s <settings-file>`` flag is forwarded to *both* stages:
#   - the compiler reads ``priority``, ``parallel``, ``annotations``;
#   - the PDF stage reads ``typography`` (fonts, layout, paper, fontsize).
#
# Usage:
#   ./tei-to-pdf.sh [-s <settings-file>] [--keep-tex | --tex-output <path>] <project> <file_name> <output-file>

set -e

usage() {
  echo "Usage: $0 [-s <settings-file>] [--keep-tex | --tex-output <path>] <project> <file_name> <output-file>"
  exit 1
}

SETTINGS_FILE=""
KEEP_TEX=false
TEX_OUTPUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -s)
      SETTINGS_FILE="${2:-}"; shift 2 ;;
    --keep-tex)
      KEEP_TEX=true; shift ;;
    --tex-output)
      TEX_OUTPUT="${2:-}"; shift 2 ;;
    --)
      shift; break ;;
    -*)
      echo "Invalid option: $1" >&2; usage ;;
    *)
      break ;;
  esac
done

if $KEEP_TEX && [ -n "$TEX_OUTPUT" ]; then
  echo "Error: --keep-tex and --tex-output are mutually exclusive." >&2
  exit 2
fi

if [ "$#" -ne 3 ]; then
  usage
fi

PROJECT="$1"
FILE_NAME="$2"
OUTPUT="$3"

if [ -n "$SETTINGS_FILE" ]; then
  SETTINGS_ARG=(-s "$SETTINGS_FILE")
else
  SETTINGS_ARG=()
fi

TEX_OUTPUT_ARGS=()
if [ -n "$TEX_OUTPUT" ]; then
  TEX_OUTPUT_ARGS=(--tex-output "$TEX_OUTPUT")
elif $KEEP_TEX; then
  TEX_OUTPUT_ARGS=(--keep-tex)
fi

uv run python -m opensiddur.exporter.compiler "${SETTINGS_ARG[@]}" -p "$PROJECT" -f "$FILE_NAME" -o "$OUTPUT.xml"
uv run python -m opensiddur.exporter.pdf.pdf "${SETTINGS_ARG[@]}" "${TEX_OUTPUT_ARGS[@]}" "$OUTPUT.xml" "$OUTPUT"
rm -f "$OUTPUT.xml"
