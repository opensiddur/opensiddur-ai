#!/bin/bash

# This script converts a TEI file to a PDF file using the Open Siddur TEI to PDF converter.

# Usage:
# ./tei-to-pdf.sh <project> <file_name> <output-file>

# Example:
# ./tei-to-pdf.sh  output.pdf

# The input file should be a valid TEI file.
# The output file will be a PDF file.
# Parse arguments, supporting optional -s <settings-file>
set -e

usage() {
  echo "Usage: $0 [-s <settings-file>] <project> <file_name> <output-file>"
  exit 1
}

SETTINGS_FILE=""
while getopts ":s:" opt; do
  case "$opt" in
    s) SETTINGS_FILE="$OPTARG" ;;
    \?) echo "Invalid option: -$OPTARG" >&2; usage ;;
    :)  echo "Option -$OPTARG requires an argument." >&2; usage ;;
  esac
done
shift $((OPTIND-1))

if [ "$#" -ne 3 ]; then
  usage
fi

PROJECT="$1"
FILE_NAME="$2"
OUTPUT="$3"

if [ -n "$SETTINGS_FILE" ]; then
  SETTINGS_ARG="-s $SETTINGS_FILE"
else
  SETTINGS_ARG=""
fi


uv run python -m opensiddur.exporter.compiler ${SETTINGS_ARG} -p $1 -f $2 -o $3.xml
uv run python -m opensiddur.exporter.pdf.pdf $3.xml $3
rm -f $3.xml
